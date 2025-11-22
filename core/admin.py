# core/admin.py
import csv
import logging
from django.utils import timezone
from django.http import HttpResponse

from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from django.core.exceptions import PermissionDenied
import uuid
 
# from .dashboard import DashboardMixin
from .models import (
    Company, CustomUser, Customer,
    Restaurant, Table,
    Cuisine, Category, MenuItem, RecipeItem, InventoryItem,
    MenuVariant, MultiCurrencyPrice,
    Order, OrderItem, Payment,
    AnalyticsSnapshot, APIToken,
    KitchenTicket, Attendance, ChatMessage
)

# =============================================================================
# === ROLE‑BASED PERMISSION SYSTEM ============================================
# =============================================================================

class RoleRestrictedAdmin(admin.ModelAdmin):
    """Base admin with role‑based control."""

    def has_module_permission(self, request):
        u = request.user
        return u.is_authenticated and (u.is_superuser or u.role in [
            CustomUser.Roles.SUPER_ADMIN,
            CustomUser.Roles.MANAGER
        ])

    def has_view_permission(self, request, obj=None):
        u = request.user
        return u.is_authenticated and (
            u.is_superuser or u.role in [
                CustomUser.Roles.SUPER_ADMIN, CustomUser.Roles.MANAGER,
                CustomUser.Roles.SERVER, CustomUser.Roles.CASHIER, CustomUser.Roles.COOK
            ]
        )

    def has_add_permission(self, request):
        u = request.user
        return u.is_superuser or u.role in [
            CustomUser.Roles.SUPER_ADMIN, CustomUser.Roles.MANAGER
        ]

    def has_change_permission(self, request, obj=None):
        u = request.user
        return u.is_superuser or u.role in [
            CustomUser.Roles.SUPER_ADMIN, CustomUser.Roles.MANAGER
        ]

    def has_delete_permission(self, request, obj=None):
        u = request.user
        return u.is_superuser or u.role in [
            CustomUser.Roles.SUPER_ADMIN, CustomUser.Roles.MANAGER
        ]


class RestaurantScopedAdmin(RoleRestrictedAdmin):
    """Restrict queryset visibility by assigned restaurant."""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        u = request.user
        if u.is_superuser or u.role == CustomUser.Roles.SUPER_ADMIN:
            return qs
        if hasattr(u, "restaurant") and u.restaurant:
            return qs.filter(restaurant=u.restaurant)
        if hasattr(u, "company") and u.company:
            return qs.filter(restaurant__company=u.company)
        return qs.none()


# =============================================================================
# === GLOBAL UTILITIES ========================================================
# =============================================================================

@admin.action(description="Mark selected as inactive")
def mark_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.action(description="Mark selected as active")
def mark_active(modeladmin, request, queryset):
    queryset.update(is_active=True)


# =============================================================================
# === COMPANY & USER ADMIN ====================================================
# =============================================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "registration_number", "email", "active", "created_at")
    list_filter = ("active", "created_at")
    search_fields = ("name", "registration_number")
    ordering = ("name",)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "company", "is_active", "is_staff")
    list_filter = ("role", "company", "is_active")
    search_fields = ("username", "email", "phone_number")
    readonly_fields = ("last_login", "date_joined")
    list_editable = ("is_active",)
    ordering = ("-date_joined",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "restaurant", "check_in", "check_out")
    list_filter = ("restaurant", "check_in")
    search_fields = ("employee__username", "restaurant__name")


# =============================================================================
# === CUSTOMER ADMIN ==========================================================
# =============================================================================

