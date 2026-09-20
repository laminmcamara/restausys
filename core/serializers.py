from decimal import Decimal

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
    Printer,
    PrintJob,
    WebhookConfiguration,
    Session,
    TableSession,
    Customer,
    Discount,
    PaymentMethod,
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


# ==============================================================================
# HELPERS
# ==============================================================================

def get_request_from_context(serializer):
    return serializer.context.get("request")


def get_user_restaurant(serializer):
    request = get_request_from_context(serializer)

    if not request or not request.user.is_authenticated:
        return None

    return getattr(request.user, "restaurant", None)


def decimal_value(value):
    if value is None:
        return Decimal("0.00")

    return Decimal(str(value))


# ==============================================================================
# USER & AUTH SERIALIZERS
# ==============================================================================

class CustomUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

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
            "is_staff",
            "is_superuser",
        ]
        read_only_fields = [
            "id",
            "restaurant",
            "is_staff",
            "is_superuser",
        ]

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.username


class StaffUserSerializer(serializers.ModelSerializer):
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
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "date_joined",
        ]


class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        required=True,
    )

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
        read_only_fields = ["id"]

    def create(self, validated_data):
        restaurant = self.context.get("restaurant")

        if not restaurant:
            raise serializers.ValidationError(
                "A restaurant is required to create staff."
            )

        password = validated_data.pop("password")

        user = CustomUser(
            restaurant=restaurant,
            **validated_data,
        )
        user.set_password(password)
        user.save()

        return user


class StaffUpdateSerializer(serializers.ModelSerializer):
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
            "is_active",
        ]
        read_only_fields = [
            "id",
            "username",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        min_length=8,
    )


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


# ==============================================================================
# MENU & TABLES
# ==============================================================================

class TableSerializer(serializers.ModelSerializer):
    has_active_session = serializers.BooleanField(
        read_only=True
    )

    current_status = serializers.CharField(
        read_only=True
    )

    class Meta:
        model = Table
        fields = [
            "id",
            "table_number",
            "status",
            "current_status",
            "capacity",
            "qr_code",
            "has_active_session",
            "is_occupied",
        ]
        read_only_fields = [
            "id",
            "status",
            "current_status",
            "qr_code",
            "has_active_session",
            "is_occupied",
        ]
            

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
    options = ModifierOptionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "name",
            "selection_type",
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
    modifier_groups = ModifierGroupSerializer(
        many=True,
        read_only=True,
    )

    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    price = serializers.DecimalField(
        source="base_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "base_price",
            "price",
            "image",
            "is_available",
            "category",
            "modifier_groups",
            "variants",
        ]


class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "display_order",
            "products",
        ]


class MenuSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(
        many=True,
        read_only=True,
    )

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
        read_only_fields = [
            "restaurant",
        ]


# ==============================================================================
# ORDER ITEMS
# ==============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'product',
            'product_name',
            'variant',
            'quantity',
            'final_price',
            'total_price',
            'notes',
            'modifiers',
            'status',
        ]
        read_only_fields = [
            'id',
        ]
        extra_kwargs = {
            'order': {'required': True},
        }

    def get_total_price(self, obj):
        return obj.final_price * obj.quantity

    def get_restaurant(self):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        return getattr(
            request.user,
            "restaurant",
            None,
        )

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )

        return value

    def validate_product(self, product):
        restaurant = self.get_restaurant()

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        if not product.is_available:
            raise serializers.ValidationError(
                "This product is not currently available."
            )

        # Do not access product.category.restaurant_id.
        #
        # Your Category model does not contain a restaurant field.
        # Product ownership must instead be checked through another
        # relationship, such as product.restaurant, menu.restaurant,
        # or category.menu.restaurant, if those fields exist.

        return product

    def get_total_price(self, obj):
        price = obj.final_price or 0
        quantity = obj.quantity or 0

        return f"{price * quantity:.2f}"
    
# ==============================================================================
# PAYMENT METHODS
# ==============================================================================

class PaymentMethodSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(
        source="active",
        read_only=True,
    )

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "name",
            "display_name",
            "slug",
            "is_active",
            "requires_reference",
            "restaurant",
        ]
        read_only_fields = [
            "id",
            "display_name",
            "slug",
            "is_active",
            "restaurant",
        ]

    def get_display_name(self, obj):
        if hasattr(obj, "get_name_display"):
            return obj.get_name_display()

        return obj.name

    def validate(self, attrs):
        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        return attrs


