# C:\Users\Administrator\restaurant_management\core\models.py

import uuid
from datetime import date, timedelta
from io import BytesIO
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum, F, DecimalField, Q
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.files.base import File
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from django.db.models.functions import Coalesce

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
    # PLATFORM AUTHORITY
    # =====================================================

    is_platform_owner = models.BooleanField(default=False)

    
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

    # ✅ Restaurant-level users must belong to a restaurant
        if (
            not self.is_superuser
            and not self.is_platform_owner
            and not self.restaurant
        ):
            raise ValidationError("Restaurant users must belong to a restaurant.")

        # ✅ Superuser always has admin access
        if self.is_superuser:
            self.is_staff = True

        # ✅ Platform owner has admin access (but is not necessarily superuser)
        elif self.is_platform_owner:
            self.is_staff = True

        # ✅ Restaurant manager can access Django admin (optional choice)
        else:
            self.is_staff = self.role == self.Roles.MANAGER

        super().save(*args, **kwargs)
    # =====================================================
    # ROLE HELPERS (RBAC LAYER)
    # =====================================================

    @property
    def is_owner(self):
        return self.is_platform_owner

    @property
    def is_manager(self):
        return self.role == self.Roles.MANAGER or self.is_platform_owner

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
        return self.is_platform_owner or self.role == self.Roles.MANAGER
    
    
    @property
    def can_access_pos(self):
        allowed_roles = {
            self.Roles.CASHIER,
            self.Roles.SERVER,
            self.Roles.MANAGER,
        }

        return (
            self.is_superuser
            or self.is_platform_owner
            or self.role in allowed_roles
        )

    @property
    def can_access_kitchen(self):
        return self.is_cook or self.role == self.Roles.MANAGER or self.is_platform_owner

    
    @property
    def can_view_reports(self):
        return self.role == self.Roles.MANAGER or self.is_platform_owner

    @property
    def can_manage_settings(self):
        return self.role == self.Roles.MANAGER or self.is_platform_owner
    
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
    
    CURRENCY_CHOICES = [
        ("USD", "US Dollar ($)"),
        ("EUR", "Euro (€)"),
        ("GBP", "British Pound (£)"),
        ("CAD", "Canadian Dollar ($)"),
        ("AUD", "Australian Dollar ($)"),
        ("HKD", "Hong Kong Dollar (HK$)"),
        ("TRY", "Turkish Lira (₺)"),
        ("NGN", "Nigerian Naira (₦)"),
        ("GMD", "Gambian Dalasi (D)"),
        ("INR", "Indian Rupee (₹)"),
        ("JPY", "Japanese Yen (¥)"),
        ("CNY", "Chinese Yuan (¥)"),
        ("ZAR", "South African Rand (R)"),
        ("AED", "UAE Dirham (د.إ)"),
        ("SAR", "Saudi Riyal (﷼)"),
        ("SEK", "Swedish Krona (kr)"),
        ("NOK", "Norwegian Krone (kr)"),
        ("DKK", "Danish Krone (kr)"),
        ("CHF", "Swiss Franc (CHF)"),
        ("SGD", "Singapore Dollar (S$)"),
        ("BRL", "Brazilian Real (R$)"),
        ("MXN", "Mexican Peso ($)"),
        ("KES", "Kenyan Shilling (KSh)"),
        ("RWF", "Rwandan Franc (FRw)"),
    ]

    
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name='restaurants')
    name = models.CharField(max_length=100)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)

    country = models.CharField(max_length=60, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=6, default="USD")
    logo = models.ImageField(upload_to="restaurants/logos/", null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=RestaurantStatus.choices, default=RestaurantStatus.OPEN)
    display_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    slug = models.SlugField(unique=True)
    def __str__(self):
        return f"{self.name} ({self.company.name})"
    @property
    def profile_complete(self):
        return all([
            self.address_line_1,
            self.city,
            self.country,
        ])
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
    
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
    capacity = models.PositiveIntegerField(default=4)
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
        
    @property
    def current_status(self):
        active_session = self.sessions.filter(is_active=True).exists()

        if active_session:
            return self.Status.OCCUPIED

        return self.Status.AVAILABLE    
    

