# C:\Users\Administrator\restaurant_management\core\models.py

import uuid
from datetime import date, timedelta
from io import BytesIO
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Sum, F, DecimalField
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.files.base import File
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import qrcode
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# === BASE MODELS & MANAGERS ==================================================
# =============================================================================

class TimeStampedModel(models.Model):
    """Abstract base model for created_at and updated_at timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class OrderManager(models.Manager):
    def annotate_with_total_price(self):
        # This manager is now simpler, as the complex calculation is handled
        # by the OrderItem.final_price field.
        return self.annotate(
            calculated_total=Sum('items__final_price', output_field=DecimalField())
        )

# =============================================================================
# === COMPANY (Multi-brand parent) ============================================
# =============================================================================

class Company(TimeStampedModel):
    """Parent company or franchise group."""
    name = models.CharField(max_length=150, unique=True)
    registration_number = models.CharField(max_length=100, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="companies/logos/", null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# =============================================================================
# === USER & STAFF SYSTEM =====================================================
# =============================================================================

phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Use international format: +999999999. Up to 15 digits."
)

class CustomUser(AbstractUser):

    class Roles(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        MANAGER = 'MANAGER', 'Manager'
        SERVER = 'SERVER', 'Server'
        COOK = 'COOK', 'Cook'
        CASHIER = 'CASHIER', 'Cashier'
        CUSTOMER = 'CUSTOMER', 'Customer'
        STAFF = 'STAFF', 'General Staff'

    restaurant = models.ForeignKey(
        'core.Restaurant',
        null=True,
        blank=True,
        on_delete=models.PROTECT,  # ✅ PROTECT instead of SET_NULL
        related_name='users'
    )

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STAFF
    )

    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True
    )

    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    passport_id_card_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if not self.is_superuser:
            self.is_staff = self.role in [
                self.Roles.MANAGER,
                self.Roles.CASHIER,
                self.Roles.SUPER_ADMIN,
            ]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
class Shift(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="shifts"
    )
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE, related_name="shifts")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    role = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.employee} - {self.role} ({self.start_time:%b %d})"

class Attendance(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(blank=True, null=True)
    shift = models.ForeignKey(
        "core.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendances"
    )

    class Meta:
        ordering = ["-check_in"]

    def __str__(self):
        return f"{self.employee} - {self.restaurant.name} ({self.check_in:%Y-%m-%d})"

    @property
    def duration(self):
        if self.check_out:
            return self.check_out - self.check_in
        return None

# =============================================================================
# === CUSTOMER & LOYALTY ======================================================
# =============================================================================

class Customer(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile', null=True, blank=True)
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=30, default="en")
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loyalty_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.full_name

    def add_points(self, amount: Decimal):
        self.loyalty_points += int(amount // Decimal('10'))
        self.total_spent += amount
        self.save(update_fields=['loyalty_points', 'total_spent'])

# =============================================================================
# === COMPANY RESTAURANTS =======================================================
# =============================================================================

class Restaurant(TimeStampedModel):
    class RestaurantStatus(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'
        HOLIDAY = 'HOLIDAY', 'Holiday Hours'

    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name='restaurants')
    name = models.CharField(max_length=100)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=60)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=6, default="USD")
    logo = models.ImageField(upload_to="restaurants/logos/", null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=RestaurantStatus.choices, default=RestaurantStatus.OPEN)

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    class Meta:
        unique_together = ('company', 'name')

class Table(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        NEEDS_CLEANING = "NEEDS_CLEANING", "Needs Cleaning"
        RESERVED = "RESERVED", "Reserved"
        MERGED = "MERGED", "Merged"

    restaurant = models.ForeignKey(
    "core.Restaurant",
    on_delete=models.CASCADE,
    related_name="tables",
)

    table_number = models.CharField(max_length=20)

    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    class Meta:
        unique_together = ("restaurant", "table_number")

    def __str__(self):
        return f"Table {self.table_number}"

    def generate_qr_code(self):
        site = getattr(settings, "SITE_URL", "http://localhost:8000")
        qr_data = f"{site}/table/{self.access_token}/"
        qr_img = qrcode.make(qr_data).convert("RGB")

        width, height = qr_img.size
        new_height = height + 60
        combined = Image.new("RGB", (width, new_height), "white")

        combined.paste(qr_img, (0, 0))
        draw = ImageDraw.Draw(combined)

        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()

        text = f"Table {self.table_number}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (width - text_width) // 2

        draw.text((text_x, height + 20), text, font=font, fill="black")

        buffer = BytesIO()
        combined.save(buffer, format="PNG")

        safe_label = str(self.table_number).replace(" ", "_")
        filename = f"qr_table_{safe_label}_{self.id}.png"
        self.qr_code.save(filename, File(buffer), save=False)
        buffer.close()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_table_number = None

        if not is_new:
            old = Table.objects.filter(pk=self.pk).first()
            if old:
                old_table_number = old.table_number

        # generate QR for new table
        if is_new and not self.qr_code:
            self.generate_qr_code()

        super().save(*args, **kwargs)

        # regenerate QR only if number changed
        if not is_new and old_table_number != self.table_number:
            self.generate_qr_code()
            super().save(update_fields=["qr_code"])

# =============================================================================
# === INVENTORY & RECIPES =====================================================
# =============================================================================

class InventoryItem(models.Model):
    restaurant = models.ForeignKey(
        "core.Restaurant", on_delete=models.CASCADE, related_name="inventory"
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="pcs")
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("restaurant", "name")

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

# =============================================================================
# === ### NEW & IMPROVED MENU SYSTEM ### ======================================
# =============================================================================

class Menu(TimeStampedModel):
    """
    The top-level container for a set of categories and products.
    E.g., "Dinner Menu", "Lunch Menu", "Drinks Menu".
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE, related_name="menus")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Is this menu currently available?")

    class Meta:
        ordering = ['name']
        verbose_name = "Menu"
        verbose_name_plural = "Menus"
        unique_together = ('restaurant', 'name')

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class Category(TimeStampedModel):
    """
    A category for products. Can be nested infinitely.
    E.g., "Drinks" -> "Soft Drinks" -> "Carbonated".
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu = models.ForeignKey("core.Menu", on_delete=models.CASCADE, related_name="categories")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_categories',
        help_text="Leave blank for a top-level category."
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0, help_text="Order of display in the UI.")

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        unique_together = ('name', 'parent', 'menu')

    def __str__(self):
        path = [self.name]
        ancestor = self.parent
        while ancestor:
            path.insert(0, ancestor.name)
            ancestor = ancestor.parent
        return ' > '.join(path)
    
class Cuisine(models.Model):
    """Kept from original design."""
    name = models.CharField(max_length=100, unique=True)
    halal_certified = models.BooleanField(default=False)
    region = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    """
    The actual sellable item on the menu. This replaces the old `MenuItem` model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey("core.Category", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)]
    )
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    is_available = models.BooleanField(
        default=True,
        help_text="Is this product available for sale right now?"
    )
    display_order = models.PositiveIntegerField(default=0)
    
    cuisines = models.ManyToManyField("core.Cuisine", blank=True, related_name="products")
    ingredients = models.ManyToManyField(
        "core.InventoryItem",
        through="RecipeItem",
        related_name="products",
        blank=True,
        help_text="Ingredients used to prepare this product."
    )
    halal = models.BooleanField(default=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Product"
        verbose_name_plural = "Products"
        unique_together = ('category', 'name')

    def __str__(self):
        return self.name

class ModifierGroup(models.Model):
    """

    A group of choices for a product. E.g., "Size", "Add-ons", "Steak Temperature".
    """
    class SelectionType(models.TextChoices):
        SINGLE = 'SINGLE', 'Single Choice'
        MULTIPLE = 'MULTIPLE', 'Multiple Choices'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    products = models.ManyToManyField("core.Product", related_name='modifier_groups', blank=True)
    selection_type = models.CharField(
        max_length=20,
        choices=SelectionType.choices,
        default=SelectionType.SINGLE,
        help_text="Can the user select only one or multiple options?"
    )

    def __str__(self):
        return self.name

class ModifierOption(models.Model):
    """
    An individual option within a ModifierGroup. E.g., "Small", "Extra Cheese".
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey("core.ModifierGroup", on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Amount to add to the base price. Can be negative for a discount."
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} (+{self.price_adjustment})"

class RecipeItem(models.Model):
    product = models.ForeignKey(
        "core.Product",
        on_delete=models.CASCADE,
        related_name="recipe_items"
    )
    ingredient = models.ForeignKey(
        "core.InventoryItem",
        on_delete=models.CASCADE,
        related_name="ingredient_recipes"
    )
    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity of this ingredient used per 1 serving of the product."
    )
    unit = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ("product", "ingredient")
        ordering = ["product"]

    def __str__(self):
        unit = self.unit or self.ingredient.unit
        return f"{self.product.name} uses {self.quantity_used} {unit} of {self.ingredient.name}"

class MultiCurrencyPrice(models.Model):
    product = models.ForeignKey("core.Product", on_delete=models.CASCADE, related_name='prices')
    currency = models.CharField(max_length=6)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'currency')

    def __str__(self):
        return f"{self.product.name} - {self.currency} {self.price}"

# =============================================================================
# === ORDERS, PAYMENTS & KITCHEN ==============================================
# =============================================================================

class Order(TimeStampedModel):

    class Status(models.TextChoices):
        PLACED = 'PLACED', 'Placed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        READY = 'READY', 'Ready'
        SERVED = 'SERVED', 'Served'
        PAID = 'PAID', 'Paid'
        CANCELED = 'CANCELED', 'Canceled'
        COMPLETED = 'COMPLETED', 'Completed'

    class Meta:
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["created_at"]),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        'core.Restaurant',
        on_delete=models.PROTECT,
        related_name='orders'
    )

    customer = models.ForeignKey(
        'core.Customer',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders'
    )

    table = models.ForeignKey(
        'core.Table',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLACED
    )

    tax = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )

    service_charge = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )

    customer_session = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    objects = OrderManager()

    @property
    def total_price(self):
        total_items_price = self.items.aggregate(
            total=Sum('final_price')
        )['total'] or Decimal('0.00')

        return total_items_price + self.tax + self.service_charge

    @property
    def elapsed_time(self):
        return timezone.now() - self.created_at

    @property
    def age_status(self):
        minutes = self.elapsed_time.total_seconds() / 60

        if minutes < 30:
            return "green"
        if minutes < 45:
            return "yellow"
        return "red"

    def ensure_kitchen_ticket(self):
        if (
            self.status == Order.Status.IN_PROGRESS
            and not hasattr(self, "kitchen_ticket")
        ):
            KitchenTicket.objects.create(order=self)
            return True
        return False

    def __str__(self):
        return f"Order {str(self.id)[:8]} ({self.restaurant.name})"

class OrderItem(models.Model):

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
        ]

    order = models.ForeignKey(
        "core.Order",
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        "core.Product",
        on_delete=models.PROTECT
    )

    modifiers = models.ManyToManyField(
        "core.ModifierOption",
        blank=True
    )

    quantity = models.PositiveIntegerField(default=1)

    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, default="QUEUED")

    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total price for this line item (quantity × (base_price + modifier_prices)). Auto-calculated."
    )

    def _calculate_final_price(self):
        """Calculates the price based on product, modifiers, and quantity."""
        unit_price = self.product.base_price

        if self.pk:
            modifier_price_sum = self.modifiers.aggregate(
                total=Sum('price_adjustment')
            )['total'] or Decimal('0.00')
            unit_price += modifier_price_sum

        return unit_price * Decimal(self.quantity)

    def save(self, *args, **kwargs):
        # Calculate initial price (without modifiers if new)
        if not self.pk:
            self.final_price = self.product.base_price * Decimal(self.quantity)

        super().save(*args, **kwargs)

        # Recalculate after save if modifiers exist
        if self.pk and self.modifiers.exists():
            recalculated = self._calculate_final_price()
            if recalculated != self.final_price:
                self.__class__.objects.filter(pk=self.pk).update(
                    final_price=recalculated
                )

    @property
    def item_total(self):
        return self.final_price

    def __str__(self):
        return f"{self.quantity}x {self.product.name} for Order {self.order.id}"
    
class KitchenTicket(models.Model):
    order = models.OneToOneField("core.Order", on_delete=models.CASCADE, related_name="kitchen_ticket")
    created_at = models.DateTimeField(auto_now_add=True)
    printed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Kitchen Ticket #{self.pk} for Order {self.order.id}"

class AnalyticsSnapshot(models.Model):
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(default=date.today)
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    top_selling_item = models.CharField(max_length=120, blank=True)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('restaurant', 'date')

    def __str__(self):
        return f"Analytics {self.restaurant.name} ({self.date})"

class APIToken(models.Model):
    device_name = models.CharField(max_length=100)
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE, related_name='api_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_name} ({'Active' if self.active else 'Inactive'})"

class ChatMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="chat_messages",
        null=True,
        blank=True,
        help_text="If applicable, scope message to a particular restaurant.",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_chat_messages",
        help_text="User who sent the message (retained even if user is deleted).",
    )
    content = models.TextField(help_text="Raw text of the chat message.")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    system_generated = models.BooleanField(default=False)
    important = models.BooleanField(
        default=False,
        help_text="If marked, indicates this message was flagged as important in UI.",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["restaurant", "timestamp"]),
        ]

    def __str__(self):
        sender = self.sender.username if self.sender else "System"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {sender}: {self.content[:40]}"

class LoyaltyTier(models.Model):
    name = models.CharField(max_length=50, unique=True)
    points_required = models.PositiveIntegerField()
    reward_description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name} ({self.points_required} pts)"
    
    Customer.add_to_class(
    "current_tier",
    models.ForeignKey(
        "core.LoyaltyTier",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customers"
    ),
)

def assign_tier(customer: "Customer"):
    tiers = LoyaltyTier.objects.order_by("points_required")
    chosen = None
    for tier in tiers:
        if customer.loyalty_points >= tier.points_required:
            chosen = tier
    if chosen:
        customer.current_tier = chosen



class Rider(models.Model):
    restaurant = models.ForeignKey(
        "core.Restaurant", on_delete=models.CASCADE, related_name="riders"
    )
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    phone = models.CharField(max_length=20, blank=True)
    current_order = models.ForeignKey(
        "core.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_rider"
    )

    def __str__(self):
        return f"{self.name} ({'Active' if self.active else 'Offline'})"

class Refund(models.Model):
    order = models.OneToOneField(
        "core.Order",
        on_delete=models.CASCADE,
        related_name="refund_record"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund for Order {str(self.order.id)[:8]}"

class PaymentMethod(models.Model):
    name = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    order = models.ForeignKey(
        "core.Order",
        on_delete=models.CASCADE,
        related_name="payments"
    )
    method = models.CharField(
        max_length=50,
        default="unknown",
        help_text="e.g., cash, card, stripe, mobile_money"
    )
    stripe_payment_intent = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Stripe PaymentIntent ID, if applicable."
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount paid for this payment transaction."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Receipts, POS references, or transaction codes."
    )

    def __str__(self):
        return f"{self.order.id} - {self.method} - {self.amount} ({self.status})"

class PaymentIntentLog(models.Model):
    intent_id = models.CharField(max_length=200, unique=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

class DailyReport(models.Model):
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE)
    date = models.DateField()
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ("restaurant", "date")

    def __str__(self):
        return f"{self.restaurant.name} - {self.date}"

class Settings(models.Model):
    """
    A model to store application-wide settings.
    This is designed to have only ONE row (singleton pattern).
    """
    # General Settings
    restaurant_name = models.CharField(max_length=100, default="RestaurantSys")
    currency_symbol = models.CharField(max_length=5, default="$")

    # Display & Theme Settings
    THEME_CHOICES = [
        ('system', 'System Preference'),
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
    ]
    default_theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')
    items_per_page = models.PositiveIntegerField(default=20)

    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    stock_alerts = models.BooleanField(default=False)

    def __str__(self):
        return "Application Settings"

    class Meta:
        # Enforces that there's only one settings object
        verbose_name = "Application Settings"
        verbose_name_plural = "Application Settings"