# ==============================================================================
# ORDERS
# ==============================================================================

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        required=False,
    )

    staff_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    table_name = serializers.SerializerMethodField()

    restaurant_name = serializers.CharField(
        source="restaurant.name",
        read_only=True,
    )

    payment_method_details = PaymentMethodSerializer(
        source="payment_method",
        read_only=True,
    )

    order_type_display = serializers.CharField(
        source="get_order_type_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    payment_status_display = serializers.CharField(
        source="get_payment_status_display",
        read_only=True,
    )

    total_price = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    short_id = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "short_id",
            "order_number",
            "restaurant",
            "restaurant_name",
            "customer",
            "table",
            "table_name",
            "section",
            "session",
            "created_by",
            "staff_name",
            "order_type",
            "order_type_display",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "payment_method",
            "payment_method_details",
            "items",
            "notes",
            "subtotal",
            "tax",
            "service_charge",
            "discount",
            "tip",
            "total",
            "total_price",
            "total_amount",
            "inventory_deducted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "short_id",
            "order_number",
            "restaurant",
            "restaurant_name",
            "created_by",
            "staff_name",
            "table_name",
            "order_type_display",
            "status_display",
            "payment_status_display",
            "payment_method_details",
            "subtotal",
            "total",
            "total_price",
            "total_amount",
            "inventory_deducted",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "customer": {
                "required": False,
                "allow_null": True,
            },
            "table": {
                "required": False,
                "allow_null": True,
            },
            "section": {
                "required": False,
                "allow_null": True,
            },
            "session": {
                "required": False,
                "allow_null": True,
            },
            "payment_method": {
                "required": False,
                "allow_null": True,
            },
            "notes": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "tax": {
                "required": False,
                "min_value": Decimal("0.00"),
            },
            "service_charge": {
                "required": False,
                "min_value": Decimal("0.00"),
            },
            "discount": {
                "required": False,
                "min_value": Decimal("0.00"),
            },
            "tip": {
                "required": False,
                "min_value": Decimal("0.00"),
            },
        }

    def get_table_name(self, obj):
        if not obj.table:
            return "Takeout"

        return str(obj.table.table_number)

    def get_short_id(self, obj):
        if hasattr(obj, "short_id"):
            return obj.short_id()

        return f"ORD-{str(obj.id)[:6].upper()}"

    def get_total_price(self, obj):
        total = decimal_value(obj.total)

        if total == Decimal("0.00"):
            total = sum(
                (
                    decimal_value(item.final_price)
                    * (item.quantity or 0)
                )
                for item in obj.items.all()
            )

        return f"{total:.2f}"

    def get_total_amount(self, obj):
        return self.get_total_price(obj)

    def validate_payment_method(self, payment_method):
        if payment_method is None:
            return payment_method

        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        if not payment_method.active:
            raise serializers.ValidationError(
                "This payment method is inactive."
            )

        if (
            payment_method.restaurant_id is not None
            and payment_method.restaurant_id != restaurant.id
        ):
            raise serializers.ValidationError(
                "This payment method does not belong "
                "to your restaurant."
            )

        return payment_method

    def validate_customer(self, customer):
        if customer is None:
            return customer

        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        if customer.restaurant_id != restaurant.id:
            raise serializers.ValidationError(
                "This customer does not belong to your restaurant."
            )

        return customer

    def validate_table(self, table):
        if table is None:
            return table

        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        if table.restaurant_id != restaurant.id:
            raise serializers.ValidationError(
                "This table does not belong to your restaurant."
            )

        return table

    def validate_section(self, section):
        if section is None:
            return section

        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        if section.restaurant_id != restaurant.id:
            raise serializers.ValidationError(
                "This section does not belong to your restaurant."
            )

        return section

    def validate_session(self, session):
        if session is None:
            return session

        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        if session.restaurant_id != restaurant.id:
            raise serializers.ValidationError(
                "This session does not belong to your restaurant."
            )

        if not session.is_active:
            raise serializers.ValidationError(
                "This table session is not active."
            )

        return session

    def validate(self, attrs):
        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        payment_method = attrs.get(
            "payment_method",
            getattr(
                self.instance,
                "payment_method",
                None,
            ),
        )

        payment_status = attrs.get(
            "payment_status",
            getattr(
                self.instance,
                "payment_status",
                Order.PaymentStatus.UNPAID,
            ),
        )

        order_status = attrs.get(
            "status",
            getattr(
                self.instance,
                "status",
                Order.Status.DRAFT,
            ),
        )

        if (
            payment_status == Order.PaymentStatus.PAID
            and payment_method is None
        ):
            raise serializers.ValidationError(
                {
                    "payment_method": (
                        "A paid order must have a payment method."
                    )
                }
            )

        if (
            payment_status == Order.PaymentStatus.REFUNDED
            and order_status != Order.Status.CANCELED
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        "A refunded order must have CANCELED status."
                    )
                }
            )

        if (
            order_status == Order.Status.COMPLETED
            and payment_status != Order.PaymentStatus.PAID
        ):
            raise serializers.ValidationError(
                {
                    "payment_status": (
                        "A completed order must be paid."
                    )
                }
            )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        validated_data.pop("restaurant", None)
        validated_data.pop("created_by", None)
        validated_data.pop("order_number", None)

        order = super().update(
            instance,
            validated_data,
        )

        if items_data is not None:
            order.items.all().delete()

            for item_data in items_data:
                product = item_data["product"]

                final_price = item_data.get(
                    "final_price",
                    product.base_price,
                )

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=item_data.get("variant"),
                    quantity=item_data.get("quantity", 1),
                    final_price=final_price,
                    notes=item_data.get("notes", ""),
                    modifiers=item_data.get("modifiers"),
                    status=item_data.get("status"),
                )

        if hasattr(order, "calculate_totals"):
            order.calculate_totals()
            order.refresh_from_db()

        return order

