# C:\Users\Administrator\restaurant_management\core\models.py

import uuid
from datetime import date, timedelta # Added timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField


# =============================================================================
# USER AND STAFF MODELS
# =============================================================================

class CustomUser(AbstractUser):
    """
    A modern, consolidated custom user model.
    """
    class Roles(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        SERVER = 'SERVER', 'Server'
        COOK = 'COOK', 'Cook'
        CASHIER = 'CASHIER', 'Cashier'
        STAFF = 'STAFF', 'General Staff' # A default role

    email = models.EmailField(unique=True, help_text="Required. Used for login and notifications.")
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STAFF,
        help_text="The primary role of the user in the system."
    )

    @property
    def is_manager(self):
        return self.role == self.Roles.MANAGER

    @property
    def is_kitchen_staff(self):
        return self.role == self.Roles.COOK

    def save(self, *args, **kwargs):
        # ENHANCEMENT: Always sync is_staff status with the role to ensure consistency.
        if self.role == self.Roles.MANAGER:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class Shift(models.Model):
    """Represents a standard work shift template, e.g., 'Morning Shift'."""
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['start_time']
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class Attendance(models.Model):
    """
    Tracks daily staff attendance.
    """
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'
        ON_LEAVE = 'ON_LEAVE', 'On Leave'

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendances')
    # BEST PRACTICE: Use date.today for DateField defaults.
    date = models.DateField(default=date.today)
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    # end_time = models.DateTimeField()  # Ensure this field exists
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABSENT)

    class Meta:
        ordering = ['-date', 'staff']
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        constraints = [
            models.UniqueConstraint(fields=['staff', 'date'], name='unique_attendance_per_day')
        ]

    def __str__(self):
        return f"{self.staff.username} on {self.date} - {self.get_status_display()}"


# =============================================================================
# RESTAURANT AND MENU MODELS
# =============================================================================

class Restaurant(models.Model):
    """
    Represents a single restaurant location.
    """
    name = models.CharField(max_length=100)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"

    def __str__(self):
        return self.name


class Table(models.Model):
    """Represents a single table within a restaurant."""
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        RESERVED = 'RESERVED', 'Reserved'
        CLEANING = 'CLEANING', 'Needs Cleaning'

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    coordinates = models.JSONField(default=dict, blank=True, help_text="Optional JSON for floor plan UI, e.g. {'x': 100, 'y': 50}")

    class Meta:
        ordering = ['restaurant', 'table_number']
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'table_number'], name='unique_table_in_restaurant')
        ]

    def __str__(self):
        return f"Table {self.table_number} at {self.restaurant.name}"


class MenuItem(models.Model):
    """Represents an item on the menu, like 'Cheeseburger'."""
    class Category(models.TextChoices):
        APPETIZER = 'APPETIZER', 'Appetizer'
        MAIN_COURSE = 'MAIN', 'Main Course'
        DESSERT = 'DESSERT', 'Dessert'
        BEVERAGE = 'BEVERAGE', 'Beverage'
        SIDE = 'SIDE', 'Side Dish'

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True, help_text="Is the item currently available to order?")
    # ENHANCEMENT: Added prep_time for more dynamic kitchen ticket calculations.
    prep_time = models.DurationField(
        default=timedelta(minutes=10),
        help_text="Estimated preparation time for this item (e.g., 00:15:00 for 15 mins)."
    )

    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'name'], name='unique_menu_item_per_restaurant')
        ]

    def __str__(self):
        return self.name


class MenuVariant(models.Model):
    """Represents a specific variant of a menu item, e.g., 'Large Coke'."""
    menu_item = models.ForeignKey(MenuItem, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="e.g., 'Small', 'Large', 'Spicy'")
    price_modifier = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Amount to add to the base price.")
    stock = models.PositiveIntegerField(default=0, help_text="Current available stock for this variant.")
    
    class Meta:
        ordering = ['menu_item', 'price_modifier']
        verbose_name = "Menu Variant"
        verbose_name_plural = "Menu Variants"

    def __str__(self):
        return f"{self.menu_item.name} - {self.name}"


# =============================================================================
# ORDERING, KITCHEN, AND PAYMENT MODELS
# =============================================================================

class Order(models.Model):
    """Represents a customer's order for a specific table."""
    class Status(models.TextChoices):
        PLACED = 'PLACED', 'Placed'
        IN_KITCHEN = 'IN_KITCHEN', 'In Kitchen'
        READY = 'READY', 'Ready for Pickup'
        SERVED = 'SERVED', 'Served'
        PAID = 'PAID', 'Paid'
        CANCELED = 'CANCELED', 'Canceled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Allow anonymous/QR code orders
        related_name='orders'
    )
    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.id} for Table {self.table.table_number}"

    @property
    def total_price(self):
        """
        Calculates the total price by summing the total_price of all related OrderItems.
        
        PERFORMANCE WARNING: This performs a separate DB query for each order.
        For fetching the total price for multiple orders in a queryset, it is much more 
        efficient to use `annotate()` in your view/manager.
        """
        if self.pk and self.items.exists():
            return sum(item.total_price for item in self.items.all())
        return 0


