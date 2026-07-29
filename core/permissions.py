from django.contrib import admin
from rest_framework.permissions import BasePermission
from django.utils import timezone
from core.models import Subscription


# ===================================================================
# 1. DJANGO ADMIN PERMISSION BASE
# ===================================================================

class RoleRestrictedAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if hasattr(request.user, "restaurant") and request.user.restaurant:
            return qs.filter(restaurant=request.user.restaurant)

        return qs.none()

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.is_authenticated

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if getattr(request.user, "role", None) == "manager":
            if obj is not None:
                return obj.restaurant == request.user.restaurant
            return True

        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True

        return getattr(request.user, "role", None) == "manager"

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not obj.pk and not request.user.is_superuser:
            if hasattr(request.user, "restaurant"):
                obj.restaurant = request.user.restaurant

        super().save_model(request, obj, form, change)


# ===================================================================
# 2. DRF PERMISSIONS
# ===================================================================

from rest_framework.permissions import BasePermission


from rest_framework.permissions import BasePermission

class IsStaffOfRestaurant(BasePermission):
    message = "Permission denied."

    def has_permission(self, request, view):
        user = request.user

        print("----- PERMISSION DEBUG -----")
        print("User:", user)
        print("Authenticated:", user.is_authenticated)
        print("Restaurant:", getattr(user, "restaurant", None))
        print("Role:", getattr(user, "role", None))
        print("----------------------------")

        if not user or not user.is_authenticated:
            print("FAILED: not authenticated")
            return False

        if user.is_superuser:
            print("PASSED: superuser")
            return True

        if not hasattr(user, "restaurant") or user.restaurant is None:
            print("FAILED: no restaurant")
            return False

        print("PASSED: restaurant exists")
        return True

    def has_object_permission(self, request, view, obj):
        return True
    
    
class IsOwnerOrManager(BasePermission):
    message = "Only a manager can perform this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        role = getattr(user, "role", "")
        return role.strip().lower() == "manager"

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        role = getattr(user, "role", "")
        if role.strip().lower() != "manager":
            return False

        if hasattr(obj, "restaurant"):
            return obj.restaurant == user.restaurant

        return True


# ===================================================================
# 3. SUBSCRIPTION PERMISSION (SaaS Enforcement)
# ===================================================================

class HasActiveSubscription(BasePermission):
    message = "Active subscription required."

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        restaurant = getattr(user, "restaurant", None)

        if not restaurant:
            return False

        subscription = Subscription.objects.filter(
            restaurant=restaurant
        ).first()

        if not subscription:
            return False

        if subscription.status in ["active", "trialing"]:
            if (
                subscription.current_period_end
                and subscription.current_period_end > timezone.now()
            ):
                return True

        return False