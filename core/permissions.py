# core/permissions.py

from django.contrib import admin
from django.utils import timezone
from rest_framework.permissions import BasePermission

from core.models import Subscription


# ============================================================================
# Shared helpers
# ============================================================================


def is_authenticated(user):
    return bool(user and user.is_authenticated)


def is_global_authority(user):
    """
    Platform-level authorities can access all restaurants and bypass
    restaurant subscription checks.

    Restaurant managers are not global authorities.
    """
    return bool(
        user
        and (
            user.is_superuser
            or getattr(user, "is_platform_owner", False)
        )
    )


def get_user_restaurant(user):
    """
    Return the restaurant assigned to the user, or None.

    This expects your User model to have a `restaurant` relation.
    """
    return getattr(user, "restaurant", None)


def get_user_role(user):
    """
    Normalize the user role stored on your custom User model.
    """
    return str(
        getattr(user, "role", "") or ""
    ).strip().upper()


def is_manager(user):
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
    return bool(
        is_authenticated(user)
        and get_user_restaurant(user) is not None
    )


def get_restaurant_subscription(restaurant):
    """
    Safely return the newest subscription for a restaurant.

    Do NOT use `restaurant.subscription` here. If Subscription.restaurant is a
    OneToOneField and no related object exists, Django can raise
    RelatedObjectDoesNotExist instead of returning None.
    """
    if restaurant is None:
        return None

    return (
        Subscription.objects
        .filter(restaurant=restaurant)
        .order_by("-created_at", "-id")
        .first()
    )


def subscription_is_valid(subscription, now=None):
    """
    A subscription is valid only when:

    - It exists
    - Its status is active or trialing
    - Its current_period_end is either unset or later than now

    Calling expire_if_needed() ensures a completed trial/period becomes expired
    before this function decides access.
    """
    if subscription is None:
        return False

    if now is None:
        now = timezone.now()

    subscription.expire_if_needed()

    subscription.refresh_from_db(
        fields=[
            "status",
            "current_period_end",
        ]
    )

    valid_statuses = {
        Subscription.SubscriptionStatus.ACTIVE,
        Subscription.SubscriptionStatus.TRIALING,
    }

    if subscription.status not in valid_statuses:
        return False

    period_end = subscription.current_period_end

    if period_end is not None and period_end <= now:
        return False

    return True


def object_restaurant(obj):
    """
    Resolve the restaurant from common direct and indirect relationships.
    """
    restaurant = getattr(obj, "restaurant", None)

    if restaurant is not None:
        return restaurant

    for relation_name in (
        "order",
        "menu",
        "table",
        "product",
    ):
        related_object = getattr(
            obj,
            relation_name,
            None,
        )

        if related_object is not None:
            restaurant = getattr(
                related_object,
                "restaurant",
                None,
            )

            if restaurant is not None:
                return restaurant

    return None


def user_can_access_object(user, obj):
    """
    Platform authorities can access all records.

    Other users can access only objects belonging to their assigned
    restaurant.
    """
    if not is_authenticated(user):
        return False

    if is_global_authority(user):
        return True

    user_restaurant = get_user_restaurant(user)

    if user_restaurant is None:
        return False

    return object_restaurant(obj) == user_restaurant


# ============================================================================
# Django admin base class
# ============================================================================