@admin.register(Customer)
class CustomerAdmin(RoleRestrictedAdmin):
    list_display = ("full_name", "email", "phone", "loyalty_points", "total_spent", "created_at")
    search_fields = ("full_name", "email", "phone")
    list_filter = ("preferred_language",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    @admin.action(description="Reset loyalty points to 0")
    def reset_loyalty_points(self, request, queryset):
        queryset.update(loyalty_points=0)


# =============================================================================
# === RESTAURANT & TABLE ADMIN ===============================================
# =============================================================================

class TableInline(admin.TabularInline):
    model = Table
    extra = 1
    readonly_fields = ("qr_code_preview",)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="80" height="80" />', obj.qr_code.url)
        return "-"
    qr_code_preview.short_description = "QR Code"


@admin.register(Restaurant)
class RestaurantAdmin(RoleRestrictedAdmin):
    list_display = ("name", "company", "city", "currency", "status")
    list_filter = ("company", "status")
    search_fields = ("name", "city")
    readonly_fields = ("created_at",)
    inlines = [TableInline]
    ordering = ("company", "name")


# =============================================================================
# === INVENTORY & RECIPE ADMIN ===============================================
# =============================================================================

@admin.register(InventoryItem)
class InventoryItemAdmin(RestaurantScopedAdmin):
    list_display = ("name", "restaurant", "quantity", "unit", "reorder_level", "last_updated")
    list_filter = ("restaurant", "category")
    search_fields = ("name",)
    ordering = ("restaurant", "name")


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 2
    autocomplete_fields = ["ingredient"]
    fields = ("ingredient", "quantity_used", "unit")


# =============================================================================
# === MENU / CATEGORY ADMIN ==================================================
# =============================================================================

class MultiCurrencyPriceInline(admin.TabularInline):
    model = MultiCurrencyPrice
    extra = 1
    fields = ("currency", "price", "exchange_rate", "updated_at")
    readonly_fields = ("updated_at",)


class MenuVariantInline(admin.TabularInline):
    model = MenuVariant
    extra = 2
    fields = ("name", "price_modifier", "stock", "is_active")


@admin.register(MenuItem)
class MenuItemAdmin(RestaurantScopedAdmin):
    list_display = ("name", "restaurant", "category", "available", "halal", "base_price")
    list_filter = ("available", "halal", "restaurant", "category", "cuisines")
    search_fields = ("name", "description")
    actions = [mark_active, mark_inactive]
    inlines = [RecipeItemInline, MenuVariantInline, MultiCurrencyPriceInline]
    list_editable = ("available", "halal")
    ordering = ("restaurant", "name")


@admin.register(Category)
class CategoryAdmin(RoleRestrictedAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Cuisine)
class CuisineAdmin(RoleRestrictedAdmin):
    list_display = ("name", "region", "halal_certified")
    list_filter = ("region", "halal_certified")
    search_fields = ("name", "region")


# =============================================================================
# === ORDERS, PAYMENTS, KITCHEN ADMIN ========================================
# =============================================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("final_price_display",)

    def final_price_display(self, obj):
        return format_html("<b>{}</b>", obj.final_price)
    final_price_display.short_description = "Final Price"


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(KitchenTicket)
class KitchenTicketAdmin(admin.ModelAdmin):
    list_display = ("order", "created_at", "printed")
    list_filter = ("printed", "created_at")


@admin.register(Order)
class OrderAdmin(RestaurantScopedAdmin):
    list_display = ("short_id", "restaurant", "customer", "status", "created_at", "total_price_display")
    list_filter = ("status", "restaurant", "created_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline, PaymentInline]
    search_fields = ("id", "customer__full_name")
    ordering = ("-created_at",)

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "Order ID"

    def total_price_display(self, obj):
        return format_html("<strong>{}</strong>", obj.total_price())
    total_price_display.short_description = "Total (incl. tax)"


@admin.register(Payment)
class PaymentAdmin(RestaurantScopedAdmin):
    list_display = ("order", "amount", "method", "status", "created_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("order__id", "reference")
    ordering = ("-created_at",)


# =============================================================================
# === ANALYTICS & API TOKEN ADMIN ============================================
# =============================================================================

@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(RestaurantScopedAdmin):
    list_display = ("restaurant", "date", "total_orders", "total_revenue",
                    "average_order_value", "top_selling_item", "last_updated")
    list_filter = ("restaurant", "date")
    readonly_fields = ("last_updated",)
    ordering = ("-date",)


@admin.register(APIToken)
class APITokenAdmin(RestaurantScopedAdmin):
    list_display = ("device_name", "restaurant", "token", "active", "last_used", "created_at")
    list_filter = ("active", "restaurant")
    search_fields = ("device_name", "token")
    readonly_fields = ("token", "created_at", "last_used")

    @admin.action(description="Rotate (Regenerate) selected tokens")
    def rotate_tokens(self, request, queryset):
        for obj in queryset:
            obj.token = uuid.uuid4()
            obj.save(update_fields=["token"])
        self.message_user(request, f"Rotated {queryset.count()} tokens successfully.")

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Read-only, filterable staff chat audit view with CSV export."""

    list_display = (
        "timestamp",
        "sender",
        "restaurant",
        "short_message",
        "system_generated",
        "important",
    )
    list_filter = ("restaurant", "system_generated", "important")
    search_fields = ("content", "sender__username", "restaurant__name")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    readonly_fields = [f.name for f in ChatMessage._meta.get_fields()]
    actions = ["export_selected_to_csv"]

    # --------------------------------------------------------------------------
    # Permissions (read-only)
    # --------------------------------------------------------------------------
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # --------------------------------------------------------------------------
    # Display helpers
    # --------------------------------------------------------------------------
    @admin.display(description="Message")
    def short_message(self, obj):
        """Truncate long chat messages for list display."""
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content

    # --------------------------------------------------------------------------
    # CSV Export Action
    # --------------------------------------------------------------------------
    def export_selected_to_csv(self, request, queryset):
        """
        Exports the selected ChatMessage objects to a downloadable CSV file.
        Only visible to superusers or staff with 'view_chatmessage' permission.
        """
        if not request.user.is_superuser and not request.user.has_perm("core.view_chatmessage"):
            self.message_user(request, "🚫 You do not have permission to export chat logs.", level="error")
            return None

        response = HttpResponse(content_type="text/csv")
        filename = f"chat_messages_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(["Timestamp", "Sender", "Restaurant", "System", "Important", "Content"])

        for msg in queryset.select_related("sender", "restaurant"):
            writer.writerow([
                msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                msg.sender.username if msg.sender else "System",
                msg.restaurant.name if msg.restaurant else "",
                "Yes" if msg.system_generated else "No",
                "Yes" if msg.important else "No",
                msg.content.replace("\n", " "),
            ])

        # ✅ AUDIT LOG ENTRY (inside the method)
        audit_logger = logging.getLogger("audit")
        audit_logger.info(
            f"User {request.user.username} exported {queryset.count()} chat messages "
            f"on {timezone.now():%Y-%m-%d %H:%M} from IP={request.META.get('REMOTE_ADDR')}"
        )

        return response

    export_selected_to_csv.short_description = "⬇️ Export selected chat messages to CSV"
    
# =============================================================================
# === INLINE SUPPORT REGISTRATION ============================================
# =============================================================================
admin.site.register(MenuVariant)
admin.site.register(MultiCurrencyPrice)


# =============================================================================
# === ADMIN DASHBOARD SETUP ===================================================
# =============================================================================
# from .dashboard import DashboardMixin

# admin.site.__class__ = type(
#    "CustomAdminSite",
#    (DashboardMixin, admin.AdminSite),
#    {},
# )