# core/serializers.py

from django.db import transaction
from rest_framework import serializers
from django.db.models import Sum 

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
    Printer,
    PrintJob,
    WebhookConfiguration,
)


LANGUAGE_CHOICES = [
    ("en", "English"),
    ("es", "Español"),
    ("zh", "中文"),
    ("zh-HK", "粵語"), 

    ("fr", "Français"),
    ("tr", "Türkçe"),
    ("ur", "اردو"),
    ("ar", "العربية"),
]


language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, required=False)


# ==============================================================================
# ✅ USER
# ==============================================================================

class CustomUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "role",
            "restaurant",
        ]

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.email or obj.username
    

class CustomUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    can_manage_staff = serializers.BooleanField(read_only=True)
    can_access_pos = serializers.BooleanField(read_only=True)
    can_access_kitchen = serializers.BooleanField(read_only=True)
    can_access_public_display = serializers.BooleanField(read_only=True)
    can_view_dashboard = serializers.BooleanField(read_only=True)
    can_view_reports = serializers.BooleanField(read_only=True)
    can_manage_products = serializers.BooleanField(read_only=True)
    can_manage_tables = serializers.BooleanField(read_only=True)
    can_manage_settings = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "language",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "role",
            "restaurant",

            "can_manage_staff",
            "can_access_pos",
            "can_access_kitchen",
            "can_access_public_display",
            "can_view_dashboard",
            "can_view_reports",
            "can_manage_products",
            "can_manage_tables",
            "can_manage_settings",
        ]
        read_only_fields = [
            "id",
            "restaurant",
            "can_manage_staff",
            "can_access_pos",
            "can_access_kitchen",
            "can_access_public_display",
            "can_view_dashboard",
            "can_view_reports",
            "can_manage_products",
            "can_manage_tables",
            "can_manage_settings",
        ]

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.email or obj.username

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

class StaffUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    can_manage_staff = serializers.BooleanField(read_only=True)
    can_access_pos = serializers.BooleanField(read_only=True)
    can_access_kitchen = serializers.BooleanField(read_only=True)
    can_access_public_display = serializers.BooleanField(read_only=True)
    can_view_dashboard = serializers.BooleanField(read_only=True)
    can_view_reports = serializers.BooleanField(read_only=True)
    can_manage_products = serializers.BooleanField(read_only=True)
    can_manage_tables = serializers.BooleanField(read_only=True)
    can_manage_settings = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "language",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "avatar",
            "is_active",
            "is_staff",
            "date_joined",

            "can_manage_staff",
            "can_access_pos",
            "can_access_kitchen",
            "can_access_public_display",
            "can_view_dashboard",
            "can_view_reports",
            "can_manage_products",
            "can_manage_tables",
            "can_manage_settings",
        ]
        read_only_fields = [
            "id",
            "username",
            "is_staff",
            "date_joined",
            "can_manage_staff",
            "can_access_pos",
            "can_access_kitchen",
            "can_access_public_display",
            "can_view_dashboard",
            "can_view_reports",
            "can_manage_products",
            "can_manage_tables",
            "can_manage_settings",
        ]

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.email or obj.username
    
class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "password",
        ]

    def validate_role(self, value):
        allowed_roles = [
            CustomUser.Roles.MANAGER,
            CustomUser.Roles.SERVER,
            CustomUser.Roles.COOK,
            CustomUser.Roles.CASHIER,
            CustomUser.Roles.STAFF,
        ]

        if value not in allowed_roles:
            raise serializers.ValidationError("Invalid staff role.")

        return value

    def create(self, validated_data):
        restaurant = self.context["restaurant"]
        password = validated_data.pop("password")

        user = CustomUser(
            **validated_data,
            restaurant=restaurant,
        )
        user.set_password(password)
        user.save()
        return user
    
class StaffUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "language",
            "role",
            "is_active",
        ]

    def validate_role(self, value):
        allowed_roles = [
            CustomUser.Roles.MANAGER,
            CustomUser.Roles.SERVER,
            CustomUser.Roles.COOK,
            CustomUser.Roles.CASHIER,
            CustomUser.Roles.STAFF,
        ]

        if value not in allowed_roles:
            raise serializers.ValidationError("Invalid staff role.")

        return value
    


# ==============================================================================
# ✅ INVENTORY
# ==============================================================================

