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
        fields = ["id", "language", "username", "first_name", "last_name", "full_name", "email", "role", "restaurant", "is_staff", "is_superuser"]
        read_only_fields = ["id", "restaurant", "is_staff", "is_superuser"]

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
        fields = ["id", "table_number", "status", "capacity", "qr_code", "has_active_session"]

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
    # Alias base_price to price for frontend compatibility
    price = serializers.DecimalField(source='base_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
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
# ✅ SINGLE UNIFIED ORDER ITEM SERIALIZER
# ==============================================================================
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "product_name", "variant", 
            "quantity", "final_price", "notes", "modifiers", 
            "status", "total_price", "order"
        ]

    def get_total_price(self, obj):
        price = obj.final_price or 0
        qty = obj.quantity or 0
        return price * qty


# ==============================================================================
# ✅ SINGLE UNIFIED ORDER SERIALIZER
# ==============================================================================
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    staff_name = serializers.ReadOnlyField(source="created_by.username")
    table_name = serializers.ReadOnlyField(source="table.table_number", default="Takeout")
    
    # Added these for the Dashboard and Printing
    total_price = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    short_id = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "short_id", 'payment_method', "restaurant", "table", "table_name", "status", 
            "order_type", "items", "staff_name", "total_price", 
            "total_amount", "created_at", "session"
        ]
        read_only_fields = ["restaurant", "created_at"]
    
    def get_short_id(self, obj):
        return str(obj.id)[-4:].upper()

    def get_total_price(self, obj):
        # Logic: Use model field if available, otherwise calculate
        val = getattr(obj, 'total_price', getattr(obj, 'total_amount', 0))
        if not val or val == 0:
            val = sum((item.final_price * item.quantity) for item in obj.items.all())
        return "{:.2f}".format(float(val))

    def get_total_amount(self, obj):
        return self.get_total_price(obj)

    @transaction.atomic
    def create(self, validated_data):
        # Extract items from the raw request data
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("No request in serializer context.")

        items_data = request.data.get('items', [])
        restaurant = request.user.restaurant
        session = TableSession.objects.get(restaurant=restaurant)

        # Handle Takeout
        if validated_data.get('order_type') == 'TAKEOUT' and not validated_data.get('table'):
            virtual_table, _ = Table.objects.get_or_create(
                restaurant=restaurant,
                table_number="TO",
                defaults={'capacity': 0}
            )
            validated_data['table'] = virtual_table

        # ✅ Assign payment_method if provided in the request
        payment_method_id = request.data.get("payment_method")
        if payment_method_id:
            from .models import PaymentMethod
            pm = PaymentMethod.objects.filter(
                id=payment_method_id,
                restaurant=restaurant
            ).first()
            if pm:
                validated_data["payment_method"] = pm
            else:
                logger.warning(
                    f"PaymentMethod {payment_method_id} not found for restaurant {restaurant.id}"
                )

        # Create the order instance
        order = Order.objects.create(
            session=session,
            restaurant=restaurant,
            created_by=request.user,
            **{k: v for k, v in validated_data.items() if k != "items"}
        )

        # Create order items
        for item_data in items_data:
            product = Product.objects.get(id=item_data['product'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data.get('quantity', 1),
                final_price=item_data.get('final_price', product.base_price),
                notes=item_data.get('notes', '')
            )

        if hasattr(order, 'calculate_totals'):
            order.calculate_totals()

        # validated_data["session"] = session  # not needed anymore; already used above
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


class PaymentMethodSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source='active')

    class Meta:
        model = PaymentMethod
        # Ensure these fields exist in models.py 
        fields = ['id', 'name', 'slug', 'is_active', 'requires_reference']

class PaymentSerializer(serializers.ModelSerializer):
    # We add this to see the method details in GET requests, 
    # but keep it simple for POST requests.
    class Meta:
        model = Payment
        fields = ['id', 'order', 'method', 'amount', 'status', 'transaction_id', 'created_at']
        
class PaymentSummarySerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(source="method.name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_number",  # or whatever you use
            "method_name",
            "amount",
            "status",
            "created_at",
        ]

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