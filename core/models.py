import uuid
from datetime import date, timedelta
from io import BytesIO
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Sum, F, DecimalField
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.files import File
from django.urls import reverse
from django.utils import timezone

import qrcode

# =============================================================================
# === BASE MANAGERS & UTILITIES ==============================================
# =============================================================================

class OrderManager(models.Manager):
    def annotate_with_total_price(self):
        return self.annotate(
            calculated_total=Sum(
                F('items__quantity') *
                (F('items__menu_item__base_price') + F('items__variant__price_modifier')),
                output_field=DecimalField()
            )
        )


class MenuItemManager(models.Manager):
    """Global halal & availability filters."""
    def available_halal(self):
        return self.filter(is_active=True, available=True, halal=True)


# =============================================================================
# === COMPANY (Multi-brand parent) ============================================
# =============================================================================

class Company(models.Model):
    """Parent company or franchise group."""
    name = models.CharField(max_length=150, unique=True)
    registration_number = models.CharField(max_length=100, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="companies/logos/", null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

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

    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.STAFF)
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    passport_id_card_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.is_superuser:
            self.is_staff = self.role in [
                self.Roles.MANAGER, self.Roles.CASHIER, self.Roles.SUPER_ADMIN
            ]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Shift(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="shifts"
    )
    restaurant = models.ForeignKey("Restaurant", on_delete=models.CASCADE, related_name="shifts")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    role = models.CharField(max_length=50)  # e.g. 'Cook', 'Cashier', etc.

    def __str__(self):
        return f"{self.employee} - {self.role} ({self.start_time:%b %d})"
    