# class InventoryItemSerializer(serializers.ModelSerializer):
#    class Meta:
#        model = InventoryItem
#        fields = "__all__"


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
        required=False,
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
        read_only_fields = [
            "id",
            "product",
            "modifiers",
            "final_price",
        ]

    # ✅ Multi-tenant safety + superuser support
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return

        user = request.user

        # ✅ Superuser can test across all restaurants
        if user.is_superuser:
            self.fields["product_id"].queryset = Product.objects.all()
            self.fields["modifier_ids"].queryset = ModifierOption.objects.all()
            return

        restaurant = getattr(user, "restaurant", None)

        if restaurant is None:
            self.fields["product_id"].queryset = Product.objects.none()
            self.fields["modifier_ids"].queryset = ModifierOption.objects.none()
            return

        self.fields["product_id"].queryset = Product.objects.filter(
            category__menu__restaurant=restaurant
        )

        self.fields["modifier_ids"].queryset = (
            ModifierOption.objects.filter(
                group__products__category__menu__restaurant=restaurant
            ).distinct()
        )

    def validate(self, attrs):
        """
        ✅ Works for both:
        - POST create: order + product_id are required
        - PATCH update: quantity-only updates are allowed
        """

        instance = getattr(self, "instance", None)

        order = attrs.get("order") or getattr(instance, "order", None)
        product = attrs.get("product") or getattr(instance, "product", None)
        modifiers = attrs.get("modifiers", None)

        # ✅ Only require order/product on create
        if instance is None:
            if not order:
                raise serializers.ValidationError({
                    "order": "Order is required."
                })

            if not product:
                raise serializers.ValidationError({
                    "product_id": "Product is required."
                })

        # ✅ On PATCH quantity-only, skip restaurant/product modifier validation if missing
        if not order or not product:
            return attrs

        order_restaurant_id = order.restaurant_id
        product_restaurant_id = product.category.menu.restaurant_id

        if product_restaurant_id != order_restaurant_id:
            raise serializers.ValidationError({
                "product_id": "Product does not belong to this order's restaurant."
            })

        # ✅ Only validate modifiers if request includes modifier_ids
        if modifiers is not None:
            for modifier in modifiers:
                valid_for_product = modifier.group.products.filter(
                    id=product.id
                ).exists()

                modifier_belongs_to_restaurant = modifier.group.products.filter(
                    category__menu__restaurant_id=order_restaurant_id
                ).exists()

                if not modifier_belongs_to_restaurant:
                    raise serializers.ValidationError({
                        "modifier_ids": "One or more modifiers do not belong to this order's restaurant."
                    })

                if not valid_for_product:
                    raise serializers.ValidationError({
                        "modifier_ids": "One or more modifiers are not valid for this product."
                    })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        modifiers = validated_data.pop("modifiers", [])
        item = OrderItem.objects.create(**validated_data)

        if modifiers:
            item.modifiers.set(modifiers)

        item.recalculate_price()
        item.order.calculate_totals()

        return item

    @transaction.atomic
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
    

# ==============================================================================
# ✅ ORDER SERIALIZER (UPDATED FOR DISPLAY)
# ==============================================================================