class TableSection(models.Model):
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    label = models.CharField(max_length=5)  # A, B, Left, Right

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("table", "label")

    def __str__(self):
        return f"{self.table.table_number}{self.label}"
    

from decimal import Decimal
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class TableSession(models.Model):

    class SessionType(models.TextChoices):
        TABLE = "TABLE", "Table"
        TAKEAWAY = "TAKEAWAY", "Takeaway"

    # -------------------------------------------------
    # CORE RELATIONS
    # -------------------------------------------------

    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    table = models.ForeignKey(
        "core.Table",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    section = models.ForeignKey(
        "core.TableSection",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.TABLE,
        db_index=True,
    )

    # -------------------------------------------------
    # TIMESTAMPS
    # -------------------------------------------------

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)

    # -------------------------------------------------
    # ✅ FINAL SNAPSHOT (NEW)
    # -------------------------------------------------

    final_subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    final_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    final_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # -------------------------------------------------
    # META
    # -------------------------------------------------

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["table", "section"],
                condition=Q(is_active=True, session_type="TABLE"),
                name="unique_active_table_section_session"
            ),
        ]

        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["session_type", "is_active"]),
        ]

    # -------------------------------------------------
    # LIVE FINANCIAL PROPERTIES
    # (Used while session is active)
    # -------------------------------------------------

    @property
    def total_amount(self):
        return self.orders.aggregate(
            total=Coalesce(
                Sum("total"),
                Decimal("0.00"),
                output_field=DecimalField()
            )
        )["total"]
        
    @property
    def total_paid(self):
        return (
            self.orders.aggregate(
                total=Sum("payments__amount")
            )["total"]
            or Decimal("0.00")
        )

    @property
    def remaining_balance(self):
        return self.total_amount - self.total_paid

    @property
    def is_fully_paid(self):
        return self.remaining_balance <= 0

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------

    def is_full_table(self):
        return (
            self.session_type == self.SessionType.TABLE
            and self.section is None
        )

    def is_takeaway(self):
        return self.session_type == self.SessionType.TAKEAWAY

    # -------------------------------------------------
    # ✅ IMPROVED CLOSE LOGIC
    # -------------------------------------------------

    def close(self):
        """
        Safely close session.
        Prevent closing if unpaid balance exists.
        Snapshot financial totals for audit safety.
        """

        if self.remaining_balance > 0:
            raise ValueError("Cannot close session with unpaid balance.")

        # ✅ Calculate subtotal from orders
        subtotal = self.total_amount

        # ✅ Get tax rate from restaurant (fallback 10%)
        tax_rate = getattr(
            self.restaurant,
            "tax_rate",
            Decimal("10.00")
        )

        tax_rate_decimal = Decimal(tax_rate) / Decimal("100")

        tax = subtotal * tax_rate_decimal
        grand_total = subtotal + tax

        # ✅ Snapshot values
        self.final_subtotal = subtotal
        self.final_tax = tax
        self.final_total = grand_total

        self.is_active = False
        self.closed_at = timezone.now()

        self.save(update_fields=[
            "final_subtotal",
            "final_tax",
            "final_total",
            "is_active",
            "closed_at",
        ])

    # -------------------------------------------------

    def __str__(self):
        if self.session_type == self.SessionType.TAKEAWAY:
            return f"Takeaway Session #{self.id}"

        if self.section:
            return f"{self.table.table_number}{self.section.label} Session"

        return f"Full Table {self.table.table_number} Session"
    
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
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this category from POS."
    )
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        unique_together = ('name', 'parent', 'menu')
        
    def clean(self):
        if self.parent and self.parent.menu != self.menu:
            raise ValidationError("Parent category must belong to the same menu.")

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

    prep_time = models.PositiveIntegerField(
        default=10,
        help_text="Average preparation time in minutes"
    )
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Product"
        verbose_name_plural = "Products"
        unique_together = ('category', 'name')
        
    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )
    name = models.CharField(max_length=100)  # Small, Large, etc.
    price = models.DecimalField(max_digits=10, decimal_places=2)

    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.product.name} - {self.name}"


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
# === # =============================================================================
# ORDERS
# =============================================================================

