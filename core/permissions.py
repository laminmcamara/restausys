"""
permissions.py

Custom role-based admin access control for the Global Restaurant Management Platform.
"""

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from .models import CustomUser


class RoleRestrictedAdmin(admin.ModelAdmin):
    """
    A base admin class that automatically enforces role-based view, add, change, and delete permissions.
    """

    def has_module_permission(self, request):
        """Managers and Super Admins can see the module."""
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.role in [
            CustomUser.Roles.SUPER_ADMIN,
            CustomUser.Roles.MANAGER
        ]

    def has_view_permission(self, request, obj=None):
        user = request.user
        if user.is_superuser or user.role in [
            CustomUser.Roles.SUPER_ADMIN,
            CustomUser.Roles.MANAGER,
            CustomUser.Roles.CASHIER,
            CustomUser.Roles.SERVER,
        ]:
            return True
        return False

    def has_add_permission(self, request):
        user = request.user
        return user.is_superuser or user.role in [
            CustomUser.Roles.SUPER_ADMIN,
            CustomUser.Roles.MANAGER
        ]

    def has_change_permission(self, request, obj=None):
        user = request.user
        return user.is_superuser or user.role in [
            CustomUser.Roles.SUPER_ADMIN,
            CustomUser.Roles.MANAGER
        ]

    def has_delete_permission(self, request, obj=None):
        user = request.user
        return user.is_superuser or user.role in [
            CustomUser.Roles.SUPER_ADMIN,
            CustomUser.Roles.MANAGER
        ]