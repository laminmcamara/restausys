from django.db import transaction
from rest_framework import serializers
from django.db.models import Sum 
from .models import (
    CustomUser, Restaurant, Table, Order, OrderItem, Product, 
    ModifierGroup, ModifierOption, InventoryItem, Category, 
    Menu, Payment, ProductVariant, Subscription, KitchenTicket, 
    Settings, Printer, PrintJob, WebhookConfiguration, Session,
    TableSession, Customer, Discount, PaymentMethod
)

LANGUAGE_CHOICES = [
    ("en", "English"), ("es", "Español"), ("zh", "中文"),
    ("zh-HK", "粵語"), ("fr", "Français"), ("tr", "Türkçe"),
    ("ur", "اردو"), ("ar", "العربية"),
]

# ==============================================================================
# ✅ USER & AUTH SERIALIZERS
# ==============================================================================
class CustomUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ["id", "language", "username", "first_name", "last_name", "full_name", "email", "role", "restaurant"]
        read_only_fields = ["id", "restaurant"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

class StaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "phone_number", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]

class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "phone_number", "role", "password"]

    def create(self, validated_data):
        restaurant = self.context["restaurant"]
        password = validated_data.pop("password")
        user = CustomUser(**validated_data, restaurant=restaurant)
        user.set_password(password)
        user.save()
        return user

class StaffUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "phone_number", "role", "is_active"]
        read_only_fields = ["id", "username"]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

# ==============================================================================
# ✅ MENU & TABLES
# ==============================================================================
class TableSerializer(serializers.ModelSerializer):
    has_active_session = serializers.BooleanField(read_only=True)
    class Meta:
        model = Table
        fields = ["id", "table_number", "capacity", "qr_code", "has_active_session"]

class ModifierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModifierOption
        fields = ["id", "group", "name", "price_adjustment", "display_order"]

class ModifierGroupSerializer(serializers.ModelSerializer):
    options = ModifierOptionSerializer(many=True, read_only=True)
    class Meta:
        model = ModifierGroup
        fields = ["id", "name", "selection_type", "options"]

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "name", "price", "is_default"]

class ProductSerializer(serializers.ModelSerializer):
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    # Define price as a read-only method field to avoid model field validation
    price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        # ONLY include fields that DEFINITELY exist in your models.py Product class
        # Based on your errors, 'base_price' exists, but 'price' does not.
        fields = [
            "id", "name", "description", "base_price", "price", 
            "image", "is_available", "category", "modifier_groups", "variants"
        ]

    def get_price(self, obj):
        # Return base_price as the price for the frontend
        return str(obj.base_price)

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
# ✅ ORDER SYSTEM (WITH POS FIXES)
# ==============================================================================
# ==============================================================================
# ✅ PRODUCT SERIALIZER (FIXED FIELD NAMES)
# ==============================================================================
class ProductSerializer(serializers.ModelSerializer):
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    # We create a virtual 'price' field so the frontend doesn't break
    price = serializers.DecimalField(source='base_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        # Removed 'price' from the direct model fields and used the alias above
        fields = [
            "id", "name", "description", "base_price", "price", 
            "image", "is_available", "category", "modifier_groups", "variants"
        ]


# ==============================================================================
# ✅ ORDER ITEM SERIALIZER (FIXED FIELD NAMES)
# ==============================================================================
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "variant",
            "quantity",
            "final_price",   # This is the unit price in  model
            "notes",
            "modifiers",
            "status",
            "total_price",
        ]

    def get_total_price(self, obj):
        # Ensure we handle potential None values
        price = obj.final_price or 0
        qty = obj.quantity or 0
        return price * qty