class Order(TimeStampedModel):

    # -------------------------------------------------
    # ORDER TYPE
    # -------------------------------------------------
    class OrderType(models.TextChoices):
        DINE_IN = "DINE_IN", "Dine In"
        TAKEOUT = "TAKEOUT", "Takeout"
        DELIVERY = "DELIVERY", "Delivery"

    # -------------------------------------------------
    # OPERATIONAL STATUS
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
    # PAYMENT STATUS
    # -------------------------------------------------
    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        REFUNDED = "REFUNDED", "Refunded"

    # -------------------------------------------------
    # META
    # -------------------------------------------------
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["restaurant", "payment_status"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "order_type"]),
        ]
    # -------------------------------------------------
    # IDENTIFICATION
    # -------------------------------------------------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order_number = models.PositiveIntegerField(null=True, blank=True, editable=False)

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

    section = models.ForeignKey(
        "core.TableSection",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    session = models.ForeignKey(
        "core.TableSession",
        on_delete=models.PROTECT,
        related_name="orders"
    )

    # -------------------------------------------------
    # CORE FIELDS
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
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders_created"
    )
    
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    notes = models.TextField(blank=True, null=True)

    # -------------------------------------------------
    # FINANCIALS
    # -------------------------------------------------
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tip = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    objects = OrderManager()

    # =============================================================================
    # FACTORY METHODS (SECTION + FULL TABLE SUPPORT)
    # =============================================================================

    @classmethod
    def create_for_table(cls, table, **extra_fields):

        with transaction.atomic():

            table = (
                Table.objects
                .select_for_update()
                .get(pk=table.pk)
            ) 

            # Block if any section active
            if TableSession.objects.filter(
                table=table,
                section__isnull=False,
                is_active=True
            ).exists():
                raise ValueError("One or more sections are occupied.")

            session, _ = TableSession.objects.get_or_create(
                table=table,
                section=None,
                restaurant=table.restaurant,
                is_active=True,
            )

            return cls._create_for_session(session, None, **extra_fields)
    
    @property
    def is_editable(self):
        return (
            self.payment_status != self.PaymentStatus.PAID and
            self.status not in [self.Status.COMPLETED, self.Status.CANCELED]
        )
    
    @classmethod
    def create_for_section(cls, section, **extra_fields):

        with transaction.atomic():

            # Lock the table row
            table = (
                Table.objects
                .select_for_update()
                .get(pk=section.table_id)
            )

            # Check full-table occupation
            if TableSession.objects.filter(
                table=table,
                section__isnull=True,
                is_active=True
            ).exists():
                raise ValueError("Entire table is currently occupied.")

            # Lock the section row
            section = (
                TableSection.objects
                .select_for_update()
                .get(pk=section.pk)
            )

            session, _ = TableSession.objects.get_or_create(
                table=table,
                section=section,
                restaurant=table.restaurant,
                is_active=True,
            )

            return cls._create_for_session(session, section, **extra_fields)
    @property
    def total_paid(self):
        return self.payments.aggregate(
        total=Sum("amount")
        )["total"] or Decimal("0.00")


    @property
    def remaining_balance(self):
        return self.total_price - self.total_paid


    @property
    def is_fully_paid(self):
        return self.remaining_balance <= 0

    @classmethod
    def _create_for_session(cls, session, section, **extra_fields):
        """
        Internal helper to create order linked to a session.
        Ensures only one active order per session.
        """
        # Lock session row
        TableSession.objects.select_for_update().get(pk=session.pk)
        
        # Prevent duplicate active order for same session
        existing = cls.objects.filter(
            session=session,
            status__in=[
                cls.Status.DRAFT,
                cls.Status.PLACED,
                cls.Status.IN_PROGRESS,
                cls.Status.READY,
                cls.Status.SERVED,
            ]
        ).first()

        if existing:
            return existing

        order = cls.objects.create(
            restaurant=session.restaurant,
            table=session.table,
            section=section,
            session=session,
            order_type=cls.OrderType.DINE_IN,
            status=cls.Status.DRAFT,
            payment_status=cls.PaymentStatus.UNPAID,
            **extra_fields
        )

        return order
    
    
    # =============================================================================
    # CALCULATIONS
    # =============================================================================

    def calculate_totals(self):

        subtotal = self.items.aggregate(
            total=Sum("final_price")
        )["total"] or Decimal("0.00")

        self.subtotal = subtotal

        self.total = (
            subtotal
            + self.tax
            + self.service_charge
            + self.tip
            - self.discount
        )

        super().save(update_fields=["subtotal", "total"])
        
    # =============================================================================
    # STATE MACHINE
    # =============================================================================

    VALID_TRANSITIONS = {
        Status.DRAFT: [Status.PLACED],
        Status.PLACED: [Status.IN_PROGRESS, Status.CANCELED],
        Status.IN_PROGRESS: [Status.READY],
        Status.READY: [Status.SERVED],
        Status.SERVED: [Status.COMPLETED],
    }

    def transition_to(self, new_status, actor=None):

        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from {self.status} to {new_status}")

        old_status = self.status

        if actor:
            self._validate_actor_permission(new_status, actor)

        self.status = new_status
        self.save(update_fields=["status"])

        OrderStatusHistory.objects.create(
            order=self,
            restaurant=self.restaurant,
            from_status=old_status,
            to_status=new_status,
            changed_by=actor
        )

    # =============================================================================
    # COMPLETION LOGIC
    # =============================================================================

    def complete_order(self, actor=None):
        if self.payment_status != self.PaymentStatus.PAID:
            raise PermissionDenied("Order must be paid before completion.")

        self.transition_to(self.Status.COMPLETED, actor=actor)

        # Close session
        if self.session and self.session.is_active:
            self.session.close()

    # =============================================================================
    # SAVE OVERRIDE
    # =============================================================================

    def save(self, *args, **kwargs):

        creating = self._state.adding

        # Get previous status before saving (for transition detection)
        previous_status = None
        if not creating and self.pk:
            previous_status = (
                Order.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        # ✅ Auto-generate order number (only on create)
        if creating and not self.order_number:
            last_number = (
                Order.objects.filter(restaurant=self.restaurant)
                .aggregate(models.Max("order_number"))["order_number__max"]
            )
            self.order_number = (last_number or 0) + 1

        super().save(*args, **kwargs)

        # ✅ Kitchen ticket auto-create when entering IN_PROGRESS
        if (
            self.status == self.Status.IN_PROGRESS
            and previous_status != self.Status.IN_PROGRESS
        ):
            KitchenTicket.objects.get_or_create(order=self)

        # ✅ Auto-close session when order completes or is canceled
        if (
            self.status in [self.Status.COMPLETED, self.Status.CANCELED]
            and previous_status not in [self.Status.COMPLETED, self.Status.CANCELED]
        ):
            if self.session and self.session.is_active:
                self.session.is_active = False
                self.session.closed_at = timezone.now()
                self.session.save()

    # =============================================================================
    # HELPERS
    # =============================================================================

    @property
    def is_active(self):
        return self.status not in [self.Status.CANCELED, self.Status.COMPLETED]

    def short_id(self):
        return str(self.id)[:8]
    
    
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
        related_name="items"
    )

    product = models.ForeignKey(
        "core.Product",
        on_delete=models.PROTECT
    )
    
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
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
        default=Decimal("0.00")
    )

    
    # -------------------------------------------------
    # CALCULATED SUBTOTAL
    # -------------------------------------------------

    @property
    def subtotal(self):
        base_price = (
            self.variant.price if self.variant else self.product.base_price
        )

        modifiers_total = sum(
            mod.price_adjustment for mod in self.modifiers.all()
        )

        return (base_price + modifiers_total) * self.quantity
    # -------------------------------------------------
    # SAVE OVERRIDE
    # -------------------------------------------------

    def save(self, *args, **kwargs):

        with transaction.atomic():

            order = (
                type(self.order).objects
                .select_for_update()
                .get(pk=self.order.pk)
            )

            if order.payment_status == order.PaymentStatus.PAID:
                raise PermissionDenied("Cannot modify items on a paid order.")

            if order.status in [
                order.Status.COMPLETED,
                order.Status.CANCELED
            ]:
                raise PermissionDenied("Cannot modify items on a closed order.")

            if self.product.category.menu.restaurant_id != self.order.restaurant_id:
                raise ValidationError("Product does not belong to the same restaurant as the order.")
            is_new = self.pk is None
            super().save(*args, **kwargs)
            final_price = self.subtotal
            # ✅ Update using queryset to avoid re-insert issues
            type(self).objects.filter(pk=self.pk).update(
                final_price=final_price
            )
            self.final_price = final_price
            order.calculate_totals()
    # -------------------------------------------------
    # DELETE OVERRIDE
    # -------------------------------------------------

    def delete(self, *args, **kwargs):

        with transaction.atomic():

            order = (
                type(self.order).objects
                .select_for_update()
                .get(pk=self.order.pk)
            )

            if order.payment_status == order.PaymentStatus.PAID:
                raise PermissionDenied("Cannot delete items from a paid order.")

            if order.status in [
                order.Status.COMPLETED,
                order.Status.CANCELED
            ]:
                raise PermissionDenied("Cannot delete items from a closed order.")

            super().delete(*args, **kwargs)

            order.calculate_totals()