# ==============================================================================
# ✅ ORDER SERIALIZER (UPDATED FOR DISPLAY)
# ==============================================================================

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    staff = CustomUserSerializer(source="created_by", read_only=True)

    total_price = serializers.SerializerMethodField()
    display_id = serializers.SerializerMethodField()
    estimated_time = serializers.SerializerMethodField()

    # ✅ ADD THIS LINE: Pulls the name from the Restaurant model
    restaurant_name = serializers.CharField(
        source="restaurant.name", 
        read_only=True
    )

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
            "restaurant_name", 
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
        fields = [
            "id",

            # General
            "restaurant_display_name",
            "business_email",
            "business_phone",
            "business_address",
            "currency_symbol",
            "timezone",

            # Tax and charges
            "tax_percentage",
            "service_charge_percentage",
            "prices_include_tax",

            # Order behavior
            "auto_mark_order_paid",
            "allow_split_payments",
            "allow_table_merge",
            "default_order_type",
            "require_table_for_dine_in",
            "auto_print_kitchen_tickets",

            # Receipt
            "show_logo_on_receipt",
            "receipt_header_text",
            "receipt_footer_text",

            # Inventory
            "stock_alerts_enabled",
            "auto_deduct_inventory",

            # Notifications
            "email_notifications_enabled",
            "send_daily_sales_report",
            "low_stock_email_alerts",
            "notify_on_new_order",

            # Appearance
            "default_theme",
            "items_per_page",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

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


class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = "__all__"

    def validate(self, attrs):
        connection_type = attrs.get(
            "connection_type",
            getattr(self.instance, "connection_type", None)
        )

        ip_address = attrs.get(
            "ip_address",
            getattr(self.instance, "ip_address", None)
        )

        system_name = attrs.get(
            "system_name",
            getattr(self.instance, "system_name", "")
        )

        if connection_type == "NETWORK" and not ip_address:
            raise serializers.ValidationError({
                "ip_address": "IP address is required for network printers."
            })

        if connection_type in ["USB", "SYSTEM"] and not system_name:
            raise serializers.ValidationError({
                "system_name": "System printer name is required for USB/system printers."
            })

        return attrs
    
class PrintJobSerializer(serializers.ModelSerializer):
    printer_name = serializers.CharField(source="printer.name", read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = PrintJob
        fields = [
            "id",
            "order",
            "order_id",
            "printer",
            "printer_name",
            "job_type",
            "status",
            "payload",
            "error_message",
            "attempt_count",
            "created_at",
            "printed_at",
        ]
        read_only_fields = [
            "status",
            "error_message",
            "attempt_count",
            "created_at",
            "printed_at",
        ]
        
        
"""
BEEPOS - Serializers for Staff, Customers, Payments, Inventory, Discounts
==========================================================================

Place this in your Django app's serializers.py or a new file.
Adjust model imports to match your project structure.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, Payment, InventoryItem, Discount

User = get_user_model()





# ===================================================================
# CUSTOMER SERIALIZER
# ===================================================================

class CustomerSerializer(serializers.ModelSerializer):
    """
    Includes computed fields for total_orders and total_spent.
    These are read-only and calculated on the fly.
    """
    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'total_spent', 'created_at', 'total_orders', 'restaurant']
        read_only_fields = ('restaurant',) 

    def get_total_orders(self, obj):
        # This counts the number of orders linked to this customer
        # Note: 'orders' is the related_name on the Order -> Customer ForeignKey
        return obj.orders.count()

    def get_total_spent(self, obj):
        # This sums the 'total_amount' field from all orders linked to this customer
        result = obj.orders.aggregate(total=Sum('total_amount'))['total']
        return str(result) if result else "0.00"


# ===================================================================
# PAYMENT SERIALIZER
# ===================================================================
class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializes payment records. Includes order ID and customer name
    for display in the payments table.
    """

    order_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "restaurant",
            "order",
            "order_id",
            "customer",
            "customer_name",
            "amount",
            "payment_method",
            "status",
            "transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_order_id(self, obj):
        return obj.order.id if obj.order else None

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else None


# ===================================================================
# INVENTORY SERIALIZER
# ===================================================================
class InventoryItemSerializer(serializers.ModelSerializer):
    """
    Includes is_low_stock computed property for quick filtering.
    """

    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "restaurant",
            "name",
            "category",
            "quantity",
            "unit",
            "low_stock_threshold",
            "unit_cost",
            "supplier",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]





# ===================================================================
# DISCOUNT SERIALIZER
# ===================================================================
class DiscountSerializer(serializers.ModelSerializer):
    """
    Includes is_valid and is_expired computed properties.
    """

    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Discount
        fields = [
            "id",
            "restaurant",
            "name",
            "code",
            "discount_type",
            "value",
            "is_active",
            "valid_from",
            "valid_to",
            "min_order_amount",
            "max_discount_amount",
            "usage_limit",
            "times_used",
            "is_valid",
            "is_expired",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_used", "created_at", "updated_at"]


class WebhookConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookConfiguration
        fields = [
            'live_api_key', 
            'test_api_key', 
            'live_secret', 
            'test_secret', 
            'live_webhook_url', 
            'test_webhook_url', 
            'is_live_enabled', 
            'is_test_enabled'
        ]
        # We make these read-only so they can't be changed via the standard POST
        # (Regeneration is handled by our custom endpoint instead)
        read_only_fields = ['live_api_key', 'test_api_key', 'live_secret', 'test_secret']