# ==============================================================================
# ✅ ORDER SERIALIZER (FIXED TOTALS & CREATION)
# ==============================================================================
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    staff_name = serializers.ReadOnlyField(source="created_by.username")
    table_name = serializers.ReadOnlyField(source="table.table_number", default="Takeout")
    
    table = serializers.PrimaryKeyRelatedField(
        queryset=Table.objects.all(),
        required=False,
        allow_null=True
    )

    total_price = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "table", "table_name", "status", 
            "order_type", "items", "staff_name", "total_price", 
            "total_amount", "created_at", "session"
        ]
        read_only_fields = ["restaurant", "created_at"]

    def get_total_price(self, obj):
        # Try to get the calculated total from the model field
        val = getattr(obj, 'total_price', getattr(obj, 'total_amount', 0))
        # If the model field is 0, try to calculate it on the fly for the response
        if not val or val == 0:
            val = sum((item.final_price * item.quantity) for item in obj.items.all())
        return "{:.2f}".format(float(val))

    def get_total_amount(self, obj):
        return self.get_total_price(obj)

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        user = request.user if request else None
        restaurant = user.restaurant if user else None

        # 1. Handle Virtual Table for Takeout
        if validated_data.get('order_type') == 'TAKEOUT' and not validated_data.get('table'):
            virtual_table, _ = Table.objects.get_or_create(
                restaurant=restaurant,
                table_number="TO",
                defaults={'capacity': 0, 'is_active': False}
            )
            validated_data['table'] = virtual_table

        # 2. Inject Context Data
        if restaurant:
            validated_data['restaurant'] = restaurant
        if user:
            validated_data['created_by'] = user

        # 3. Create the Order
        order = Order.objects.create(**validated_data)
        
        # 4. Create Order Items
        for item_data in items_data:
            modifiers = item_data.pop('modifiers', [])
            product = item_data.get('product')
            
            # FIX: Use 'final_price' instead of 'unit_price' to match your model
            if not item_data.get('final_price'):
                item_data['final_price'] = getattr(product, 'price', getattr(product, 'base_price', 0))
            
            oi = OrderItem.objects.create(order=order, **item_data)
            if modifiers:
                oi.modifiers.set(modifiers)
            oi.save()
        
        # 5. Calculate Totals
        if hasattr(order, 'calculate_totals'):
            order.calculate_totals()
        
        order.save()
        return order
# ==============================================================================
# ✅ KITCHEN & PRINTING
# ==============================================================================
class KitchenTicketSerializer(serializers.ModelSerializer):
    # Helper fields for the KDS UI
    table_number = serializers.ReadOnlyField(source='order.table.table_number')
    order_type = serializers.ReadOnlyField(source='order.order_type')
    items = OrderItemSerializer(source='order.items', many=True, read_only=True)

    class Meta:
        model = KitchenTicket
        fields = [
            'id', 
            'order', 
            'table_number',
            'order_type',
            'status', 
            'items', 
            'notes',
            'printed',
            'created_at',
            'started_at',  
            'completed_at',  
        ]
        read_only_fields = ['created_at', 'started_at', 'completed_at']
class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = "__all__"

class PrintJobSerializer(serializers.ModelSerializer):
    printer_name = serializers.CharField(source="printer.name", read_only=True)
    class Meta:
        model = PrintJob
        fields = "__all__"

# ==============================================================================
# ✅ BUSINESS & SETTINGS
# ==============================================================================
class SessionSerializer(serializers.ModelSerializer):
    opened_by_name = serializers.ReadOnlyField(source='opened_by.username')

    class Meta:
        model = Session
        fields = [
            'id', 'restaurant', 'opened_by', 'opened_by_name', 
            'start_time', 'end_time', 'start_amount', 'end_amount', 
            'status', 'notes'
        ]
        read_only_fields = ['opened_by', 'restaurant', 'start_time']

    def create(self, validated_data):
        # Automatically assign restaurant and user from the view context
        validated_data['restaurant'] = self.context['request'].user.restaurant
        validated_data['opened_by'] = self.context['request'].user
        return super().create(validated_data)
    
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'restaurant']

class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "quantity", "unit", "low_stock_threshold", "is_low_stock"]

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ["id", "name", "code", "discount_type", "value", "is_active"]

# core/serializers.py

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        # Ensure these fields exist in models.py 
        fields = ['id', 'name', 'slug', 'active', 'requires_reference']

class PaymentSerializer(serializers.ModelSerializer):
    # We add this to see the method details in GET requests, 
    # but keep it simple for POST requests.
    class Meta:
        model = Payment
        fields = ['id', 'order', 'method', 'amount', 'status', 'transaction_id', 'created_at']

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = "__all__"

class WebhookConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookConfiguration
        fields = "__all__"

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = "__all__"