from django.contrib import admin
from django.utils.safestring import mark_safe

from .permissions import RoleRestrictedAdmin  

from .models import (
    Company, Restaurant, CustomUser, Table,
    Menu, Category, Cuisine, Product,
    ModifierGroup, ModifierOption,
    InventoryItem, RecipeItem, MultiCurrencyPrice,
    Order, OrderItem, KitchenTicket, Payment,
    Shift, Attendance,
    Customer, LoyaltyTier,
    Rider, Refund,
    AnalyticsSnapshot, APIToken,
    ChatMessage, PaymentMethod,
)

# ==============================================================================
# MULTI-TENANT BASE ADMIN
# ==============================================================================

class RestaurantRestrictedAdmin(admin.ModelAdmin):
    """
    Ensures restaurant-level data isolation.
    Superuser (platform owner) sees everything.
    Restaurant users only see their own data.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if hasattr(request.user, "restaurant") and request.user.restaurant:
            if hasattr(self.model, "restaurant"):
                return qs.filter(restaurant=request.user.restaurant)

        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if hasattr(obj, "restaurant"):
                obj.restaurant = request.user.restaurant
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Prevent cross-tenant foreign key selection.
        """
        if not request.user.is_superuser:
            if db_field.name == "restaurant":
                kwargs["queryset"] = Restaurant.objects.filter(
                    id=request.user.restaurant.id
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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


# ==============================================================================
# MAIN SYSTEM ADMINS
# ==============================================================================

@admin.register(CustomUser)
class CustomUserAdmin(RestaurantRestrictedAdmin):
    list_display = ('username', 'email', 'role', 'restaurant', 'is_staff')
    list_filter = ('role', 'is_staff', 'restaurant')
    search_fields = ('username', 'email')
    autocomplete_fields = ['restaurant']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    # Platform-level only (you)
    list_display = ('name', 'email', 'phone', 'active')
    list_filter = ('active',)
    search_fields = ('name',)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    # Platform-level only
    list_display = ('name', 'company', 'status', 'city')
    list_filter = ('company', 'status')
    search_fields = ('name', 'city')
    autocomplete_fields = ['company']


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
    list_display = ("id", "order", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__id", "stripe_payment_intent")
    autocomplete_fields = ['order']


@admin.register(Shift)
class ShiftAdmin(RestaurantRestrictedAdmin):
    list_display = ('employee', 'restaurant', 'role', 'start_time', 'end_time')
    list_filter = ('restaurant', 'role')
    search_fields = ('employee__username',)


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
    list_display = ('order', 'amount', 'processed_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__id', 'processed_by__username')


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