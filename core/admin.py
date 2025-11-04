# C:\Users\Administrator\restaurant_management\core\admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    CustomUser,
    Shift,
    Restaurant,
    Table,
    MenuItem,
    MenuVariant,
    Order,
    OrderItem,
    KitchenTicket,
    Payment,
    QRToken,
    SalesData,
    Inventory, # Added Inventory to imports list
    ScreenDisplay, # Added ScreenDisplay to imports list
)
from .forms import OrderItemForm

# ==============================================================================
# ADMIN INLINES (These are used within parent models, e.g., Order has OrderItems)
# ==============================================================================

class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('quantity', 'variant_name', 'final_price',)
    fields = ('menu_item', 'quantity', 'variant_name', 'status', 'final_price',)
    autocomplete_fields = ('menu_item',) 


class PaymentInline(TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('amount', 'method', 'paid_at', 'transaction_id',)
    fields = ('amount', 'method', 'status', 'paid_at', 'transaction_id',)


# ==============================================================================
# Admin customizations for unfold
# ==============================================================================

# Unregister the default User and Group to replace them with unfold versions
admin.site.unregister(Group)

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Restaurant Management', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Restaurant Management', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role')


# ==============================================================================
# Standard model registration
# ==============================================================================

@admin.register(Shift)
class ShiftAdmin(ModelAdmin):
    list_display = ('name', 'start_time', 'end_time')
    search_fields = ('name',)


@admin.register(Restaurant)
class RestaurantAdmin(ModelAdmin):
    list_display = ('name', 'city', 'phone_number')
    list_filter = ('city', 'state',)
    search_fields = ('name', 'address_line_1', 'city')


@admin.register(Table)
class TableAdmin(ModelAdmin):
    list_display = ('table_number', 'restaurant', 'capacity', 'status')
    list_filter = ('restaurant', 'status')
    search_fields = ('table_number', 'restaurant__name')


@admin.register(MenuItem)
class MenuItemAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'base_price', 'is_active')
    list_filter = ('restaurant', 'category', 'is_active')
    search_fields = ('name',)


@admin.register(MenuVariant)
class MenuVariantAdmin(ModelAdmin):
    list_display = ('name', 'menu_item', 'price_modifier', 'stock')
    search_fields = ('name', 'menu_item__name')


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'user', 'table', 'created_at', 'status', 'total_price')
    list_filter = ('status', 'table', 'created_at')
    search_fields = ('user__username', 'table__table_number')
    inlines = [OrderItemInline, PaymentInline]


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'variant_name', 'final_price', 'status') 
    # FIX: Filter using the real field on the related KitchenTicket model
    list_filter = ('ticket__status', 'menu_item',) 


@admin.register(KitchenTicket)
class KitchenTicketAdmin(ModelAdmin):
    list_display = ('order_item', 'station', 'status', 'priority', 'due_at')
    list_filter = ('station', 'status', 'priority')
    readonly_fields = ('due_at',) 


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('order', 'amount', 'method', 'status', 'paid_at')
    list_filter = ('method', 'status')
    readonly_fields = ('paid_at', 'transaction_id',)
    # FIX: Use the actual database field 'created_at' for date hierarchy
    date_hierarchy = 'created_at' 


@admin.register(QRToken)
class QRTokenAdmin(ModelAdmin):
    list_display = ('token', 'table')
    search_fields = ('token',)


@admin.register(ScreenDisplay)
class ScreenDisplayAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'type')
    list_filter = ('type', 'restaurant')


@admin.register(SalesData)
class SalesDataAdmin(ModelAdmin):
    list_display = ('month', 'amount', 'restaurant', 'date')
    list_filter = ('restaurant', 'month', 'date')


@admin.register(Inventory)
class InventoryAdmin(ModelAdmin):
    list_display = ('name', 'restaurant', 'quantity', 'unit', 'low_stock_threshold', 'is_low_stock')
    list_filter = ('restaurant', 'unit')
    search_fields = ('name',)
    readonly_fields = ('last_updated',)

