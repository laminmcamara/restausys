# C:\Users\Administrator\restaurant_management\core\models.py

import uuid
from datetime import date, timedelta
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
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
import secrets
import uuid

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

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="companies",
        null=True,
        blank=True,
    )

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
    language = models.CharField(max_length=10, default='en')

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

        # ✅ Platform owner has admin access
        elif self.is_platform_owner:
            self.is_staff = True

        # ✅ Restaurant manager may access Django admin
        else:
            self.is_staff = self.role == self.Roles.MANAGER

        super().save(*args, **kwargs)

    # =====================================================
    # ROLE HELPERS (Hierarchical)
    # =====================================================

    @property
    def is_owner(self):
        return self.is_platform_owner or self.is_superuser

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
    # PERMISSION CAPABILITIES (Capability-Based Access)
    # =====================================================

    @property
    def can_manage_staff(self):
        return self.is_manager

    @property
    def can_access_pos(self):
        return self.is_cashier or self.is_server

    @property
    def can_access_kitchen(self):
        return self.is_cook or self.is_manager
    
    @property
    def can_access_public_display(self):
        return self.is_manager

    @property
    def can_view_dashboard(self):
        return self.is_manager

    @property
    def can_view_reports(self):
        return self.is_manager

    @property
    def can_manage_products(self):
        return self.is_manager

    @property
    def can_manage_tables(self):
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
        if self.is_default:
            Printer.objects.filter(
                printer_type=self.printer_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

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
    restaurant = models.ForeignKey(
        'Restaurant', 
        on_delete=models.CASCADE, 
        related_name='customers',
        null=True, 
        blank=True
    )
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
def generate_display_key():
    return secrets.token_hex(16)



class Restaurant(TimeStampedModel):

    class RestaurantStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        HOLIDAY = "HOLIDAY", "Holiday Hours"

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

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="restaurants",
    )

    name = models.CharField(max_length=100)

    display_key = models.CharField(
        max_length=64,
        unique=True,
        default=generate_display_key,
    )

    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=60, blank=True)

    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text="IANA timezone name, e.g. UTC, Europe/London, Africa/Banjul",
    )

    currency = models.CharField(
        max_length=6,
        choices=CURRENCY_CHOICES,
        default="USD",
    )

    locale = models.CharField(
        max_length=10,
        default="en_US",
        help_text="Locale for formatting, e.g. en_US, de_DE, fr_FR",
    )

    logo = models.ImageField(
        upload_to="restaurants/logos/",
        null=True,
        blank=True,
    )
    

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=RestaurantStatus.choices,
        default=RestaurantStatus.OPEN,
    )

    display_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    
    onboarding_completed = models.BooleanField(
        default=False,
    )

    onboarding_completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    slug = models.SlugField(unique=True)

    # =====================================================
    # SUBSCRIPTION LOGIC
    # =====================================================

    @property
    def subscription_valid(self):
        """
        Returns True if the restaurant currently has access.

        Access is valid when the related Subscription exists and is either:
        - trialing with time remaining
        - active with time remaining
        """
        subscription = getattr(self, "subscription", None)

        if not subscription:
            return False

        subscription.expire_if_needed()
        return subscription.is_active()

    @property
    def subscription_days_remaining(self):
        """
        Returns the number of days remaining in the current subscription period.
        Returns 0 if no subscription exists or the subscription is expired.
        """
        subscription = getattr(self, "subscription", None)

        if not subscription:
            return 0

        subscription.expire_if_needed()
        return subscription.days_remaining

    @property
    def subscription_status(self):
        """
        Useful for templates, serializers, and admin display.
        """
        subscription = getattr(self, "subscription", None)

        if not subscription:
            return "no_subscription"

        subscription.expire_if_needed()
        return subscription.status

    @property
    def subscription_period_end(self):
        """
        Returns the current access expiry date.
        """
        subscription = getattr(self, "subscription", None)

        if not subscription:
            return None

        subscription.expire_if_needed()
        return subscription.current_period_end

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

            if not base_slug:
                base_slug = "restaurant"

            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        super().save(*args, **kwargs)

    def __str__(self):
        company_name = self.company.name if self.company_id else "No Company"
        return f"{self.name} ({company_name})"

    class Meta:
        unique_together = ("company", "name")
        

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
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "table_number"],
                name="unique_table_number_per_restaurant"
            )
        ]
        
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
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="inventory"
    )

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, null=True)

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    unit = models.CharField(max_length=20, default="pcs")

    # ✅ This is your low stock threshold
    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # ✅ Cached low stock flag (for fast dashboards)
    low_stock_threshold = models.IntegerField(default=0)  # Example definition

    is_low_stock = models.BooleanField(default=False)
    
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("restaurant", "name")
        indexes = [
            models.Index(fields=["restaurant", "is_low_stock"]),
            models.Index(fields=["restaurant", "active"]),
        ]

    # -------------------------------------------------
    # LOW STOCK LOGIC
    # -------------------------------------------------

    def check_low_stock(self):
        """
        Returns True if item is below reorder level.
        """
        return self.quantity <= self.reorder_level

    def refresh_low_stock_flag(self):
        """
        Sync cached low stock flag.
        """
        low = self.check_low_stock()
        if self.is_low_stock != low:
            self.is_low_stock = low
            super().save(update_fields=["is_low_stock"])

    # -------------------------------------------------
    # SAFE DEDUCTION
    # -------------------------------------------------

    def deduct(self, amount):
        """
        Deduct stock safely.
        Must be used inside transaction + select_for_update.
        """

        if amount <= 0:
            return

        if self.quantity < amount:
            raise ValidationError(
                f"Not enough {self.name} in stock."
            )

        self.quantity -= amount
        super().save(update_fields=["quantity"])

        # ✅ Automatically check for low stock
        self.refresh_low_stock_flag()

    # -------------------------------------------------
    # SAFE RESTOCK
    # -------------------------------------------------

    def restock(self, amount):
        """
        Add stock safely.
        """

        if amount <= 0:
            return

        self.quantity += amount
        super().save(update_fields=["quantity"])

        self.refresh_low_stock_flag()

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