# ==============================================================================
# KITCHEN & PRINTING
# ==============================================================================

class KitchenTicketSerializer(serializers.ModelSerializer):
    table_number = serializers.ReadOnlyField(
        source="order.table.table_number"
    )

    order_type = serializers.ReadOnlyField(
        source="order.order_type"
    )

    items = OrderItemSerializer(
        source="order.items",
        many=True,
        read_only=True,
    )

    class Meta:
        model = KitchenTicket
        fields = [
            "id",
            "order",
            "table_number",
            "order_type",
            "status",
            "items",
            "notes",
            "printed",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "created_at",
            "started_at",
            "completed_at",
        ]


class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = "__all__"


class PrintJobSerializer(serializers.ModelSerializer):
    printer_name = serializers.CharField(
        source="printer.name",
        read_only=True,
    )

    class Meta:
        model = PrintJob
        fields = "__all__"


# ==============================================================================
# BUSINESS & SETTINGS
# ==============================================================================

class SessionSerializer(serializers.ModelSerializer):
    opened_by_name = serializers.ReadOnlyField(
        source="opened_by.username"
    )

    class Meta:
        model = Session
        fields = [
            "id",
            "restaurant",
            "opened_by",
            "opened_by_name",
            "start_time",
            "end_time",
            "start_amount",
            "end_amount",
            "status",
            "notes",
        ]
        read_only_fields = [
            "opened_by",
            "restaurant",
            "start_time",
        ]

    def create(self, validated_data):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        restaurant = getattr(
            request.user,
            "restaurant",
            None,
        )

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        validated_data["restaurant"] = restaurant
        validated_data["opened_by"] = request.user

        return super().create(validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "restaurant",
        ]
        read_only_fields = [
            "restaurant",
        ]

    def create(self, validated_data):
        restaurant = get_user_restaurant(self)

        if not restaurant:
            raise serializers.ValidationError(
                "Your account is not connected to a restaurant."
            )

        validated_data["restaurant"] = restaurant

        return super().create(validated_data)


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(
        read_only=True
    )

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "quantity",
            "unit",
            "low_stock_threshold",
            "is_low_stock",
        ]


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = [
            "id",
            "name",
            "code",
            "discount_type",
            "value",
            "is_active",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(
        source="method.name",
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "method",
            "method_name",
            "amount",
            "status",
            "transaction_id",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "method_name",
        ]


class PaymentSummarySerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(
        source="method.name",
        read_only=True,
    )

    order_number = serializers.IntegerField(
        source="order.order_number",
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "order_number",
            "method_name",
            "amount",
            "status",
            "transaction_id",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "method_name",
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
        


class PublicProductSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        source="base_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "base_price",
            "image",
            "is_available",
        ]
        read_only_fields = [
            "id",
            "name",
            "description",
            "price",
            "base_price",
            "image",
            "is_available",
        ]


class PublicCategorySerializer(serializers.ModelSerializer):
    products = PublicProductSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "display_order",
            "products",
        ]
        read_only_fields = [
            "id",
            "name",
            "description",
            "display_order",
            "products",
        ]


class PublicTableSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(
        source="restaurant.name",
        read_only=True,
    )

    current_status = serializers.CharField(
        read_only=True,
    )

    class Meta:
        model = Table
        fields = [
            "id",
            "table_number",
            "capacity",
            "restaurant_name",
            "current_status",
        ]
        read_only_fields = [
            "id",
            "table_number",
            "capacity",
            "restaurant_name",
            "current_status",
        ]


class PublicOrderItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
    )

    quantity = serializers.IntegerField(
        min_value=1,
        max_value=50,
    )

    modifiers = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )


class PublicOrderCreateSerializer(serializers.Serializer):
    order_type = serializers.ChoiceField(
        choices=Order.OrderType.choices,
        default=Order.OrderType.DINE_IN,
        required=False,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    items = PublicOrderItemInputSerializer(
        many=True,
        allow_empty=False,
    )