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
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


class CustomUser(AbstractUser):

    # =====================================================
    # ROLES
    # =====================================================

    class Roles(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        SERVER = 'SERVER', 'Server'
        COOK = 'COOK', 'Cook'
        CASHIER = 'CASHIER', 'Cashier'
        CUSTOMER = 'CUSTOMER', 'Customer'
        STAFF = 'STAFF', 'General Staff'

    # =====================================================
    # RELATIONS
    # =====================================================

    restaurant = models.ForeignKey(
        'core.Restaurant',
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True
    )

    # =====================================================
    # FIELDS
    # =====================================================

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

    # =====================================================
    # SAVE LOGIC
    # =====================================================

    def save(self, *args, **kwargs):

        # ✅ Non-superusers must belong to a restaurant
        if not self.is_superuser and not self.restaurant:
            raise ValidationError ("Non-superusers must belong to a restaurant.")

        # ✅ Superuser = full platform owner
        if self.is_superuser:
            self.is_staff = True
        else:
            # ✅ Only MANAGER gets Django admin access
            self.is_staff = self.role == self.Roles.MANAGER

        super().save(*args, **kwargs)

    # =====================================================
    # ROLE HELPERS (RBAC LAYER)
    # =====================================================

    @property
    def is_owner(self):
        return self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.Roles.MANAGER or self.is_owner

    @property
    def is_cashier(self):
        return self.role == self.Roles.CASHIER or self.is_manager

    @property
    def is_server(self):
        return self.role == self.Roles.SERVER

    @property
    def is_cook(self):
        return self.role == self.Roles.COOK

    @property
    def is_customer(self):
        return self.role == self.Roles.CUSTOMER

    @property
    def is_general_staff(self):
        return self.role == self.Roles.STAFF

    # =====================================================
    # PERMISSION CAPABILITIES
    # =====================================================

    @property
    def can_manage_staff(self):
        return self.is_owner or self.role == self.Roles.MANAGER
    
    
    @property
    def can_access_pos(self):
        return self.is_cashier or self.is_server

    @property
    def can_access_kitchen(self):
        return self.is_cook or self.is_manager

    @property
    def can_view_reports(self):
        return self.is_manager

    @property
    def can_manage_settings(self):
        return self.is_manager
    
    # =====================================================
    # STRING REPRESENTATION
    # =====================================================

    def __str__(self):
        return f"{self.username} ({self.role})"
    
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

    check_in = models.DateTimeField(default=timezone.now)
    check_out = models.DateTimeField(blank=True, null=True)

    # Optional — keep only if Shift model exists
    shift = models.ForeignKey(
    "core.CashierShift",
    on_delete=models.CASCADE,
    related_name="attendances"
)

    class Meta:
        ordering = ["-check_in"]

    # =====================================================
    # VALIDATION
    # =====================================================

    def clean(self):
        # ✅ Prevent CUSTOMER from clocking in
        if self.employee.role == self.employee.Roles.CUSTOMER:
            raise ValidationError("Customers cannot have attendance records.")

        # ✅ Ensure employee belongs to this restaurant
        if not self.employee.is_superuser and self.employee.restaurant != self.restaurant:
            raise ValidationError("Employee does not belong to this restaurant.")

        # ✅ Prevent multiple open attendances
        if not self.pk:
            active = Attendance.objects.filter(
                employee=self.employee,
                check_out__isnull=True
            ).exists()

            if active:
                raise ValidationError("Employee already has an active attendance record.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =====================================================
    # HELPERS
    # =====================================================

    @property
    def duration(self):
        if self.check_out:
            return self.check_out - self.check_in
        return timezone.now() - self.check_in  # live duration if still clocked in

    def __str__(self):
        return f"{self.employee} - {self.restaurant.name} ({self.check_in:%Y-%m-%d})"
    
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
    display_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

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

        # ✅ NEW CODE STARTS HERE
        restaurant_logo = self.restaurant.logo if hasattr(self.restaurant, "logo") else None

        width, height = qr_img.size

        logo_height = 0
        logo_img = None

        if restaurant_logo and hasattr(restaurant_logo, "path"):
            try:
                logo_img = Image.open(restaurant_logo.path)
                logo_img.thumbnail((width, 100))
                logo_height = logo_img.size[1] + 20
            except Exception:
                logo_img = None

        text_space = 60
        new_height = height + text_space + logo_height

        combined = Image.new("RGB", (width, new_height), "white")

        current_y = 0

        # ✅ Paste logo if exists
        if logo_img:
            logo_x = (width - logo_img.size[0]) // 2
            combined.paste(logo_img, (logo_x, current_y))
            current_y += logo_height

        # ✅ Paste QR
        combined.paste(qr_img, (0, current_y))
        current_y += height
        # ✅ NEW CODE ENDS HERE

        draw = ImageDraw.Draw(combined)

        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()

        text = f"Table {self.table_number}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (width - text_width) // 2

        draw.text((text_x, current_y + 20), text, font=font, fill="black")

        buffer = BytesIO()
        combined.save(buffer, format="PNG")

        safe_label = str(self.table_number).replace(" ", "_")
        filename = f"qr_table_{safe_label}_{self.id}.png"
        self.qr_code.save(filename, File(buffer), save=False)
        buffer.close()
    
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

# =============================================================================
# ORDERS
# =============================================================================

class Order(TimeStampedModel):

    # -------------------------------------------------
    # ORDER TYPE (Dine-in, Takeout, Delivery)
    # -------------------------------------------------
    class OrderType(models.TextChoices):
        DINE_IN = "DINE_IN", "Dine In"
        TAKEOUT = "TAKEOUT", "Takeout"
        DELIVERY = "DELIVERY", "Delivery"

    # -------------------------------------------------
    # ORDER STATUS (Operational flow)
    # -------------------------------------------------
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PLACED = "PLACED", "Placed"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        READY = "READY", "Ready"
        SERVED = "SERVED", "Served"
        CANCELED = "CANCELED", "Canceled"
        COMPLETED = "COMPLETED", "Completed"

    # -------------------------------------------------
    # PAYMENT STATUS (Financial state)
    # -------------------------------------------------
    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        REFUNDED = "REFUNDED", "Refunded"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "order_type"]),
            models.Index(fields=["created_at"]),
        ]

    # -------------------------------------------------
    # IDENTIFICATION
    # -------------------------------------------------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order_number = models.PositiveIntegerField(
    editable=False,
    null=True,
    blank=True
    )
       
    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.PROTECT,
        related_name="orders"
    )

    # -------------------------------------------------
    # RELATIONS
    # -------------------------------------------------
    customer = models.ForeignKey(
        "core.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders"
    )

    table = models.ForeignKey(
        "core.Table",
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    # -------------------------------------------------
    # CORE ORDER FIELDS
    # -------------------------------------------------
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.DINE_IN
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID
    )

    notes = models.TextField(blank=True, null=True)

    # -------------------------------------------------
    # FINANCIALS
    # -------------------------------------------------
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    customer_session = models.CharField(max_length=50, blank=True, null=True)

    objects = OrderManager()

    # =============================================================================
    # CALCULATIONS
    # =============================================================================

    def calculate_totals(self):
        subtotal = self.items.aggregate(
            total=Sum("final_price")
        )["total"] or Decimal("0.00")

        self.subtotal = subtotal
        self.total = subtotal + self.tax + self.service_charge - self.discount

        super().save(update_fields=["subtotal", "total"])

    # =============================================================================
    # STATUS HELPERS
    # =============================================================================

    @property
    def is_active(self):
        return self.status not in [
            self.Status.CANCELED,
            self.Status.COMPLETED,
        ]

    @property
    def is_paid(self):
        return self.payment_status == self.PaymentStatus.PAID

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

    # =============================================================================
    # STATUS TRANSITIONS
    # =============================================================================

    def mark_as_placed(self):
        if self.status == self.Status.DRAFT:
            self.status = self.Status.PLACED
            self.save(update_fields=["status"])

    def send_to_kitchen(self):
        if self.status in [self.Status.PLACED, self.Status.DRAFT]:
            self.status = self.Status.IN_PROGRESS
            self.save(update_fields=["status"])

    def mark_ready(self):
        if self.status == self.Status.IN_PROGRESS:
            self.status = self.Status.READY
            self.save(update_fields=["status"])

    def mark_served(self):
        if self.status == self.Status.READY:
            self.status = self.Status.SERVED
            self.save(update_fields=["status"])

    def complete_order(self):
        if self.payment_status == self.PaymentStatus.PAID:
            self.status = self.Status.COMPLETED
            self.save(update_fields=["status"])

    # =============================================================================
    # SAVE OVERRIDE (KITCHEN AUTOMATION)
    # =============================================================================

    def save(self, *args, **kwargs):
        creating = self._state.adding

        # Generate sequential order number per restaurant
        if creating and not self.order_number:
            last_number = (
            Order.objects.filter(restaurant=self.restaurant)
            .aggregate(models.Max("order_number"))["order_number__max"]
            )
            self.order_number = (last_number or 0) + 1

        old_status = None
        if not creating:
            old_status = Order.objects.filter(pk=self.pk).values_list(
            "status", flat=True
            ).first()

        super().save(*args, **kwargs)

        # Only trigger when status changes TO IN_PROGRESS
        if self.status == self.Status.IN_PROGRESS and old_status != self.Status.IN_PROGRESS:
            KitchenTicket.objects.get_or_create(order=self)
    # =============================================================================
    # STRING REPRESENTATION
    # =============================================================================

    def __str__(self):
        return f"Order #{self.order_number} - {self.restaurant.name}"
    
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
        return f"{self.quantity}x {self.product.name} for Order #{self.order.order_number}" 
       