class OrderStatusHistory(models.Model):

    order = models.ForeignKey(
        "core.Order",
        on_delete=models.CASCADE,
        related_name="status_history"
    )

    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="order_status_history"
    )

    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"Order #{self.order.order_number}: {self.from_status} → {self.to_status}"
    
    
    
class KitchenTicket(models.Model):

    # -------------------------------------------------
    # KITCHEN STATUS
    # -------------------------------------------------
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        PREPARING = "PREPARING", "Preparing"
        COMPLETED = "COMPLETED", "Completed"

    order = models.OneToOneField(
        "core.Order",
        on_delete=models.CASCADE,
        related_name="kitchen_ticket"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    printed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    # -------------------------------------------------
    # STATUS TRANSITIONS
    # -------------------------------------------------

    def start_preparation(self):
        if self.status != self.Status.QUEUED:
            raise ValueError("Ticket is not in queued state")

        self.status = self.Status.PREPARING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        if self.status != self.Status.PREPARING:
            raise ValueError("Ticket must be preparing before completion")

        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

        self.order.transition_to(Order.Status.READY)

    # -------------------------------------------------
    # STRING
    # -------------------------------------------------

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

def assign_tier(customer):
    chosen = None

    for tier in LoyaltyTier.objects.filter(
        restaurant=customer.restaurant
    ).order_by("-min_points"):
        if customer.loyalty_points >= tier.min_points:
            chosen = tier
            break

    if chosen and customer.current_tier != chosen:
        customer.current_tier = chosen
        customer.save(update_fields=["current_tier"])


class Refund(models.Model):
    order = models.OneToOneField(
        "Order",
        on_delete=models.CASCADE,
        related_name="refund_record"
    )

    shift = models.ForeignKey(
        "CashierShift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund #{self.id} - Order {self.order.id}"

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
    
    shift = models.ForeignKey(
        "core.CashierShift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="cashier_shifts"
    )

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    starting_cash = models.DecimalField(max_digits=10, decimal_places=2)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # ✅ NEW FIELDS
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_difference = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"Cashier Shift {self.id} - {self.user.username}"
    
    

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
    
    
class StaffShift(models.Model):

    restaurant = models.ForeignKey(
        'Restaurant',
        on_delete=models.CASCADE,
        related_name='staff_shifts'
    )

    staff = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='staff_shifts'
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def clean(self):
        if self.staff.restaurant != self.restaurant:
            raise ValidationError("Staff must belong to the same restaurant.")

    def __str__(self):
        return f"{self.staff.username} | {self.start_time} - {self.end_time}"



class WaiterCall(TimeStampedModel):
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE)
    table = models.ForeignKey("core.Table", on_delete=models.CASCADE)
    order = models.ForeignKey("core.Order", on_delete=models.CASCADE, null=True, blank=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Call from Table {self.table.table_number}"
    
class Subscription(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=100)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)