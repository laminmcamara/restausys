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
    ProductVariant,
    Subscription,
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
# Menu System Serializers
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
        read_only_fields = ["id"]

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
        read_only_fields = ["id"]
        

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
# Order Serializers
# ==============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for items inside an order.
    Secure against cross-restaurant data leaks.
    """

    # ✅ Read representations
    product = ProductSerializer(read_only=True)
    modifiers = ModifierOptionSerializer(many=True, read_only=True)

    # ✅ Write fields
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
                category__menu__restaurant=restaurant
            )

            self.fields["modifier_ids"].queryset = ModifierOption.objects.filter(
                group__products__category__menu__restaurant=restaurant
            ).distinct()

    # -------------------------------------------------
    # ✅ VALIDATE MODIFIER SELECTION TYPE
    # -------------------------------------------------

    def validate(self, data):
        product = data.get("product")
        modifiers = data.get("modifiers", [])

        if not product:
            return data

        # Group selected modifiers by group
        grouped = {}

        for modifier in modifiers:
            group = modifier.group
            grouped.setdefault(group.id, []).append(modifier)

        for group in product.modifier_groups.all():
            selected = grouped.get(group.id, [])

            if group.selection_type == ModifierGroup.SelectionType.SINGLE:
                if len(selected) > 1:
                    raise serializers.ValidationError(
                        f"{group.name} allows only one selection."
                    )

        return data

    # -------------------------------------------------
    # ✅ CREATE
    # -------------------------------------------------

    def create(self, validated_data):
        modifiers = validated_data.pop("modifiers", [])

        item = OrderItem.objects.create(**validated_data)

        if modifiers:
            item.modifiers.set(modifiers)

        # ✅ Use model method (correct + future-safe)
        item.recalculate_price()
        item.order.calculate_totals()

        return item

    # -------------------------------------------------
    # ✅ UPDATE
    # -------------------------------------------------

    def update(self, instance, validated_data):
        modifiers = validated_data.pop("modifiers", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if modifiers is not None:
            instance.modifiers.set(modifiers)

        instance.recalculate_price()
        instance.order.calculate_totals()

        return instance
    
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    staff = CustomUserSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    display_id = serializers.SerializerMethodField()
    estimated_time = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "display_id",
            "restaurant",
            "table",
            "status",
            "created_at",
            "updated_at",
            "items",
            "staff",
            "total_price",
            "estimated_time",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_total_price(self, obj):
        return obj.total

    def get_display_id(self, obj):
        return obj.short_id()

    def get_estimated_time(self, obj):
        items = list(obj.items.all())
        return sum(
            item.product.prep_time * item.quantity
            for item in items
            if item.product and item.product.prep_time
        )
    
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



class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "price",
            "is_default",
        ]


# core/serializers.py

from .models import Settings

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        exclude = ["restaurant"]


class SubscriptionSerializer(serializers.ModelSerializer):

    plan_name = serializers.CharField(source="plan.name", read_only=True)
    monthly_price = serializers.DecimalField(
        source="plan.monthly_price",
        max_digits=10,
        decimal_places=2,
        read_only=True
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