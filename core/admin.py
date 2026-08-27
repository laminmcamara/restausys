from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict

from .models import (
    Company,
    Restaurant,
    CustomUser,
    Payment,
    Refund,
    AnalyticsSnapshot,
    AuditLog,
    Printer,
    PrintJob,
    Subscription,
    Plan,
    WebhookConfiguration, WebhookEvent,
)


# ==============================================================================
# ADMIN SITE BRANDING
# ==============================================================================

admin.site.site_header = "BEEPOS Administration"
admin.site.site_title = "BEEPOS Admin"
admin.site.index_title = "BEEPOS System Dashboard"


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
class RestaurantAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "id",
        "name",
        "company",
        "city",
        "country",
        "status",
        "subscription_status",
        "subscription_active",
        "subscription_period_end",
        "subscription_days_remaining",
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

    def subscription_status(self, obj):
        try:
            obj.subscription.expire_if_needed()
            return obj.subscription.status
        except Subscription.DoesNotExist:
            return "No Subscription"

    subscription_status.short_description = "Subscription Status"

    def subscription_active(self, obj):
        try:
            obj.subscription.expire_if_needed()
            return obj.subscription.is_active()
        except Subscription.DoesNotExist:
            return False

    subscription_active.boolean = True
    subscription_active.short_description = "Subscription Active"

    def subscription_period_end(self, obj):
        try:
            obj.subscription.expire_if_needed()
            return obj.subscription.current_period_end
        except Subscription.DoesNotExist:
            return None

    subscription_period_end.short_description = "Subscription Ends"

    def subscription_days_remaining(self, obj):
        try:
            obj.subscription.expire_if_needed()
            return obj.subscription.days_remaining
        except Subscription.DoesNotExist:
            return 0

    subscription_days_remaining.short_description = "Days Remaining"


@admin.register(CustomUser)
class CustomUserAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "restaurant",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "is_active",
        "restaurant",
    )

    search_fields = (
        "username",
        "email",
    )

    autocomplete_fields = ["restaurant"]

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied("Only system administrators can modify users.")
        super().save_model(request, obj, form, change)


# ==============================================================================
# SUBSCRIPTIONS - MANUAL/OFFLINE ONLY
# ==============================================================================

