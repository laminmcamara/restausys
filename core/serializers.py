# core/serializers.py

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
)

# ==============================================================================
# User Serializer
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
# Inventory Serializer
# ==============================================================================

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"


# ==============================================================================
# Table Serializer
# ==============================================================================

class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ["id", "restaurant", "table_number", "capacity", "status"]


# ==============================================================================
# Menu System Serializers
# ==============================================================================

class ModifierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModifierOption
        fields = ["id", "name", "price_adjustment"]


class ModifierGroupSerializer(serializers.ModelSerializer):
    options = ModifierOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "name",
            "selection_type",
            "options",
        ]

class ProductSerializer(serializers.ModelSerializer):
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)

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
        fields = ["id", "name", "description", "is_active", "restaurant", "categories"]


# ==============================================================================
# Order Serializers
# ==============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for items inside an order.
    Secure against cross-restaurant data leaks.
    """

    # Read representations
    product = ProductSerializer(read_only=True)
    modifiers = ModifierOptionSerializer(many=True, read_only=True)

    # Write fields (restricted per restaurant)
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
            "order",
            "product",
            "modifiers",
            "quantity",
            "notes",
            "final_price",
            "product_id",
            "modifier_ids",
        ]
        read_only_fields = ["order", "final_price"]

    # ✅ Multi-tenant protection
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            restaurant = request.user.restaurant

            self.fields["product_id"].queryset = Product.objects.filter(
                restaurant=restaurant
            )

            self.fields["modifier_ids"].queryset = ModifierOption.objects.filter(
                modifier_group__product__restaurant=restaurant
            )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    staff = CustomUserSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "restaurant",
            "table",
            "status",
            "created_at",
            "updated_at",
            "items",
            "staff",
            "total_price",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_total_price(self, obj):
        return obj.total


# ==============================================================================
# Payment Serializer (SECURE)
# ==============================================================================

class PaymentSerializer(serializers.ModelSerializer):
    """
    Payment data should NEVER be writable from frontend.
    Stripe webhook controls status updates.
    """

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
# Channels Helper
# ==============================================================================

def serialize_order_for_channels(order):
    """
    Used by signals.py to serialize order safely for WebSocket broadcast.
    """
    return OrderSerializer(order).data




