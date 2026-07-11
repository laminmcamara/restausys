from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.utils.safestring import mark_safe

from .models import (
    Company,
    Restaurant,
    CustomUser,
    Payment,
    Refund,
    AnalyticsSnapshot,
    AuditLog,
)

# ==============================================================================
# SUPERUSER-ONLY BASE ADMIN
# ==============================================================================

class SuperuserOnlyAdmin(admin.ModelAdmin):
    """
    Django Admin is now SYSTEM-LEVEL ONLY.
    Only superusers can access it.
    """

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ==============================================================================
# AUDIT MIXIN
# ==============================================================================

class AuditAdminMixin:
    """
    Logs CREATE, UPDATE, DELETE actions automatically.
    """

    def save_model(self, request, obj, form, change):
        is_create = not change

        old_data = {}
        if change:
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                old_data = model_to_dict(old_obj)
            except self.model.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        new_data = model_to_dict(obj)

        changes = {}

        if change:
            for field, old_value in old_data.items():
                new_value = new_data.get(field)
                if old_value != new_value:
                    changes[field] = {
                        "old": str(old_value),
                        "new": str(new_value),
                    }

        AuditLog.objects.create(
            user=request.user,
            restaurant=getattr(obj, "restaurant", None),
            action="CREATE" if is_create else "UPDATE",
            model_name=self.model.__name__,
            object_id=str(obj.pk),
            changes=changes if changes else None,
        )

    def delete_model(self, request, obj):
        AuditLog.objects.create(
            user=request.user,
            restaurant=getattr(obj, "restaurant", None),
            action="DELETE",
            model_name=self.model.__name__,
            object_id=str(obj.pk),
        )
        super().delete_model(request, obj)


# ==============================================================================
# SYSTEM-LEVEL ADMINS
# ==============================================================================

@admin.register(Company)
class CompanyAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "company",
        "city",
        "country",
        "status",
    )

    list_filter = (
        "status",
        "country",
        "company",
    )

    search_fields = (
        "name",
        "city",
        "company__name",
    )

    autocomplete_fields = ("company",)
    prepopulated_fields = {"slug": ("name",)}
    
@admin.register(CustomUser)
class CustomUserAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = ("username", "email", "role", "restaurant", "is_active", "is_staff")
    list_filter = ("role", "is_active", "restaurant")
    search_fields = ("username", "email")
    autocomplete_fields = ["restaurant"]

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied("Only system administrators can modify users.")
        super().save_model(request, obj, form, change)


# ==============================================================================
# SYSTEM PAYMENTS & FINANCIALS
# ==============================================================================

@admin.register(Payment)
class PaymentAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "id",
        "get_restaurant",
        "order",
        "method",
        "amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "method",
        "created_at",
    )

    search_fields = (
        "order__id",
        "reference",
        "stripe_payment_intent",
    )

    readonly_fields = ("created_at",)

    def get_restaurant(self, obj):
        return obj.order.restaurant

    get_restaurant.short_description = "Restaurant"

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Refund)
class RefundAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "get_restaurant",
        "amount",
        "processed_by",
        "created_at",
    )

    readonly_fields = ("created_at",)

    def get_restaurant(self, obj):
        return obj.order.restaurant  # adjust if needed

    get_restaurant.short_description = "Restaurant"

    def has_delete_permission(self, request, obj=None):
        return False
    
@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(SuperuserOnlyAdmin):
    list_display = (
        "restaurant",
        "date",
        "total_orders",
        "total_revenue",
        "average_order_value",
    )
    list_filter = ("restaurant", "date")
    ordering = ("-date",)


# ==============================================================================
# AUDIT LOG (READ-ONLY)
# ==============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(SuperuserOnlyAdmin):
    list_display = (
        "timestamp",
        "user",
        "restaurant",
        "action",
        "model_name",
        "object_id",
    )

    list_filter = ("action", "restaurant", "timestamp")
    search_fields = ("model_name", "object_id", "user__username")

    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False