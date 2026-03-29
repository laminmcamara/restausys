from decimal import Decimal

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db.models import Sum

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order, OrderItem


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