class KitchenTicket(models.Model):
    order = models.OneToOneField("core.Order", on_delete=models.CASCADE, related_name="kitchen_ticket")
    created_at = models.DateTimeField(auto_now_add=True)
    printed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Kitchen Ticket #{self.pk} for Order #{self.order.order_number}"

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

    restaurant = models.OneToOneField(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="settings",
        null=True,
        blank=True,
    )

    # ===============================
    # General Settings
    # ===============================

    restaurant_display_name = models.CharField(max_length=150)
    currency_symbol = models.CharField(max_length=5, default="$")
    timezone = models.CharField(max_length=50, default="UTC")

    # ===============================
    # Tax & Charges
    # ===============================

    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    service_charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    prices_include_tax = models.BooleanField(default=False)

    # ===============================
    # Order Behavior
    # ===============================

    auto_mark_order_paid = models.BooleanField(default=False)
    allow_split_payments = models.BooleanField(default=True)
    allow_table_merge = models.BooleanField(default=True)

    # ===============================
    # Receipt Settings
    # ===============================

    show_logo_on_receipt = models.BooleanField(default=True)
    receipt_footer_text = models.CharField(max_length=255, blank=True, null=True)

    # ===============================
    # Inventory Settings
    # ===============================

    stock_alerts_enabled = models.BooleanField(default=True)
    auto_deduct_inventory = models.BooleanField(default=True)

    # ✅ ADD THIS SECTION HERE
    # ===============================
    # Notification Settings
    # ===============================

    email_notifications_enabled = models.BooleanField(default=True)
    send_daily_sales_report = models.BooleanField(default=False)
    low_stock_email_alerts = models.BooleanField(default=True)
    notify_on_new_order = models.BooleanField(default=True)

    # ===============================
    # UI Settings
    # ===============================

    THEME_CHOICES = [
        ('system', 'System Preference'),
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
    ]

    default_theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='system'
    )

    items_per_page = models.PositiveIntegerField(default=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.restaurant.name} Settings"
    
class CashierShift(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cashier_shifts"
    )
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    starting_cash = models.DecimalField(max_digits=10, decimal_places=2)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )

    restaurant = models.ForeignKey(
        "Restaurant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)

    changes = models.JSONField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.timestamp} | {self.user} | {self.action} | {self.model_name}"
    
    
class Shift(models.Model):

    restaurant = models.ForeignKey(
        'Restaurant',
        on_delete=models.CASCADE,
        related_name='shifts'
    )

    staff = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='shifts'
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']
    
    def clean(self):
        if self.staff.restaurant != self.restaurant:
            raise ValidationError("Staff must belong to the same restaurant.")
    
    def __str__(self):
        return f"{self.staff.username} | {self.start_time} - {self.end_time}"