class MenuItemIngredient(models.Model):
    # Changed 'MenuItem' to 'Menu'
    menu_item = models.ForeignKey(
        'Menu', 
        related_name='ingredients', 
        on_delete=models.CASCADE
    )
    inventory_item = models.ForeignKey(
        'InventoryItem', 
        related_name='used_in_items',
        on_delete=models.CASCADE
    )
    quantity_needed = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        help_text="How much of this inventory item is used for 1 serving of this Menu item"
    )

    def __str__(self):
        return f"{self.menu_item.name} recipe: {self.quantity_needed} of {self.inventory_item.name}"
    
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

    # ✅ Prevent double inventory deduction
    inventory_deducted = models.BooleanField(default=False)

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
    # CALCULATIONS
    # =============================================================================
    
    
    def short_id(self):
        return f"ORD-{str(self.id)[:6].upper()}"
    
    def calculate_totals(self):
        """
        Recalculate order subtotal and total safely.
        """

        subtotal = Decimal("0.00")

        for item in self.items.all():
            item_total = Decimal(str(item.final_price or 0)) * item.quantity
            subtotal += item_total
        
        # ✅ Ensure all monetary fields are Decimal
        tax = self.tax or Decimal("0.00")
        service_charge = self.service_charge or Decimal("0.00")
        tip = self.tip or Decimal("0.00")
        discount = self.discount or Decimal("0.00")

        total = subtotal + tax + service_charge + tip - discount

        # ✅ Round properly to 2 decimal places
        total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        self.subtotal = subtotal
        self.total = total

        super().save(update_fields=["subtotal", "total"])

    # =============================================================================
    # INVENTORY DEDUCTION
    # =============================================================================

    def deduct_inventory(self):
        """
        Deduct inventory based on recipe items.
        Must be called inside an atomic block.
        """

        from core.models import RecipeItem, InventoryItem

        if self.inventory_deducted:
            return

        for item in self.items.select_related("product"):

            recipe_items = RecipeItem.objects.select_related(
                "ingredient"
            ).filter(product=item.product)

            for recipe in recipe_items:

                total_quantity_used = recipe.quantity_used * item.quantity

                # ✅ LOCK THE INVENTORY ROW
                ingredient = (
                    InventoryItem.objects
                    .select_for_update()
                    .get(pk=recipe.ingredient.pk)
                )

                if ingredient.quantity < total_quantity_used:
                    raise ValidationError(
                        f"Not enough {ingredient.name} in stock."
                    )

                ingredient.quantity -= total_quantity_used
                ingredient.save(update_fields=["quantity"])

                # ✅ Auto refresh low stock flag (if implemented)
                if hasattr(ingredient, "refresh_low_stock_flag"):
                    ingredient.refresh_low_stock_flag()

        self.inventory_deducted = True
        super().save(update_fields=["inventory_deducted"])
    
    def transition_to(self, new_status, actor=None):
        """
        Centralized status transition logic.
        """

        allowed_transitions = {
            self.Status.DRAFT: [self.Status.PLACED, self.Status.CANCELED],
            self.Status.PLACED: [self.Status.IN_PROGRESS, self.Status.CANCELED],
            self.Status.IN_PROGRESS: [self.Status.READY, self.Status.CANCELED],
            self.Status.READY: [self.Status.SERVED, self.Status.CANCELED],
            self.Status.SERVED: [self.Status.COMPLETED],
            self.Status.COMPLETED: [],
            self.Status.CANCELED: [],
        }

        if new_status not in allowed_transitions.get(self.status, []):
            raise ValidationError(
                f"Invalid transition from {self.status} to {new_status}"
            )

        self.status = new_status
        self.save(update_fields=["status"])
    
    # =============================================================================
    # COMPLETION LOGIC
    # =============================================================================

    def complete_order(self, actor=None):
        """
        Mark order as completed.
        - Requires payment to be PAID
        - Deducts inventory
        - Locks order row
        - Closes session
        """

        if self.payment_status != self.PaymentStatus.PAID:
            raise PermissionDenied("Order must be paid before completion.")

        with transaction.atomic():

            order = Order.objects.select_for_update().get(pk=self.pk)

            # ✅ Prevent duplicate completion
            if order.status == self.Status.COMPLETED:
                return order

            # ✅ Deduct inventory safely
            order.deduct_inventory()

            # ✅ Mark completed
            order.status = self.Status.COMPLETED
            order.save(update_fields=["status"])

            # ✅ Close session safely
            if order.session and order.session.is_active:
                order.session.is_active = False
                order.session.closed_at = timezone.now()
                order.session.save(update_fields=["is_active", "closed_at"])

            return order
    def mark_as_paid(self, actor=None):
        if self.payment_status == self.PaymentStatus.PAID:
            return self

        self.payment_status = self.PaymentStatus.PAID
        self.save(update_fields=["payment_status"])

        return self
    
    def restore_inventory(self):

        for item in self.items.all():
            for ingredient in item.product.ingredients.all():
                ingredient.stock += ingredient.quantity_required * item.quantity
                ingredient.save(update_fields=["stock"])
                
    def mark_as_refunded(self, actor=None):

        if self.payment_status == self.PaymentStatus.REFUNDED:
            return self

        self.payment_status = self.PaymentStatus.REFUNDED
        self.status = self.Status.CANCELED
        self.save(update_fields=["payment_status", "status"])

        return self
    
    
    # =============================================================================
    # SAVE OVERRIDE
    # =============================================================================

    def save(self, *args, **kwargs):

        creating = self._state.adding

        previous_status = None
        if not creating and self.pk:
            previous_status = (
                Order.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        # ✅ Auto-generate order number
        if creating and not self.order_number:
            last_number = (
                Order.objects.filter(restaurant=self.restaurant)
                .aggregate(models.Max("order_number"))["order_number__max"]
            )
            self.order_number = (last_number or 0) + 1

        super().save(*args, **kwargs)

        # ✅ Kitchen ticket auto-create
        if (
            self.status == self.Status.IN_PROGRESS
            and previous_status != self.Status.IN_PROGRESS
        ):
            KitchenTicket.objects.get_or_create(order=self)

        # ✅ Auto-close session
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

    def __str__(self):
        return f"Order #{self.order_number} - {self.restaurant.name}"
    
# Add this to your existing models.py

class ProductIngredient(models.Model):
    """
    Links a Product to an InventoryItem (The Recipe).
    """
    product = models.ForeignKey(
        'Product', 
        on_delete=models.CASCADE, 
        related_name='product_recipe'
    )
    inventory_item = models.ForeignKey(
        'InventoryItem', 
        on_delete=models.CASCADE,
        related_name='used_in_products'
    )
    quantity_required = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        help_text="Amount of inventory item used for 1 unit of this product"
    )

    class Meta:
        unique_together = ('product', 'inventory_item')

    def __str__(self):
        return f"{self.product.name} needs {self.quantity_required} of {self.inventory_item.name}"
    
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
        "core.ProductVariant",
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

    # ✅ This is now a true snapshot field
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # -------------------------------------------------
    # CALCULATED SUBTOTAL (READ-ONLY PROPERTY)
    # -------------------------------------------------

    @property
    def subtotal(self):
        """
        This is only for display.
        It recalculates dynamically and should NOT be used
        for accounting logic.
        """
        base_price = (
            self.variant.price if self.variant else self.product.base_price
        )

        modifiers_total = sum(
            mod.price_adjustment for mod in self.modifiers.all()
        )

        return (base_price + modifiers_total) * self.quantity

    # -------------------------------------------------
    # SAFE PRICE RECALCULATION (CALL AFTER M2M SET)
    # -------------------------------------------------



    def recalculate_price(self):
        if not self.product:
            return

        base_price = (
            self.variant.price
            if getattr(self, "variant", None)
            else self.product.base_price
        ) or Decimal("0.00")

        modifiers_total = sum(
            (mod.price_adjustment or Decimal("0.00"))
            for mod in self.modifiers.all()
        )

        # ✅ Change: final_price is now the price for ONE unit
        self.final_price = (base_price + modifiers_total)
    
        super().save(update_fields=["final_price"])

    # -------------------------------------------------
    # SAVE OVERRIDE (NO PRICE CALCULATION HERE)
    # -------------------------------------------------

    def save(self, *args, **kwargs):

        with transaction.atomic():

            order = (
                type(self.order).objects
                .select_for_update()
                .get(pk=self.order.pk)
            )

            if order.payment_status == order.PaymentStatus.PAID:
                raise PermissionDenied(
                    "Cannot modify items on a paid order."
                )

            if order.status in [
                order.Status.COMPLETED,
                order.Status.CANCELED
            ]:
                raise PermissionDenied(
                    "Cannot modify items on a closed order."
                )

            if self.product.category.menu.restaurant_id != self.order.restaurant_id:
                raise ValidationError(
                    "Product does not belong to the same restaurant as the order."
                )

            super().save(*args, **kwargs)

            # ✅ DO NOT calculate price here anymore
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
                raise PermissionDenied(
                    "Cannot delete items from a paid order."
                )

            if order.status in [
                order.Status.COMPLETED,
                order.Status.CANCELED
            ]:
                raise PermissionDenied(
                    "Cannot delete items from a closed order."
                )

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

    def start_preparation(self, actor=None):
        if self.status != self.Status.QUEUED:
            raise ValueError("Ticket is not in queued state")

        if not actor:
            raise PermissionDenied("Actor is required to start preparation.")

        self.status = self.Status.PREPARING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

        # ✅ Transition order as well
        self.order.transition_to(Order.Status.IN_PROGRESS, actor=actor)
        
        
    def mark_completed(self, actor=None):
        if not actor:
            raise PermissionDenied("Actor is required.")

        if self.status != self.Status.PREPARING:
            raise ValueError("Ticket must be in PREPARING state.")

        # ✅ Permission check (optional extra layer)
        if not actor.is_cook and not actor.is_manager:
            raise PermissionDenied("Only kitchen staff can complete tickets.")

        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

        # ✅ This enforces order permissions + history logging
        self.order.transition_to(
        self.order.Status.READY,
        actor=actor
        )
    
    
    
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
    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="loyalty_tiers"
    )

    name = models.CharField(max_length=50)
    min_points = models.PositiveIntegerField()
    reward_description = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("restaurant", "name")
        ordering = ["-min_points"]

    def __str__(self):
        return f"{self.name} ({self.min_points} pts)"
    

