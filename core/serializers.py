from rest_framework import serializers
from .models import CustomUser, Order, OrderItem  # Ensure all models are imported

class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for the CustomUser model."""
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']  # Include necessary fields

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for individual items within an order."""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True, allow_null=True)

    class Meta:
        model = OrderItem  # Ensure you specify the model
        fields = ['menu_item_name', 'variant_name', 'quantity', 'notes']

class OrderSerializer(serializers.ModelSerializer):
    """
    Main serializer for the Order model, including nested items.
    Used for sending data to Channels consumers.
    """
    items = OrderItemSerializer(many=True, read_only=True)  # 'items' is the related_name from the OrderItem's ForeignKey to Order
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order  # Ensure you specify the model
        fields = [
            'id', 
            'table_number', 
            'status', 
            'status_display',
            'created_at', 
            'items'
        ]