class RoleRestrictedAdmin(admin.ModelAdmin):
    """
    Global authorities can manage all records.

    Restaurant managers can only view/manage records belonging to their
    assigned restaurant, if the model has a `restaurant` field.
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
        return bool(
            is_global_authority(request.user)
            or is_manager(request.user)
        )

    def has_view_permission(self, request, obj=None):
        user = request.user

        if not (
            is_global_authority(user)
            or is_manager(user)
        ):
            return False

        if obj is None:
            return True

        return user_can_access_object(user, obj)

    def has_add_permission(self, request):
        return bool(
            is_global_authority(request.user)
            or is_manager(request.user)
        )

    def has_change_permission(self, request, obj=None):
        user = request.user

        if is_global_authority(user):
            return True

        if not is_manager(user):
            return False

        if obj is None:
            return True

        return user_can_access_object(user, obj)

    def has_delete_permission(self, request, obj=None):
        user = request.user

        if is_global_authority(user):
            return True

        if not is_manager(user):
            return False

        if obj is None:
            return True

        return user_can_access_object(user, obj)

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        user = request.user

        if not change and not is_global_authority(user):
            restaurant = get_user_restaurant(user)

            if restaurant is not None:
                model_fields = {
                    field.name
                    for field in obj._meta.get_fields()
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
# Basic DRF permissions
# ============================================================================


class IsAuthenticatedUser(BasePermission):
    message = "Authentication credentials were not provided."

    def has_permission(self, request, view):
        return is_authenticated(request.user)


class IsGlobalAuthority(BasePermission):
    message = "Global platform authority is required."

    def has_permission(self, request, view):
        return is_global_authority(request.user)


class IsStaffOrGlobalAuthority(BasePermission):
    """
    For internal platform administration endpoints.

    This allows a Django staff account or global platform authority. Do not use
    this permission for ordinary restaurant business endpoints unless that is
    explicitly intended.
    """

    message = "Platform staff access is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            is_authenticated(user)
            and (
                user.is_staff
                or is_global_authority(user)
            )
        )


class HasRestaurant(BasePermission):
    message = "You are not assigned to a restaurant."

    def has_permission(self, request, view):
        return has_restaurant(request.user)


# ============================================================================
# Subscription permission
# ============================================================================


class HasActiveSubscription(BasePermission):
    """
    Allow access only when the restaurant subscription is active or trialing
    and its current period has not ended.

    Superusers and platform owners bypass the check.
    """

    message = (
        "Your free trial or subscription has ended. "
        "Select a plan and complete payment to continue using BEEPOS."
    )

    def has_permission(self, request, view):
        user = request.user

        if not is_authenticated(user):
            self.message = (
                "Authentication credentials were not provided."
            )
            return False

        # Platform-level accounts always retain access.
        if is_global_authority(user):
            return True

        restaurant = get_user_restaurant(user)

        if restaurant is None:
            self.message = (
                "Your account is not assigned to a restaurant."
            )
            return False

        subscription = get_restaurant_subscription(restaurant)

        if subscription is None:
            self.message = (
                "No subscription was found for this restaurant."
            )
            return False

        if not subscription_is_valid(subscription):
            self.message = (
                "Your trial or subscription has expired. "
                "Choose a plan to restore access."
            )
            return False

        return True


# Keep this alias while views are migrated to HasActiveSubscription.
HasActiveSubscriptionOrTrial = HasActiveSubscription


class IsAuthorizedToAccessRestaurant(BasePermission):
    """
    Compatibility permission for existing views.

    Allows:
    - Superusers and platform owners
    - Restaurant managers whose restaurant has a valid active/trialing
      subscription

    This intentionally uses the same subscription rules as
    HasActiveSubscription.
    """

    message = "You are not authorized to access this restaurant."

    def has_permission(self, request, view):
        user = request.user

        if not is_authenticated(user):
            self.message = (
                "Authentication credentials were not provided."
            )
            return False

        # Platform-level authority bypass.
        if is_global_authority(user):
            return True

        # This permission is for manager-level restaurant access.
        if not is_manager(user):
            self.message = "Manager access is required."
            return False

        restaurant = get_user_restaurant(user)

        if restaurant is None:
            self.message = (
                "Your account is not assigned to a restaurant."
            )
            return False

        subscription = get_restaurant_subscription(restaurant)

        if subscription is None:
            self.message = (
                "No subscription was found for this restaurant."
            )
            return False

        if not subscription_is_valid(subscription):
            self.message = (
                "Your trial or subscription has expired. "
                "Choose a plan to restore access."
            )
            return False

        return True

# ============================================================================
# Restaurant manager permissions
# ============================================================================


class IsManagerOrGlobalAuthority(BasePermission):
    message = "Manager access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)

    def has_object_permission(self, request, view, obj):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageStaff(BasePermission):
    message = "Staff management access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)

    def has_object_permission(self, request, view, obj):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageProducts(BasePermission):
    message = "Product management access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)

    def has_object_permission(self, request, view, obj):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageTables(BasePermission):
    message = "Table management access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)

    def has_object_permission(self, request, view, obj):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanManageSettings(BasePermission):
    message = "Restaurant settings access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)

    def has_object_permission(self, request, view, obj):
        return user_can_access_object(
            request.user,
            obj,
        )


class CanViewReports(BasePermission):
    message = "Financial reports access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)


class CanViewDashboard(BasePermission):
    message = "Dashboard access is required."

    def has_permission(self, request, view):
        return is_manager(request.user)


# ============================================================================
# POS, orders, cashier, and kitchen permissions
# ============================================================================


class CanAccessPOS(BasePermission):
    message = "POS access is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cashier(user)
            or is_server(user)
        )


class CanAccessCashierShift(BasePermission):
    message = "Cashier or manager access is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cashier(user)
        )


class CanAccessKitchen(BasePermission):
    message = "Kitchen access is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cook(user)
        )


class CanAccessOrders(BasePermission):
    message = "Order access is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            is_global_authority(user)
            or is_manager(user)
            or is_cook(user)
            or is_cashier(user)
            or is_server(user)
        )

    def has_object_permission(self, request, view, obj):
        return user_can_access_object(
            request.user,
            obj,
        )


# ============================================================================
# Combined role and subscription permissions
# ============================================================================


class IsManagerWithSubscription(BasePermission):
    message = (
        "Manager access with an active subscription is required."
    )

    def has_permission(self, request, view):
        manager_permission = IsManagerOrGlobalAuthority()
        subscription_permission = HasActiveSubscription()

        if not manager_permission.has_permission(
            request,
            view,
        ):
            self.message = manager_permission.message
            return False

        if not subscription_permission.has_permission(
            request,
            view,
        ):
            self.message = subscription_permission.message
            return False

        return True


class CanAccessPOSWithSubscription(BasePermission):
    message = (
        "POS access with an active subscription is required."
    )

    def has_permission(self, request, view):
        role_permission = CanAccessPOS()
        subscription_permission = HasActiveSubscription()

        if not role_permission.has_permission(
            request,
            view,
        ):
            self.message = role_permission.message
            return False

        if not subscription_permission.has_permission(
            request,
            view,
        ):
            self.message = subscription_permission.message
            return False

        return True


class CanAccessKitchenWithSubscription(BasePermission):
    message = (
        "Kitchen access with an active subscription is required."
    )

    def has_permission(self, request, view):
        role_permission = CanAccessKitchen()
        subscription_permission = HasActiveSubscription()

        if not role_permission.has_permission(
            request,
            view,
        ):
            self.message = role_permission.message
            return False

        if not subscription_permission.has_permission(
            request,
            view,
        ):
            self.message = subscription_permission.message
            return False

        return True