def assign_tier(customer):
    tiers = LoyaltyTier.objects.filter(
        restaurant=customer.restaurant
    ).order_by("-min_points")

    for tier in tiers:
        if customer.loyalty_points >= tier.min_points:
            if customer.current_tier != tier:
                customer.current_tier = tier
                customer.save(update_fields=["current_tier"])
            return

    # No tier matched
    if customer.current_tier:
        customer.current_tier = None
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
    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="payment_methods"
    )

    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)
    active = models.BooleanField(default=True)
    requires_reference = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ("restaurant", "name")

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
    
    
    
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

    method = models.ForeignKey(
        "core.PaymentMethod",
        on_delete=models.PROTECT,
        related_name="payments"
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
        help_text="Amount paid for this transaction."
    )
    
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Processing fee percentage"
    )

    requires_reference = models.BooleanField(default=False)

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
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["stripe_payment_intent"],
                name="unique_stripe_intent",
                condition=models.Q(stripe_payment_intent__isnull=False)
            )
        ]
        
        
    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["status"]),
            models.Index(fields=["stripe_payment_intent"]),
        ]
    
    
class PaymentIntentLog(models.Model):
    intent_id = models.CharField(max_length=200, unique=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.intent_id
    
    
class DailyReport(models.Model):
    restaurant = models.ForeignKey("core.Restaurant", on_delete=models.CASCADE)
    date = models.DateField()
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ("restaurant", "date")

    def __str__(self):
        return f"{self.restaurant.name} - {self.date}"


from django.core.validators import MinValueValidator, MaxValueValidator


class Settings(models.Model):

    restaurant = models.OneToOneField(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # General
    restaurant_display_name = models.CharField(max_length=150)
    currency_symbol = models.CharField(max_length=5, default="$")
    timezone = models.CharField(max_length=50, default="UTC")
    restaurant_display_name = models.CharField(max_length=150)
    business_email = models.EmailField(blank=True, null=True)
    business_phone = models.CharField(max_length=30, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)

    # Tax & Charges
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    service_charge_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    prices_include_tax = models.BooleanField(default=False)

    # Order Behavior
    auto_mark_order_paid = models.BooleanField(default=False)
    allow_split_payments = models.BooleanField(default=True)
    allow_table_merge = models.BooleanField(default=True)

    # Receipt
    show_logo_on_receipt = models.BooleanField(default=True)
    receipt_header_text = models.CharField(max_length=255, blank=True, null=True)
    receipt_footer_text = models.CharField(max_length=255, blank=True, null=True)
    
    # Inventory
    stock_alerts_enabled = models.BooleanField(default=True)
    auto_deduct_inventory = models.BooleanField(default=True)

    # Notifications
    email_notifications_enabled = models.BooleanField(default=True)
    send_daily_sales_report = models.BooleanField(default=False)
    low_stock_email_alerts = models.BooleanField(default=True)
    notify_on_new_order = models.BooleanField(default=True)

    # UI
    THEME_CHOICES = [
        ("system", "System Preference"),
        ("light", "Light Mode"),
        ("dark", "Dark Mode"),
    ]

    default_theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default="system",
    )
    
    ORDER_TYPE_CHOICES = [
        ("DINE_IN", "Dine In"),
        ("TAKEAWAY", "Takeaway"),
        ("DELIVERY", "Delivery"),
    ]

    default_order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default="DINE_IN",
    )

    require_table_for_dine_in = models.BooleanField(default=True)
    auto_print_kitchen_tickets = models.BooleanField(default=True)
    
    items_per_page = models.PositiveIntegerField(default=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_tax(self, subtotal):
        if self.prices_include_tax:
            return Decimal("0.00")
        return (subtotal * self.tax_percentage) / Decimal("100")

    def calculate_service_charge(self, subtotal):
        return (subtotal * self.service_charge_percentage) / Decimal("100")

    def __str__(self):
        return f"{self.restaurant.name} Settings"

    class Meta:
        indexes = [
            models.Index(fields=["restaurant"]),
        ]
    
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
    

class Plan(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Internal plan code, e.g. starter, pro, enterprise.",
    )

    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    max_users = models.PositiveIntegerField(
        default=5,
    )

    max_tables = models.PositiveIntegerField(
        default=20,
    )

    allow_inventory = models.BooleanField(
        default=True,
    )

    allow_analytics = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["monthly_price"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class SubscriptionStatus(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        SUSPENDED = "suspended", "Suspended"
        CANCELED = "canceled", "Canceled"

    class OfflinePaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CHEQUE = "cheque", "Cheque"
        OTHER = "other", "Other Offline Agreement"

    restaurant = models.OneToOneField(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan = models.ForeignKey(
        "core.Plan",
        on_delete=models.PROTECT,
        related_name="subscriptions",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIALING,
    )

    trial_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    trial_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_period_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    offline_payment_method = models.CharField(
        max_length=30,
        choices=OfflinePaymentMethod.choices,
        null=True,
        blank=True,
    )

    offline_payment_reference = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    offline_payment_notes = models.TextField(
        blank=True,
        default="",
    )

    last_reactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reactivated_subscriptions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    TRIAL_DAYS = 14

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["current_period_end"]),
        ]

    def save(self, *args, **kwargs):
        current_time = timezone.now()

        if not self.trial_start:
            self.trial_start = current_time

        if not self.trial_end:
            self.trial_end = (
                self.trial_start
                + timedelta(days=self.TRIAL_DAYS)
            )

        if not self.current_period_start:
            self.current_period_start = self.trial_start

        if not self.current_period_end:
            self.current_period_end = self.trial_end

        super().save(*args, **kwargs)

    def is_active(self):
        if self.status not in {
            self.SubscriptionStatus.TRIALING,
            self.SubscriptionStatus.ACTIVE,
        }:
            return False

        if (
            self.current_period_end
            and self.current_period_end <= timezone.now()
        ):
            return False

        return True

    def is_trial(self):
        return self.status == self.SubscriptionStatus.TRIALING

    def is_expired(self):
        return self.status == self.SubscriptionStatus.EXPIRED

    @property
    def days_remaining(self):
        if not self.is_active():
            return 0

        if not self.current_period_end:
            return 0

        remaining = self.current_period_end - timezone.now()
        return max(remaining.days, 0)

    def expire_if_needed(self):
        if self.status not in {
            self.SubscriptionStatus.TRIALING,
            self.SubscriptionStatus.ACTIVE,
        }:
            return False

        if (
            self.current_period_end
            and self.current_period_end <= timezone.now()
        ):
            self.status = self.SubscriptionStatus.EXPIRED
            self.save(update_fields=["status", "updated_at"])
            return True

        return False

    def reactivate_offline(
        self,
        user=None,
        days=30,
        payment_method=OfflinePaymentMethod.CASH,
        reference="",
        notes="",
    ):
        current_time = timezone.now()

        self.status = self.SubscriptionStatus.ACTIVE
        self.current_period_start = current_time
        self.current_period_end = (
            current_time + timedelta(days=days)
        )
        self.offline_payment_method = payment_method
        self.offline_payment_reference = reference
        self.offline_payment_notes = notes
        self.last_reactivated_at = current_time
        self.reactivated_by = user

        self.save(
            update_fields=[
                "status",
                "current_period_start",
                "current_period_end",
                "offline_payment_method",
                "offline_payment_reference",
                "offline_payment_notes",
                "last_reactivated_at",
                "reactivated_by",
                "updated_at",
            ]
        )

    def suspend(self):
        self.status = self.SubscriptionStatus.SUSPENDED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self):
        self.status = self.SubscriptionStatus.CANCELED
        self.save(update_fields=["status", "updated_at"])

    def can_use_inventory(self):
        return bool(
            self.plan
            and self.is_active()
            and self.plan.allow_inventory
        )

    def can_use_analytics(self):
        return bool(
            self.plan
            and self.is_active()
            and self.plan.allow_analytics
        )

    def __str__(self):
        plan_name = self.plan.name if self.plan else "No Plan"
        return f"{self.restaurant.name} - {plan_name}"
        
class Printer(TimeStampedModel):

    class PrinterRole(models.TextChoices):
        KITCHEN = "KITCHEN", "Kitchen Printer"
        CASHIER = "CASHIER", "Cashier/POS Printer"

    class ConnectionType(models.TextChoices):
        NETWORK = "NETWORK", "Network/IP"
        USB = "USB", "USB"
        SYSTEM = "SYSTEM", "System Printer"

    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="printers",
  
    )

    name = models.CharField(max_length=100)

    role = models.CharField(
        max_length=20,
        choices=PrinterRole.choices,
    )

    connection_type = models.CharField(
        max_length=20,
        choices=ConnectionType.choices,
        default=ConnectionType.NETWORK,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Required for network/IP printers.",
    )

    port = models.PositiveIntegerField(
        default=9100,
        help_text="Default ESC/POS network printer port is usually 9100.",
    )

    usb_vendor_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional USB vendor ID.",
    )

    usb_product_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional USB product ID.",
    )

    system_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Operating system printer name, if using system printing.",
    )

    is_active = models.BooleanField(default=True)

    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        restaurant_name = self.restaurant.name if self.restaurant else "No restaurant"
        return f"{self.name} - {self.get_role_display()} - {restaurant_name}"
    
    class Meta:
        ordering = ["restaurant", "role", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "name"],
                name="unique_printer_name_per_restaurant",
            ),
            models.UniqueConstraint(
                fields=["restaurant", "role"],
                name="unique_printer_role_per_restaurant",
            ),
        ]
        
        
