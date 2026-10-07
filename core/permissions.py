# core/permissions.py

from django.contrib import admin
from django.utils import timezone

from rest_framework.permissions import (
    BasePermission,
)

from core.models import Subscription


# ============================================================================
# Shared helpers
# ============================================================================


def is_authenticated(user):
    return bool(
        user
        and user.is_authenticated
    )


def is_global_authority(user):
    """
    Global authority is limited to platform owners
    and Django superusers.

    Restaurant managers are intentionally excluded.
    """
    return bool(
        user
        and (
            user.is_superuser
            or getattr(
                user,
                "is_platform_owner",
                False,
            )
        )
    )


def get_user_restaurant(user):
    return getattr(
        user,
        "restaurant",
        None,
    )


def get_user_role(user):
    return str(
        getattr(
            user,
            "role",
            "",
        )
        or ""
    ).strip().upper()


def is_manager(user):
    """
    A manager is a restaurant-scoped manager.
    Global authority is checked separately.
    """
    if not is_authenticated(user):
        return False

    if is_global_authority(user):
        return True

    return get_user_role(user) == "MANAGER"


def is_cashier(user):
    if not is_authenticated(user):
        return False

    if is_global_authority(user):
        return True

    return get_user_role(user) == "CASHIER"


def is_server(user):
    if not is_authenticated(user):
        return False

    return get_user_role(user) == "SERVER"


def is_cook(user):
    if not is_authenticated(user):
        return False

    return get_user_role(user) == "COOK"


def has_restaurant(user):
    return (
        is_authenticated(user)
        and get_user_restaurant(user)
        is not None
    )


def object_restaurant(obj):
    """
    Resolve the restaurant from common object
    relationships.
    """
    restaurant = getattr(
        obj,
        "restaurant",
        None,
    )

    if restaurant is not None:
        return restaurant

    order = getattr(
        obj,
        "order",
        None,
    )

    if order is not None:
        restaurant = getattr(
            order,
            "restaurant",
            None,
        )

        if restaurant is not None:
            return restaurant

    menu = getattr(
        obj,
        "menu",
        None,
    )

    if menu is not None:
        restaurant = getattr(
            menu,
            "restaurant",
            None,
        )

        if restaurant is not None:
            return restaurant

    table = getattr(
        obj,
        "table",
        None,
    )

    if table is not None:
        restaurant = getattr(
            table,
            "restaurant",
            None,
        )

        if restaurant is not None:
            return restaurant

    product = getattr(
        obj,
        "product",
        None,
    )

    if product is not None:
        restaurant = getattr(
            product,
            "restaurant",
            None,
        )

        if restaurant is not None:
            return restaurant

    return None


def user_can_access_object(user, obj):
    """
    Global authorities can access all objects.

    Other users can access only objects belonging
    to their assigned restaurant.
    """
    if not is_authenticated(user):
        return False

    if is_global_authority(user):
        return True

    user_restaurant = get_user_restaurant(
        user
    )

    if user_restaurant is None:
        return False

    obj_restaurant = object_restaurant(obj)

    return (
        obj_restaurant is not None
        and obj_restaurant == user_restaurant
    )


# ============================================================================
# Django admin permission base
# ============================================================================


