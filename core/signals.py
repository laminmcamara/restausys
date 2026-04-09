from decimal import Decimal

from django.db.models.signals import post_save, m2m_changed
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order, OrderItem, Attendance

# ==============================
# ✅ ORDER BROADCASTING
# ==============================

@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, update_fields=None, **kwargs):
    """
    Broadcast order updates to POS dashboard when:
    - Order is created
    - Order status changes
    """

    # Only broadcast on creation or explicit status change
    if not created:
        if not update_fields or "status" not in update_fields:
            return

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # Lazy import to avoid circular dependency
    from .serializers import serialize_order_for_channels

    async_to_sync(channel_layer.group_send)(
        "pos_dashboard",
        {
            "type": "order_update",
            "order": serialize_order_for_channels(instance),
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

    if not user:
        return

    active_attendance = Attendance.objects.filter(
        employee=user,
        check_out__isnull=True
    ).first()

    if active_attendance:
        active_attendance.check_out = timezone.now()
        active_attendance.save()