class PrintJob(TimeStampedModel):

    class PrintJobType(models.TextChoices):
        KITCHEN_ORDER = "KITCHEN_ORDER", "Kitchen Order"
        RECEIPT = "RECEIPT", "Receipt"

    class PrintJobStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PRINTED = "PRINTED", "Printed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="print_jobs",
    )

    printer = models.ForeignKey(
        "core.Printer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_jobs",
    )

    job_type = models.CharField(
        max_length=30,
        choices=PrintJobType.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=PrintJobStatus.choices,
        default=PrintJobStatus.PENDING,
    )

    title = models.CharField(max_length=150, blank=True)

    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured print data such as order items, totals, table, and waiter.",
    )

    raw_text = models.TextField(
        blank=True,
        help_text="Formatted text to send directly to printer.",
    )

    copies = models.PositiveIntegerField(default=1)

    attempts = models.PositiveIntegerField(default=0)

    max_attempts = models.PositiveIntegerField(default=3)

    error_message = models.TextField(blank=True)

    printed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def get_target_printer_role(self):
        if self.job_type == self.PrintJobType.KITCHEN_ORDER:
            return Printer.PrinterRole.KITCHEN

        if self.job_type == self.PrintJobType.RECEIPT:
            return Printer.PrinterRole.CASHIER

        return None

    def save(self, *args, **kwargs):
        if not self.printer_id and self.restaurant_id:
            target_role = self.get_target_printer_role()

            if target_role:
                printer = Printer.objects.filter(
                    restaurant_id=self.restaurant_id,
                    role=target_role,
                    is_active=True,
                ).first()

                if printer:
                    self.printer = printer

        super().save(*args, **kwargs)

    def mark_processing(self):
        self.status = self.PrintJobStatus.PROCESSING
        self.attempts += 1
        self.save(update_fields=["status", "attempts", "updated_at"])

    def mark_printed(self):
        from django.utils import timezone

        self.status = self.PrintJobStatus.PRINTED
        self.printed_at = timezone.now()
        self.error_message = ""
        self.save(update_fields=["status", "printed_at", "error_message", "updated_at"])

    def mark_failed(self, error_message=""):
        self.status = self.PrintJobStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])

    def can_retry(self):
        return (
            self.status == self.PrintJobStatus.FAILED
            and self.attempts < self.max_attempts
        )

    def __str__(self):
        restaurant_name = self.restaurant.name if self.restaurant else "No restaurant"
        return f"{self.get_job_type_display()} - {self.status} - {restaurant_name}"
    
    class Meta:
        ordering = ["-created_at"]
        