class OrderItem(models.Model):
    """Represents a single item within an order, e.g., 2x Cheeseburger."""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    variant = models.ForeignKey(MenuVariant, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    notes = models.CharField(max_length=255, blank=True, help_text="Customer notes, e.g., 'no onions'")
    
    # Add the status field
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    
    class Meta:
        ordering = ['order']
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    @property
    def unit_price(self):
        price = self.menu_item.base_price
        if self.variant:
            price += self.variant.price_modifier
        return price

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    # --- Admin Display Properties ---
    # Note: These are for convenience in the Django Admin. A cleaner pattern is to
    # define display methods directly on the corresponding ModelAdmin class.
    @property
    def status(self):
        """Returns the status of the associated kitchen ticket or the parent order."""
        if hasattr(self, 'ticket'):
            return self.ticket.get_status_display()
        return self.order.get_status_display()
    
    @property
    def variant_name(self):
        """Returns the variant name or a default placeholder."""
        return self.variant.name if self.variant else "Standard"

    @property
    def final_price(self):
        """Alias for total_price for admin display consistency."""
        return self.total_price 
    # --- End Admin Display Properties ---


class KitchenTicket(models.Model):
    """A ticket for the kitchen display system, corresponding to an OrderItem."""
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PREPARING = 'PREPARING', 'Preparing'
        COMPLETED = 'COMPLETED', 'Completed'

    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='ticket')
    station = models.CharField(max_length=100, help_text="e.g., 'Grill', 'Fryer', 'Drinks'")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.IntegerField(default=1, help_text="Lower number means higher priority.")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['priority', 'created_at']
        verbose_name = "Kitchen Ticket"
        verbose_name_plural = "Kitchen Tickets"

    def __str__(self):
        return f"Ticket for {self.order_item}"
    
    @property
    def due_at(self):
        """Calculates when the ticket is due based on the item's estimated prep time."""
        return self.created_at + self.order_item.menu_item.prep_time


class Payment(models.Model):
    """Represents a payment transaction for an order."""
    class Method(models.TextChoices):
        CREDIT_CARD = 'CARD', 'Credit Card'
        CASH = 'CASH', 'Cash'
        MOBILE = 'MOBILE', 'Mobile Payment'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0.01)])
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    gateway_ref = models.CharField(max_length=100, blank=True, help_text="Reference ID from payment gateway.")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment of ${self.amount} for Order {self.order.id} ({self.get_status_display()})"

    # --- Admin Display Properties ---
    @property
    def paid_at(self):
        """Returns the processing time if the payment was completed."""
        return self.processed_at if self.status == self.Status.COMPLETED else None

    @property
    def transaction_id(self):
        """Alias for gateway_ref for admin display consistency."""
        return self.gateway_ref
    # --- End Admin Display Properties ---


class QRToken(models.Model):
    """Generates unique tokens for QR code table ordering."""
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.OneToOneField(Table, on_delete=models.CASCADE, related_name='qr_token')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "QR Token"
        verbose_name_plural = "QR Tokens"

    def __str__(self):
        return f"Token for Table {self.table.table_number}"


# =============================================================================
# INVENTORY AND SALES MODELS
# =============================================================================

class Inventory(models.Model):
    """Tracks current stock levels for raw ingredients or finished goods."""
    restaurant = models.ForeignKey(
        Restaurant, 
        on_delete=models.CASCADE, 
        related_name='inventory_items',
        help_text="The restaurant this inventory item belongs to."
    )
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=20, help_text="e.g., kg, L, units, boxes")
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text="Threshold for low stock alerts.")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'name'], name='unique_inventory_item_per_restaurant')
        ]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

class Restaurant(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class InventoryItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50)
    low_stock_threshold = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SalesData(models.Model):
    """
    Stores aggregate sales data for reporting and analysis.
    This should ideally be populated by a periodic task or a signal.
    """
    restaurant = models.ForeignKey(
        Restaurant, 
        on_delete=models.CASCADE, 
        related_name='sales_records'
    )
    date = models.DateField(default=date.today)
    month = models.CharField(max_length=20, editable=False, help_text="Automatically generated for easy filtering.") 
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = "Sales Data Record"
        verbose_name_plural = "Sales Data Records"
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'date'], name='unique_sales_per_day_per_restaurant')
        ]

    def save(self, *args, **kwargs):
        self.month = self.date.strftime('%B %Y')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sales for {self.date} at {self.restaurant.name}"


class ScreenDisplay(models.Model):
    """
    Represents a physical screen used for KDS or customer views.
    """
    class DisplayType(models.TextChoices):
        KDS = 'KDS', 'Kitchen Display System'
        CUSTOMER = 'CUSTOMER', 'Customer Facing Display'

    restaurant = models.ForeignKey(
        Restaurant, 
        on_delete=models.CASCADE, 
        related_name='displays'
    )
    name = models.CharField(max_length=100, help_text="e.g., 'Kitchen Screen 1', 'Lobby Customer Screen'")
    type = models.CharField(max_length=10, choices=DisplayType.choices, default=DisplayType.CUSTOMER)
    
    class Meta:
        verbose_name = "Screen Display"
        verbose_name_plural = "Screen Displays"

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"