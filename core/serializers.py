# core/serializers.py

from django.db import transaction
from rest_framework import serializers

from .models import (
    CustomUser,
    Restaurant,
    Table,
    Order,
    OrderItem,
    Product,
    ModifierGroup,
    ModifierOption,
    InventoryItem,
    Category,
    Menu,
    Payment,
    ProductVariant,
    Subscription,
    KitchenTicket,
    Settings,
)

# ==============================================================================
# ✅ USER
# ==============================================================================

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "restaurant",
        ]


# ==============================================================================
# ✅ INVENTORY
# ==============================================================================

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"


# ==============================================================================
# ✅ TABLE
# ==============================================================================

class TableSerializer(serializers.ModelSerializer):
    has_active_session = serializers.BooleanField(read_only=True)

    class Meta:
        model = Table
        fields = [
            "id",
            "table_number",
            "capacity",
            "qr_code",
            "has_active_session",
        ]


# ==============================================================================
# ✅ MENU SYSTEM
# ==============================================================================

class ModifierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModifierOption
        fields = [
            "id",
            "group",
            "name",
            "price_adjustment",
            "display_order",
        ]


class ModifierGroupSerializer(serializers.ModelSerializer):
    options = ModifierOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "name",
            "selection_type",
            "products",
            "options",
        ]


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "price",
            "is_default",
        ]


class ProductSerializer(serializers.ModelSerializer):
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    modifier_group_ids = serializers.PrimaryKeyRelatedField(
        queryset=ModifierGroup.objects.all(),
        many=True,
        write_only=True,
        source="modifier_groups",
        required=False,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "base_price",
            "image",
            "is_available",
            "category",
            "modifier_groups",
            "modifier_group_ids",
            "variants",
        ]


class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "display_order", "products"]


class MenuSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "restaurant",
            "categories",
        ]
        read_only_fields = ["id", "restaurant"]


# ==============================================================================
# ✅ ORDER SYSTEM
# ==============================================================================

class OrderItemSerializer(serializers.ModelSerializer):

    product = ProductSerializer(read_only=True)
    modifiers = ModifierOptionSerializer(many=True, read_only=True)

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.none(),
        source="product",
        write_only=True,
    )

    modifier_ids = serializers.PrimaryKeyRelatedField(
        queryset=ModifierOption.objects.none(),
        source="modifiers",
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "modifiers",
            "quantity",
            "notes",
            "final_price",
            "product_id",
            "modifier_ids",
        ]
        read_only_fields = ["final_price"]

    # ✅ Multi-tenant safety
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            restaurant = request.user.restaurant

            self.fields["product_id"].queryset = Product.objects.filter(
                category__menu__restaurant=restaurant
            )

            self.fields["modifier_ids"].queryset = (
                ModifierOption.objects.filter(
                    group__products__category__menu__restaurant=restaurant
                ).distinct()
            )

    def create(self, validated_data):
        modifiers = validated_data.pop("modifiers", [])
        item = OrderItem.objects.create(**validated_data)

        if modifiers:
            item.modifiers.set(modifiers)

        item.recalculate_price()
        item.order.calculate_totals()

        return item


# ==============================================================================
# ✅ ORDER SERIALIZER (UPDATED FOR DISPLAY)
# ==============================================================================

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    staff = CustomUserSerializer(source="created_by", read_only=True)

    total_price = serializers.SerializerMethodField()
    display_id = serializers.SerializerMethodField()
    estimated_time = serializers.SerializerMethodField()

    # ✅ Clean display helpers
    table_name = serializers.CharField(
        source="table.table_number",
        read_only=True
    )

    customer_name = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "display_id",
            "restaurant",
            "table",
            "table_name",
            "customer_name",
            "status",
            "created_at",
            "updated_at",
            "items",
            "staff",
            "total_price",
            "estimated_time",
        ]
        read_only_fields = [
            "restaurant",
            "created_at",
            "updated_at",
        ]

    def get_total_price(self, obj):
        return obj.total

    def get_display_id(self, obj):
        return obj.short_id()  # ✅ Clean short order number

    def get_estimated_time(self, obj):
        return sum(
            item.product.prep_time * item.quantity
            for item in obj.items.all()
            if item.product and item.product.prep_time
        )


# ==============================================================================
# ✅ KITCHEN TICKET
# ==============================================================================

class KitchenTicketSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = KitchenTicket
        fields = "__all__"


# ==============================================================================
# ✅ PAYMENT (READ ONLY)
# ==============================================================================

class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "amount",
            "status",
            "created_at",
        ]
        read_only_fields = fields


# ==============================================================================
# ✅ SETTINGS
# ==============================================================================

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        exclude = ["restaurant"]


# ==============================================================================
# ✅ SUBSCRIPTION
# ==============================================================================

class SubscriptionSerializer(serializers.ModelSerializer):

    plan_name = serializers.CharField(source="plan.name", read_only=True)
    monthly_price = serializers.DecimalField(
        source="plan.monthly_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "plan_name",
            "monthly_price",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "is_active",
        ]

    def get_is_active(self, obj):
        return obj.is_active()


# ==============================================================================
# ✅ CHANNELS HELPER
# ==============================================================================

def serialize_order_for_channels(order):
    return OrderSerializer(order).data