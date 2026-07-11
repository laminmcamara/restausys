from django.contrib import admin
from rest_framework.permissions import BasePermission, SAFE_METHODS


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

class IsStaffOfRestaurant(BasePermission):
    message = "You do not have permission to view or edit this object."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not hasattr(obj, "restaurant"):
            return False

        # ✅ Restrict both read & write to same restaurant
        return obj.restaurant == request.user.restaurant


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

        # ✅ Ensure same restaurant (if object has restaurant field)
        if hasattr(obj, "restaurant"):
            return obj.restaurant == user.restaurant

        return True