@admin.register(Subscription)
class SubscriptionAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "id",
        "restaurant",
        "plan",
        "status",
        "current_period_start",
        "current_period_end",
        "trial_start",
        "trial_end",
        "days_remaining",
        "offline_payment_method",
        "reactivated_by",
        "last_reactivated_at",
        "created_at",
    )

    list_filter = (
        "status",
        "plan",
        "offline_payment_method",
        "current_period_end",
        "trial_end",
        "created_at",
    )

    search_fields = (
        "restaurant__name",
        "restaurant__company__name",
        "offline_payment_reference",
        "offline_payment_notes",
    )

    autocomplete_fields = (
        "restaurant",
        "plan",
        "reactivated_by",
    )

    readonly_fields = (
        "trial_start",
        "trial_end",
        "last_reactivated_at",
        "reactivated_by",
        "created_at",
        "updated_at",
    )

    actions = (
        "reactivate_for_30_days_cash",
        "reactivate_for_90_days_cash",
        "reactivate_for_365_days_cash",
        "mark_as_expired",
        "suspend_subscription",
        "cancel_subscription",
    )

    fieldsets = (
        ("Restaurant / Plan", {
            "fields": (
                "restaurant",
                "plan",
                "status",
            )
        }),
        ("Current Access Period", {
            "fields": (
                "current_period_start",
                "current_period_end",
            )
        }),
        ("Original Free Trial Period", {
            "fields": (
                "trial_start",
                "trial_end",
            )
        }),
        ("Offline Payment / Agreement", {
            "fields": (
                "offline_payment_method",
                "offline_payment_reference",
                "offline_payment_notes",
            )
        }),
        ("Reactivation Tracking", {
            "fields": (
                "last_reactivated_at",
                "reactivated_by",
            )
        }),
        ("System", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    @admin.action(description="Reactivate selected subscriptions for 30 days - Cash/offline")
    def reactivate_for_30_days_cash(self, request, queryset):
        for subscription in queryset:
            subscription.reactivate_offline(
                user=request.user,
                days=30,
                payment_method=Subscription.OfflinePaymentMethod.CASH,
                notes="Manual 30-day offline subscription activation from admin.",
            )

    @admin.action(description="Reactivate selected subscriptions for 90 days - Cash/offline")
    def reactivate_for_90_days_cash(self, request, queryset):
        for subscription in queryset:
            subscription.reactivate_offline(
                user=request.user,
                days=90,
                payment_method=Subscription.OfflinePaymentMethod.CASH,
                notes="Manual 90-day offline subscription activation from admin.",
            )

    @admin.action(description="Reactivate selected subscriptions for 1 year - Cash/offline")
    def reactivate_for_365_days_cash(self, request, queryset):
        for subscription in queryset:
            subscription.reactivate_offline(
                user=request.user,
                days=365,
                payment_method=Subscription.OfflinePaymentMethod.CASH,
                notes="Manual yearly offline subscription activation from admin.",
            )

    @admin.action(description="Mark selected subscriptions as expired")
    def mark_as_expired(self, request, queryset):
        queryset.update(status=Subscription.SubscriptionStatus.EXPIRED)

    @admin.action(description="Suspend selected subscriptions")
    def suspend_subscription(self, request, queryset):
        queryset.update(status=Subscription.SubscriptionStatus.SUSPENDED)

    @admin.action(description="Cancel selected subscriptions")
    def cancel_subscription(self, request, queryset):
        queryset.update(status=Subscription.SubscriptionStatus.CANCELED)

@admin.register(Plan)
class PlanAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "monthly_price",
        "max_users",
        "max_tables",
        "allow_inventory",
        "allow_analytics",
        "is_active",
    )

    list_filter = (
        "is_active",
        "allow_inventory",
        "allow_analytics",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "monthly_price",
    )
    
    
# ==============================================================================
# PRINTERS
# ==============================================================================

@admin.register(Printer)
class PrinterAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "id",
        "name",
        "restaurant",
        "role",
        "connection_type",
        "ip_address",
        "port",
        "is_active",
        "last_seen_at",
    )

    list_filter = (
        "role",
        "connection_type",
        "is_active",
        "restaurant",
    )

    search_fields = (
        "name",
        "restaurant__name",
        "ip_address",
        "system_name",
    )

    autocomplete_fields = (
        "restaurant",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_seen_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "restaurant",
                    "name",
                    "role",
                    "connection_type",
                    "is_active",
                )
            },
        ),
        (
            "Network Settings",
            {
                "fields": (
                    "ip_address",
                    "port",
                )
            },
        ),
        (
            "USB Settings",
            {
                "fields": (
                    "usb_vendor_id",
                    "usb_product_id",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "System Printer Settings",
            {
                "fields": (
                    "system_name",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "last_seen_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

@admin.register(PrintJob)
class PrintJobAdmin(AuditAdminMixin, SuperuserOnlyAdmin):
    list_display = (
        "id",
        "restaurant",
        "printer",
        "job_type",
        "status",
        "title",
        "copies",
        "attempts",
        "max_attempts",
        "printed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "job_type",
        "restaurant",
        "printer",
        "created_at",
        "printed_at",
    )

    search_fields = (
        "title",
        "restaurant__name",
        "printer__name",
        "raw_text",
        "error_message",
    )

    autocomplete_fields = (
        "restaurant",
        "printer",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "printed_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "restaurant",
                    "printer",
                    "job_type",
                    "status",
                    "title",
                    "copies",
                )
            },
        ),
        (
            "Print Content",
            {
                "fields": (
                    "payload",
                    "raw_text",
                )
            },
        ),
        (
            "Retry / Error Handling",
            {
                "fields": (
                    "attempts",
                    "max_attempts",
                    "error_message",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "printed_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    actions = (
        "mark_as_pending",
        "mark_as_cancelled",
    )

    @admin.action(description="Mark selected print jobs as pending")
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(
            status=PrintJob.PrintJobStatus.PENDING,
            error_message="",
        )
        self.message_user(request, f"{updated} print job(s) marked as pending.")

    @admin.action(description="Cancel selected print jobs")
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(
            status=PrintJob.PrintJobStatus.CANCELLED,
        )
        self.message_user(request, f"{updated} print job(s) cancelled.")
        
        
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
        return obj.order.restaurant

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

    list_filter = (
        "restaurant",
        "date",
    )

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

    list_filter = (
        "action",
        "restaurant",
        "timestamp",
    )

    search_fields = (
        "model_name",
        "object_id",
        "user__username",
    )

    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    
    
@admin.register(WebhookConfiguration)
class WebhookConfigurationAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'is_live_enabled', 'is_test_enabled')

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'restaurant', 'status', 'created_at')
    list_filter = ('status', 'environment', 'event_type')
