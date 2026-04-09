from django.contrib import admin
from django.utils.safestring import mark_safe

from .permissions import RoleRestrictedAdmin  

from django.forms.models import model_to_dict
from django.core.exceptions import PermissionDenied

from .models import (
    Company, Restaurant, CustomUser, Table,
    Menu, Category, Cuisine, Product,
    ModifierGroup, ModifierOption,
    InventoryItem, RecipeItem, MultiCurrencyPrice,
    Order, OrderItem, KitchenTicket, Payment,
    Attendance,
    Customer, LoyaltyTier,
    Rider, Refund,
    AnalyticsSnapshot, APIToken,
    ChatMessage, PaymentMethod,
    AuditLog,
    CashierShift,
)


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
# MULTI-TENANT BASE ADMIN
# ==============================================================================

class RestaurantRestrictedAdmin(AuditAdminMixin, admin.ModelAdmin):
    """
    SaaS-grade multi-tenant isolation.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if hasattr(self.model, "restaurant"):
            return qs.filter(restaurant=request.user.restaurant)

        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(obj, "restaurant"):
            obj.restaurant = request.user.restaurant

        # attach actor for audit logging
        obj._actor = request.user
        super().save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.role in [
            CustomUser.Roles.MANAGER,
            CustomUser.Roles.CASHIER,
            CustomUser.Roles.COOK,
        ]

    def has_delete_permission(self, request, obj=None):
        # Never allow deletion of finalized financial records
        if obj and hasattr(obj, "status"):
            if str(obj.status).upper() in ["PAID", "COMPLETED"]:
                return False
        return super().has_delete_permission(request, obj)

# ==============================================================================
# INLINE MODELS
# ==============================================================================

class ModifierOptionInline(admin.TabularInline):
    model = ModifierOption
    extra = 1
    fields = ('name', 'price_adjustment', 'display_order')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('final_price', 'display_modifiers')
    fields = ('product', 'quantity', 'final_price', 'display_modifiers', 'notes')
    autocomplete_fields = ['product']

    def display_modifiers(self, obj):
        if not obj.pk:
            return "Save to view selected modifiers."
        mods = obj.modifiers.all()
        if not mods:
            return "None"
        return mark_safe("<br>".join(
            [f"&bull; {m.name} (+{m.price_adjustment})" for m in mods]
        ))

    display_modifiers.short_description = "Selected Modifiers"


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1
    autocomplete_fields = ['ingredient']


class MultiCurrencyPriceInline(admin.TabularInline):
    model = MultiCurrencyPrice
    extra = 1


# ==============================================================================
# MENU SYSTEM ADMINS
# ==============================================================================

@admin.register(Menu)
class MenuAdmin(RestaurantRestrictedAdmin):
    list_display = ('name', 'restaurant', 'is_active')
    list_filter = ('restaurant', 'is_active')
    search_fields = ('name',)


@admin.register(Category)
class CategoryAdmin(RestaurantRestrictedAdmin):
    list_display = ('get_full_path', 'menu', 'display_order')
    list_filter = ('menu__restaurant', 'menu')
    search_fields = ('name', 'parent__name')
    ordering = ('menu', 'parent__name', 'display_order', 'name')
    autocomplete_fields = ['menu', 'parent']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('menu', 'parent')

    @admin.display(description='Category Path', ordering='name')
    def get_full_path(self, obj):
        path = [obj.name]
        ancestor = obj.parent
        while ancestor:
            path.insert(0, ancestor.name)
            ancestor = ancestor.parent
        return ' > '.join(path)


@admin.register(Product)
class ProductAdmin(RestaurantRestrictedAdmin):
    list_display = ('name', 'category', 'base_price', 'is_available', 'halal')
    list_filter = ('category__menu__restaurant', 'category__menu', 'is_available', 'halal')
    list_editable = ('base_price', 'is_available')
    search_fields = ('name', 'description', 'category__name')
    ordering = ('category', 'display_order', 'name')
    autocomplete_fields = ['category']
    filter_horizontal = ('cuisines',)
    inlines = [RecipeItemInline, MultiCurrencyPriceInline]

    actions = ['make_unavailable', 'make_available']

    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)

    def make_available(self, request, queryset):
        queryset.update(is_available=True)


@admin.register(ModifierGroup)
class ModifierGroupAdmin(RestaurantRestrictedAdmin):
    list_display = ('name', 'selection_type')
    search_fields = ('name',)
    filter_horizontal = ('products',)
    inlines = [ModifierOptionInline]


# ==============================================================================
# ORDER SYSTEM
# ==============================================================================

@admin.register(Order)
class OrderAdmin(RestaurantRestrictedAdmin):
    list_display = (
        'short_id',
        'restaurant',
        'table',
        'status',
        'created_at',
        'display_total_price'
    )
    list_filter = ('status', 'restaurant', 'created_at', 'table')
    search_fields = ('id__startswith', 'table__table_number', 'customer__full_name')
    ordering = ('-created_at',)
    date_hierarchy = "created_at"
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'restaurant',
            'table',
            'customer'
        )

    @admin.display(description="Order ID")
    def short_id(self, obj):
        return str(obj.id)[:8]

    @admin.display(description="Total")
    def display_total_price(self, obj):
        total = obj.total_price()
        if obj.restaurant and obj.restaurant.currency:
            return f"{obj.restaurant.currency} {total:.2f}"
        return f"{total:.2f}"

    def has_change_permission(self, request, obj=None):
        if request.user.role == CustomUser.Roles.COOK:
            return False
        return super().has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == CustomUser.Roles.COOK:
            return qs.filter(status="IN_PROGRESS")
        return qs
    
    
# ==============================================================================
# MAIN SYSTEM ADMINS
# ==============================================================================

@admin.register(CustomUser)
class CustomUserAdmin(RestaurantRestrictedAdmin):
    list_display = ('username', 'email', 'role', 'restaurant', 'is_staff')
    list_filter = ('role', 'is_staff', 'restaurant')
    search_fields = ('username', 'email')
    autocomplete_fields = ['restaurant']

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.restaurant = request.user.restaurant

            if obj.role == CustomUser.Roles.MANAGER:
                raise PermissionDenied("Managers cannot create other managers.")

            obj.is_superuser = False

        obj._actor = request.user
        super().save_model(request, obj, form, change)
        
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    def has_module_permission(self, request):
        return request.user.is_superuser

@admin.register(InventoryItem)
class InventoryItemAdmin(RestaurantRestrictedAdmin):
    list_display = ('name', 'restaurant', 'quantity', 'unit', 'reorder_level', 'is_below_reorder')
    list_filter = ('restaurant',)
    search_fields = ('name',)

    def is_below_reorder(self, obj):
        return obj.quantity <= obj.reorder_level

    is_below_reorder.boolean = True


@admin.register(KitchenTicket)
class KitchenTicketAdmin(RestaurantRestrictedAdmin):
    list_display = ('id', 'order', 'created_at', 'printed')
    list_filter = ('printed', 'created_at')
    search_fields = ('order__id',)
    autocomplete_fields = ['order']


@admin.register(Payment)
class PaymentAdmin(RestaurantRestrictedAdmin):
    list_display = (
        "id",
        "order",
        "method",
        "amount",
        "status",
        "stripe_payment_intent",
        "created_at",
    )

    list_filter = ("status", "method", "created_at")
    search_fields = ("order__id", "stripe_payment_intent", "reference")

    readonly_fields = (
        "stripe_payment_intent",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = ["order"]

    def has_delete_permission(self, request, obj=None):
        return False  # Never delete financial records

@admin.register(CashierShift)
class CashierShiftAdmin(RestaurantRestrictedAdmin):
    list_display = (
        "user",
        "restaurant",
        "start_time",
        "end_time",
        "starting_cash",
        "closing_cash",
        "is_active",
    )

    list_filter = ("restaurant", "is_active", "start_time")
    search_fields = ("user__username",)
    readonly_fields = ("start_time",)

    def has_delete_permission(self, request, obj=None):
        return False  # Financial shift records should not be deleted


@admin.register(Attendance)
class AttendanceAdmin(RestaurantRestrictedAdmin):
    list_display = ('employee', 'restaurant', 'check_in', 'check_out')
    list_filter = ('restaurant',)
    search_fields = ('employee__username',)


@admin.register(Customer)
class CustomerAdmin(RestaurantRestrictedAdmin):
    list_display = ('full_name', 'email', 'phone', 'loyalty_points', 'total_spent')
    search_fields = ('full_name', 'email')


@admin.register(Rider)
class RiderAdmin(RestaurantRestrictedAdmin):
    list_display = ('name', 'restaurant', 'phone', 'active', 'current_order')
    list_filter = ('restaurant', 'active')
    search_fields = ('name', 'phone')


@admin.register(Refund)
class RefundAdmin(RestaurantRestrictedAdmin):
    list_display = (
        "order",
        "amount",
        "processed_by",
        "created_at"
    )

    readonly_fields = ("created_at",)

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(RestaurantRestrictedAdmin):
    list_display = ('restaurant', 'date', 'total_orders', 'total_revenue', 'average_order_value')
    list_filter = ('restaurant', 'date')
    ordering = ('-date',)


@admin.register(APIToken)
class APITokenAdmin(RestaurantRestrictedAdmin):
    list_display = ('device_name', 'restaurant', 'token', 'active', 'last_used')
    list_filter = ('restaurant', 'active')
    readonly_fields = ('token',)


@admin.register(ChatMessage)
class ChatMessageAdmin(RestaurantRestrictedAdmin):
    list_display = ('timestamp', 'restaurant', 'sender', 'content_short', 'important')
    list_filter = ('restaurant', 'important')
    search_fields = ('content',)

    def content_short(self, obj):
        return obj.content[:50]


# ==============================================================================
# TABLE ADMIN
# ==============================================================================

@admin.register(Table)
class TableAdmin(RestaurantRestrictedAdmin):
    list_display = ("table_number", "restaurant", "status", "qr_code_preview")
    list_filter = ("status", "restaurant")
    search_fields = ("table_number",)
    readonly_fields = ("qr_code_preview",)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return mark_safe(
                f'<img src="{obj.qr_code.url}" width="150" height="150">'
            )
        return "No QR code generated yet."
    
    
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
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

    def has_module_permission(self, request):
        user = request.user

        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return getattr(user, "role", None) == CustomUser.Roles.MANAGER