# ===================================================================
# DISCOUNT MODEL
# ===================================================================
class Discount(models.Model):
    """
    Promo codes and discounts — percentage or fixed amount.
    Supports validity windows, usage limits, and minimum order amounts.
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    restaurant = models.ForeignKey(
        "core.Restaurant",
        on_delete=models.CASCADE,
        related_name="discounts",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage (e.g. 20 for 20%) or fixed amount (e.g. 5.00).",
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Cap for percentage discounts. 0 = no cap.",
    )
    usage_limit = models.PositiveIntegerField(
        default=0,
        help_text="Max times this code can be used. 0 = unlimited.",
    )
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def is_expired(self):
        if not self.valid_to:
            return False
        from datetime import date
        return date.today() > self.valid_to

    @property
    def is_valid(self):
        from datetime import date
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.usage_limit > 0 and self.times_used >= self.usage_limit:
            return False
        if self.valid_from and date.today() < self.valid_from:
            return False
        return True




class WebhookConfiguration(models.Model):
    restaurant = models.OneToOneField('Restaurant', on_delete=models.CASCADE, related_name='webhook_config')
    
    # API Keys (For Inbound requests)
    live_api_key = models.CharField(max_length=100, unique=True, blank=True)
    test_api_key = models.CharField(max_length=100, unique=True, blank=True)
    
    # Webhook Secrets (For Outbound signing)
    live_secret = models.CharField(max_length=100, blank=True)
    test_secret = models.CharField(max_length=100, blank=True)

    # URLs
    live_webhook_url = models.URLField(blank=True, null=True)
    test_webhook_url = models.URLField(blank=True, null=True)
    
    is_live_enabled = models.BooleanField(default=False)
    is_test_enabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Auto-generate keys if they don't exist
        if not self.live_api_key:
            self.live_api_key = f"beepos_live_{secrets.token_urlsafe(32)}"
        if not self.test_api_key:
            self.test_api_key = f"beepos_test_{secrets.token_urlsafe(32)}"
        if not self.live_secret:
            self.live_secret = secrets.token_hex(24)
        if not self.test_secret:
            self.test_secret = secrets.token_hex(24)
        super().save(*args, **kwargs)

class WebhookEvent(models.Model):
    """
    A log of every webhook event triggered. 
    Useful for debugging and retrying failed deliveries.
    """
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE)
    event_id = models.CharField(max_length=50, unique=True) # e.g. evt_...
    event_type = models.CharField(max_length=100) # e.g. order.placed
    payload = models.JSONField()
    environment = models.CharField(max_length=10, choices=[('TEST', 'Test'), ('LIVE', 'Live')])
    
    status = models.CharField(max_length=20, default='PENDING') # PENDING, SENT, FAILED
    response_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.restaurant.name} ({self.status})"
    
    

class Session(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE)
    opened_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    start_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    end_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Session {self.id} - {self.restaurant.name} ({self.status})"