class Attendance(models.Model):
    """Tracks when an employee starts and ends work at a restaurant."""
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    restaurant = models.ForeignKey(
        "Restaurant",
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(blank=True, null=True)
    shift = models.ForeignKey(
        "Shift",
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

class Customer(models.Model):
    """Independent customer database for loyalty/reporting."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile', null=True, blank=True)
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=30, default="en")
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loyalty_points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    def add_points(self, amount: Decimal):
        self.loyalty_points += int(amount // Decimal('10'))
        self.total_spent += amount
        self.save(update_fields=['loyalty_points', 'total_spent'])


# =============================================================================
# === COMPANY RESTAURANTS =======================================================
# =============================================================================

class Restaurant(models.Model):
    class RestaurantStatus(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'
        HOLIDAY = 'HOLIDAY', 'Holiday Hours'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='restaurants')
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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    class Meta:
        unique_together = ('company', 'name')


class Table(models.Model):
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=10)
    capacity = models.PositiveIntegerField(default=2)
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    coordinates = models.JSONField(default=dict, blank=True)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True, editable=False)

    STATUS_CHOICES = [
        ("available", "Available"),
        ("pending", "Pending"),
        ("cooking", "Cooking"),
        ("ready", "Ready"),
        ("served", "Served"),
        ("paid", "Paid"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")

    class Meta:
        unique_together = ('restaurant', 'table_number')
        ordering = ['restaurant', 'table_number']

    def __str__(self):
        return f"{self.restaurant.name} - Table {self.table_number}"

    def get_absolute_url(self):
        return reverse('core:table-detail-view', args=[str(self.access_token)])

    def generate_qr_code(self):
        site = getattr(settings, "SITE_URL", "http://localhost:8000")
        qr_data = f"{site}{self.get_absolute_url()}"
        qr_img = qrcode.make(qr_data)
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        filename = f"table_{self.table_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)
        buffer.close()

    def save(self, *args, **kwargs):
        self.table_number = str(self.table_number).upper().strip()
        created = not self.pk
        super().save(*args, **kwargs)
        if created and not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    # ✅ FIX ADDED HERE
    @property
    def is_occupied(self) -> bool:
        """
        Return True if the table is currently considered occupied.
        You can define 'occupied' however your app treats it.
        """
        return self.status not in ["available", "paid"]
# =============================================================================
# === MENU, CATEGORY & CUISINE ===============================================
# =============================================================================

class Cuisine(models.Model):
    name = models.CharField(max_length=100, unique=True)
    halal_certified = models.BooleanField(default=False)
    region = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    """Represents a dish or product offered by a restaurant, including recipe links."""
    restaurant = models.ForeignKey(
        "Restaurant",
        on_delete=models.CASCADE,
        related_name="menu_items"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="items"
    )
    cuisines = models.ManyToManyField(
        "Cuisine",
        blank=True,
        related_name="menu_items"
    )

    # ✅ Many-to-Many link to Inventory items (ingredients)
    ingredients = models.ManyToManyField(
        "InventoryItem",
        through="RecipeItem",
        related_name="used_in_menu_items",
        blank=True,
        help_text="Ingredients and quantities used to prepare this menu item."
    )

    # ✅ These restore admin compatibility
    available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)  # 👈 add this

    halal = models.BooleanField(default=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ✅ Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["restaurant", "name"]
        unique_together = ("restaurant", "name")

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"
    
class RecipeItem(models.Model):
    """Defines how much of each inventory ingredient a MenuItem uses."""
    menu_item = models.ForeignKey(
        "MenuItem",
        on_delete=models.CASCADE,
        related_name="recipe_items"
    )
    ingredient = models.ForeignKey(
        "InventoryItem",
        on_delete=models.CASCADE,
        related_name="ingredient_recipes"
    )
    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity of this ingredient used per 1 serving of the menu item."
    )
    unit = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        # 🔧 The only valid fields to ensure uniqueness per menu item/ingredient
        unique_together = ("menu_item", "ingredient")
        ordering = ["menu_item"]

    def __str__(self):
        unit = self.unit or self.ingredient.unit
        return f"{self.menu_item.name} uses {self.quantity_used} {unit} of {self.ingredient.name}"

class MenuVariant(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    price_modifier = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.menu_item.name} - {self.name}"
    
class InventoryItem(models.Model):
    """Tracks ingredient/stock items for each restaurant."""
    restaurant = models.ForeignKey(
        "Restaurant", on_delete=models.CASCADE, related_name="inventory"
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="pcs")  # e.g. kg, ltr, box, pcs
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["name"]
        unique_together = ("restaurant", "name")

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def is_below_reorder(self):
        return self.quantity <= self.reorder_level


# =============================================================================
# === MULTI-CURRENCY, ORDERS, PAYMENTS ========================================
# =============================================================================

class MultiCurrencyPrice(models.Model):
    """Dynamic multi-currency storage."""
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='prices')
    currency = models.CharField(max_length=6)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('menu_item', 'currency')

    def __str__(self):
        return f"{self.menu_item.name} - {self.currency} {self.price}"



class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = 'PLACED', 'Placed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        READY = 'READY', 'Ready'
        SERVED = 'SERVED', 'Served'
        PAID = 'PAID', 'Paid'
        CANCELED = 'CANCELED', 'Canceled'
        COMPLETED = 'COMPLETED', 'Completed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey('Restaurant', on_delete=models.PROTECT, related_name='orders')
    customer = models.ForeignKey('Customer', null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    table = models.ForeignKey('Table', null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    tax = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    service_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))

    objects = OrderManager()

    def total_price(self):
        return sum(item.final_price for item in self.items.all()) + self.tax + self.service_charge

    def __str__(self):
        return f"Order {str(self.id)[:8]} ({self.restaurant.name})"

    # ✅ Add these two methods **inside** the class
    def elapsed_time(self):
        """Return how long ago the order was created (timedelta)."""
        return timezone.now() - self.created_at

    def age_status(self):
        """
        Return a color code for the order based on how long it's been open:
        🟢 <30 min → green
        🟡 30–45 min → yellow
        🔴 >1 hour → red
        """
        minutes = self.elapsed_time().total_seconds() / 60

        if minutes < 30:
            return "green"
        elif minutes < 45:
            return "yellow"   # ✅ updated from "orange"
        else:
            return "red"
        

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    variant = models.ForeignKey(MenuVariant, null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="QUEUED")
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))  # ✅ add this

    def save(self, *args, **kwargs):
        # Automatically compute final_price if not provided
        if not self.final_price:
            base_price = self.variant.price_modifier if self.variant else self.menu_item.base_price
            self.final_price = base_price * Decimal(self.quantity)
        super().save(*args, **kwargs)

class KitchenTicket(models.Model):
    """Represents a printable or digital ticket for kitchen staff for each order."""
    order = models.OneToOneField("Order", on_delete=models.CASCADE, related_name="kitchen_ticket")
    created_at = models.DateTimeField(auto_now_add=True)
    printed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Kitchen Ticket #{self.pk} for Order {self.order.id}"

    @property
    def final_price(self):
        modifier = self.variant.price_modifier if self.variant else Decimal('0.00')
        return (self.menu_item.base_price + modifier) * self.quantity


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = 'PAID', 'Paid'
        PENDING = 'PENDING', 'Pending'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50)
    reference = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)


# =============================================================================
# === ANALYTICS SNAPSHOT ======================================================
# =============================================================================

class AnalyticsSnapshot(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='analytics')
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


# =============================================================================
# === DEVICE API TOKENS (Display & Integration Auth) ==========================
# =============================================================================

class APIToken(models.Model):
    device_name = models.CharField(max_length=100)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='api_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_name} ({'Active' if self.active else 'Inactive'})"
    
# =============================================================================
# === STAFF CHAT HISTORY & AUDIT LOG ==========================================
# =============================================================================

class ChatMessage(models.Model):
    """
    Persistent, auditable staff chat log entry.

    Each message is saved with sender reference, timestamp, and message content.
    Useful for compliance, post-shift review, and multi-restaurant coordination.
    """

    id = models.BigAutoField(primary_key=True)
    restaurant = models.ForeignKey(
        "Restaurant",
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

    # Useful metadata for future filtering
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