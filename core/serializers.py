# myapp/serializers.py

from rest_framework import serializers
from .models import CustomUser, Order, OrderItem


# ==============================================================================
# CustomUser Serializer
# ==============================================================================

class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for the CustomUser model."""

    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
        ]
        read_only_fields = ['id', 'email']

    def get_full_name(self, obj):
        """Return full name derived from first and last names."""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


# ==============================================================================
# Order Item Serializer
# ==============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for individual items within an order."""

    menu_item_name = serializers.CharField(
        source='menu_item.name', read_only=True
    )
    variant_name = serializers.CharField(
        source='variant.name', read_only=True, allow_null=True
    )
    price = serializers.DecimalField(
        source='menu_item.price', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'menu_item_name',
            'variant_name',
            'quantity',
            'notes',
            'price',
        ]
        read_only_fields = ['id', 'menu_item_name', 'variant_name', 'price']


# ==============================================================================
# Order Serializer (Main)
# ==============================================================================

class OrderSerializer(serializers.ModelSerializer):
    """
    Main serializer for the Order model.
    Includes nested items for both read and broadcasting via Channels.
    """

    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(
        source='table.table_number', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'table_number',
            'status',
            'status_display',
            'created_at',
            'updated_at',
            'items',
            'total_price',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        """Calculate total price of all order items."""
        try:
            return sum(
                (item.menu_item.price or 0) * item.quantity
                for item in getattr(obj, 'items', [])
            )
        except Exception:
            return 0.00

    def validate_status(self, value):
        """Ensure the status value is valid according to Order model choices."""
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status: {value}")
        return value


# ==============================================================================
# Integration Helper: Build payloads for Channels Consumers
# ==============================================================================

def serialize_order_for_channels(order):
    """
    Helper function for WebSocket broadcasting.

    Usage:
        serialized_data = serialize_order_for_channels(order)
        await channel_layer.group_send("kitchen_display", {
            "type": "send_order_update",
            "order": serialized_data,
        })
    """
    serializer = OrderSerializer(order)
    return serializer.data


def serialize_order_list_for_channels(orders_queryset):
    """
    Helper for serializing multiple orders at once (e.g., all open orders for KDS).
    """
    serializer = OrderSerializer(orders_queryset, many=True)
    return serializer.data