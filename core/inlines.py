# core/inlines.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import OrderItem, Payment


# ==============================================================================
# Order Items Inline (Read-Only Financial Snapshot)
# ==============================================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    show_change_link = False

    fields = (
        "menu_item",
        "variant",
        "quantity",
        "unit_price_display",
        "subtotal_display",
    )

    readonly_fields = fields

    ordering = ("id",)

    def unit_price_display(self, obj):
        if hasattr(obj, "unit_price"):
            return f"${obj.unit_price:.2f}"
        return "-"
    unit_price_display.short_description = "Unit Price"

    def subtotal_display(self, obj):
        if hasattr(obj, "subtotal"):
            return f"${obj.subtotal:.2f}"
        return "-"
    subtotal_display.short_description = "Subtotal"


# ==============================================================================
# Payments Inline (Financial Integrity View)
# ==============================================================================

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    show_change_link = False

    fields = (
        "amount_display",
        "method",
        "status",
        "created_at",
    )

    readonly_fields = fields

    ordering = ("-created_at",)

    def amount_display(self, obj):
        return f"${obj.amount:.2f}"
    amount_display.short_description = "Amount"