class RoleRestrictedAdmin(admin.ModelAdmin):
    """
    Base ModelAdmin for restaurant-scoped admin
    access.

    Global authorities can access all records.
    Restaurant managers can access records for
    their own restaurant only.
    """

    def user_is_manager(self, request):
        return is_manager(request.user)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user

        if is_global_authority(user):
            return queryset

        if not self.user_is_manager(request):
            return queryset.none()

        restaurant = get_user_restaurant(user)

        if restaurant is None:
            return queryset.none()

        model_fields = {
            field.name
            for field in self.model._meta.get_fields()
        }

        if "restaurant" in model_fields:
            return queryset.filter(
                restaurant=restaurant
            )

        return queryset.none()

    def has_module_permission(self, request):
        return (
            is_global_authority(request.user)
            or is_manager(request.user)
        )

    def has_view_permission(
        self,
        request,
        obj=None,
    ):
        user = request.user

        if not (
            is_global_authority(user)
            or is_manager(user)
        ):
            return False

        if obj is None:
            return True

        return user_can_access_object(
            user,
            obj,
        )

    def has_add_permission(self, request):
        return (
            is_global_authority(request.user)
            or is_manager(request.user)
        )

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        user = request.user

        if is_global_authority(user):
            return True

        if not is_manager(user):
            return False

        if obj is None:
            return True

        return user_can_access_object(
            user,
            obj,
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        user = request.user

        if is_global_authority(user):
            return True

        if not is_manager(user):
            return False

        if obj is None:
            return True

        return user_can_access_object(
            user,
            obj,
        )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        user = request.user

        if (
            not change
            and not is_global_authority(user)
        ):
            restaurant = get_user_restaurant(
                user
            )

            if restaurant is not None:
                model_fields = {
                    field.name
                    for field in (
                        obj._meta.get_fields()
                    )
                }

                if "restaurant" in model_fields:
                    obj.restaurant = restaurant

        super().save_model(
            request,
            obj,
            form,
            change,
        )


# ============================================================================
# Base DRF permissions
# ============================================================================


class IsAuthenticatedUser(BasePermission):
    message = (
        "Authentication credentials "
        "were not provided."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_authenticated(
            request.user
        )


class IsGlobalAuthority(BasePermission):
    message = (
        "Global platform authority "
        "is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_global_authority(
            request.user
        )


class HasRestaurant(BasePermission):
    message = (
        "You are not assigned to a restaurant."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_restaurant(
            request.user
        )


# ============================================================================
# Restaurant-scoped role permissions
# ============================================================================


class IsManagerOrGlobalAuthority(
    BasePermission
):
    message = (
        "Manager access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageStaff(BasePermission):
    message = (
        "Staff management access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageProducts(BasePermission):
    message = (
        "Product management access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageTables(BasePermission):
    message = (
        "Table management access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageSettings(BasePermission):
    message = (
        "Restaurant settings access "
        "is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanViewReports(BasePermission):
    message = (
        "Financial reports access "
        "is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )


class CanViewDashboard(BasePermission):
    message = (
        "Dashboard access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return is_manager(
            request.user
        )


# ============================================================================
# POS, cashier, server, and kitchen permissions
# ============================================================================


class CanAccessPOS(BasePermission):
    message = (
        "POS access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cashier(user)
            or is_server(user)
        )


class CanAccessCashierShift(BasePermission):
    message = (
        "Cashier or manager access "
        "is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cashier(user)
        )


class CanAccessKitchen(BasePermission):
    message = (
        "Kitchen access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cook(user)
        )


class CanAccessOrders(BasePermission):
    message = (
        "Order access is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cook(user)
            or is_cashier(user)
            or is_server(user)
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return user_can_access_object(
            request.user,
            obj,
        )


# ============================================================================
# Subscription permission
# ============================================================================

class HasActiveSubscription(BasePermission):
    """
    Blocks access to protected APIs if:
    - No subscription exists, OR
    - Subscription status is not 'active' or 'trialing', OR
    - current_period_end has passed (trial or subscription expired).
    
    For Option B (plan selection after trial):
    - During trial: access granted (status='trialing', current_period_end in future)
    - After trial expires: access denied until admin approves a plan
    """
    
    message = (
        "Your free trial has ended. Select a plan and complete payment "
        "to continue using BEEPOS."
    )

    def has_permission(self, request, view):
        user = request.user

        if not is_authenticated(user):
            return False

        # Allow superusers/global staff
        if is_global_authority(user):
            return True

        restaurant = get_user_restaurant(user)

        if restaurant is None:
            self.message = "Your account is not assigned to a restaurant."
            return False

        # Use the OneToOne relationship if available
        try:
            subscription = restaurant.subscription
        except Exception:
            # Fallback to query if related_name doesn't work
            subscription = (
                Subscription.objects.filter(restaurant=restaurant)
                .order_by("-created_at")
                .first()
            )

        if subscription is None:
            self.message = "No subscription was found for this restaurant."
            return False

        # Expire if needed before checking (ensures status is current)
        subscription.expire_if_needed()

        now = timezone.now()
        status = str(subscription.status).lower()

        # Only 'active' and 'trialing' are valid
        if status not in {"active", "trialing"}:
            self.message = (
                "Your trial or subscription has expired. "
                "Choose a plan to restore access."
            )
            return False

        end_date = subscription.current_period_end

        # If end_date exists and is in the past, deny access
        if end_date is not None and end_date <= now:
            self.message = (
                "Your trial or subscription has expired. "
                "Choose a plan to restore access."
            )
            return False

        return True
    
# ============================================================================
# Combined convenience permissions
# ============================================================================


class IsManagerWithSubscription(
    BasePermission
):
    message = (
        "Manager access with an active "
        "subscription is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return bool(
            IsManagerOrGlobalAuthority()
            .has_permission(request, view)
            and HasActiveSubscription()
            .has_permission(request, view)
        )


class CanAccessPOSWithSubscription(
    BasePermission
):
    message = (
        "POS access with an active "
        "subscription is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return bool(
            CanAccessPOS()
            .has_permission(request, view)
            and HasActiveSubscription()
            .has_permission(request, view)
        )


class CanAccessKitchenWithSubscription(
    BasePermission
):
    message = (
        "Kitchen access with an active "
        "subscription is required."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return bool(
            CanAccessKitchen()
            .has_permission(request, view)
            and HasActiveSubscription()
            .has_permission(request, view)
        )