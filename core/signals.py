from decimal import Decimal

from django.db.models.signals import post_save, m2m_changed
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order, OrderItem, Attendance, Restaurant, Menu, Category

# ==============================
# ✅ ORDER BROADCASTING
# ==============================
@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, update_fields=None, **kwargs):
    """
    Broadcast order updates when:
    - Order created
    - Status changes
    """

    if not created and update_fields is not None:
        if "status" not in update_fields:
            return

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    from .serializers import OrderSerializer

    order_obj = (
        Order.objects
        .select_related("restaurant", "table", "created_by")
        .prefetch_related(
        "items",
        "items__product",
        "items__modifiers",
    )
        .get(pk=instance.pk)
    )

    # ✅ Force queryset evaluation BEFORE serializer
    list(order_obj.items.all())

    order_data = OrderSerializer(order_obj).data

    data = {
        "type": "order_update",
        "order": order_data,
    }

    # ✅ Restaurant Dashboard
    async_to_sync(channel_layer.group_send)(
        f"restaurant_{instance.restaurant_id}",
        {
            "type": "order_update",
            "data": data,
        }
    )

    # ✅ POS Screens
    async_to_sync(channel_layer.group_send)(
        f"pos_{instance.restaurant_id}",
        {
            "type": "order_status_update",
            "data": data,
        }
    )

    # ✅ Kitchen Screens
    async_to_sync(channel_layer.group_send)(
        f"kitchen_{instance.restaurant_id}",
        {
            "type": "order_update",
            "data": data,
        }
    )

    # ✅ TABLE SCREEN (Add This Part Here)
    if instance.table_id:
        async_to_sync(channel_layer.group_send)(
            f"table_{instance.table_id}",
            {
                "type": "order_update",
                "data": data,
            }
        )
        
        
# ==============================
# ✅ ORDER ITEM PRICE RECALCULATION
# ==============================

@receiver(m2m_changed, sender=OrderItem.modifiers.through)
def recalculate_order_item_price(sender, instance, action, **kwargs):
    """
    Recalculate OrderItem.final_price whenever modifiers change.
    """

    if action not in ["post_add", "post_remove", "post_clear"]:
        return

    # Calculate deterministically
    unit_price = instance.product.base_price

    modifier_price_sum = instance.modifiers.aggregate(
        total=Sum("price_adjustment")
    )["total"] or Decimal("0.00")

    unit_price += modifier_price_sum

    final_price = unit_price * Decimal(instance.quantity)

    # Update directly to avoid recursive save()
    OrderItem.objects.filter(pk=instance.pk).update(
        final_price=final_price
    )
    
# ==============================
# ✅ AUTO ATTENDANCE (LOGIN)
# ==============================

@receiver(user_logged_in)
def auto_clock_in(sender, request, user, **kwargs):
    """
    Automatically clock in staff on login if they have an active shift.
    Never crash login.
    """

    # SaaS admin should not clock in
    if user.is_superuser:
        return

    # Must belong to a restaurant
    if not user.restaurant:
        return

    # Try to get an active cashier shift (adjust if your model differs)
    active_shift = user.cashier_shifts.filter(is_active=True).first()

    if not active_shift:
        return  # No active shift → don't create attendance

    Attendance.objects.get_or_create(
        user=user,
        shift=active_shift,
        clock_out__isnull=True,  # prevent duplicate open attendance
        defaults={
            "clock_in": timezone.now(),
        }
    )

# ==============================
# ✅ AUTO ATTENDANCE (LOGOUT)
# ==============================

@receiver(user_logged_out)
def auto_clock_out(sender, request, user, **kwargs):
    channel_layer = get_channel_layer()
    if not user:
        return

    active_attendance = Attendance.objects.filter(
        employee=user,
        check_out__isnull=True
    ).first()

    if active_attendance:
        active_attendance.check_out = timezone.now()
        active_attendance.save()
        

# ✅ PUBLIC PICKUP DISPLAY (LIMITED TO LAST 10)

    preparing = (
        Order.objects.filter(
            restaurant_id=user.restaurant_id,
            status__in=["PLACED", "IN_PROGRESS"]
        )
        .order_by("-created_at")[:10]
        .values_list("id", flat=True)
    )

    ready = (
        Order.objects.filter(
            restaurant_id=user.restaurant_id,
            status="READY"
        )
        .order_by("-created_at")[:10]
        .values_list("id", flat=True)
    )

    async_to_sync(channel_layer.group_send)(
        f"customer_{user.restaurant_id}",
        {
            "type": "order_update",
            "data": {
                "type": "pickup_update",
                "now_preparing": list(preparing),
                "ready": list(ready),
            }
        }
    )
    
# ==============================
# ✅ AUTO CREATE DEFAULT MENU STRUCTURE
# ==============================

@receiver(post_save, sender=Restaurant)
def create_default_menu_structure(sender, instance, created, **kwargs):
    """
    Automatically create default Menu and professional
    Category structure when a new Restaurant is created.
    """

    if not created:
        return

    # Prevent duplicate menu creation
    if Menu.objects.filter(restaurant=instance).exists():
        return

    # ✅ Create default Menu
    menu = Menu.objects.create(
        restaurant=instance,
        name="Main Menu"
    )

    # ✅ Professional default categories
    default_categories = [
        "General",
        "Drinks",
        "Starters",
        "Mains",
        "Desserts",
        "Specials",
    ]

    for index, name in enumerate(default_categories):
        Category.objects.create(
            menu=menu,
            name=name,
            display_order=index,
            is_active=True
        )