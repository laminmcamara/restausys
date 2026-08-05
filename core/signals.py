from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Order,
    OrderItem,
    KitchenTicket,
)
from .serializers import OrderSerializer, KitchenTicketSerializer


# =====================================================
# ✅ ORDER BROADCASTING (React / DRF Aligned)
# =====================================================

@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, update_fields=None, **kwargs):

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # ✅ Only trigger on creation or status change
    if not created and update_fields is not None:
        if "status" not in update_fields:
            return

    # ✅ Reload order with relations for full serialization
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

    order_data = OrderSerializer(order_obj).data

    # ✅ Universal message format
    message = {
        "type": "order_status_update",  # transport layer
        "data": {
            "event": "ORDER_STATUS_UPDATED",
            "order": order_data,
        },
    }

    restaurant_id = instance.restaurant_id

    # ✅ Broadcast to all relevant groups
    groups = [
        f"restaurant_{restaurant_id}",
        f"pos_{restaurant_id}",
        f"kitchen_{restaurant_id}",
        f"display_{restaurant_id}",
    ]

    if instance.table_id:
        groups.append(f"table_{instance.table_id}")

    for group in groups:
        async_to_sync(channel_layer.group_send)(group, message)

    # =====================================================
    # ✅ KITCHEN TICKET FLOW (JSON ONLY — No Templates)
    # =====================================================

    kitchen_group = f"kitchen_{restaurant_id}"

    # ✅ Order enters kitchen flow
    if instance.status in [
        Order.Status.PLACED,
        Order.Status.IN_PROGRESS,
    ]:

        ticket, _ = KitchenTicket.objects.get_or_create(order=instance)

        ticket_data = KitchenTicketSerializer(ticket).data

        async_to_sync(channel_layer.group_send)(
            kitchen_group,
            {
                "type": "order_status_update",
                "data": {
                    "event": "KITCHEN_TICKET_UPDATED",
                    "ticket": ticket_data,
                },
            },
        )

    # ✅ Order completed or cancelled
    elif instance.status in [
        Order.Status.COMPLETED,
        Order.Status.CANCELED,
    ]:
        try:
            ticket = instance.kitchen_ticket

            async_to_sync(channel_layer.group_send)(
                kitchen_group,
                {
                    "type": "order_status_update",
                    "data": {
                        "event": "KITCHEN_TICKET_REMOVED",
                        "ticket_id": ticket.id,
                    },
                },
            )

            ticket.delete()

        except KitchenTicket.DoesNotExist:
            pass


# =====================================================
# ✅ ORDER ITEM CHANGES → UPDATE KITCHEN (JSON ONLY)
# =====================================================

@receiver([post_save, post_delete], sender=OrderItem)
def update_kitchen_ticket_on_item_change(sender, instance, **kwargs):

    order = instance.order

    # ✅ Only update active kitchen orders
    if order.status not in [
        Order.Status.PLACED,
        Order.Status.IN_PROGRESS,
    ]:
        return

    try:
        ticket = order.kitchen_ticket
    except KitchenTicket.DoesNotExist:
        return

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    kitchen_group = f"kitchen_{order.restaurant_id}"

    ticket_data = KitchenTicketSerializer(ticket).data

    async_to_sync(channel_layer.group_send)(
        kitchen_group,
        {
            "type": "order_status_update",
            "data": {
                "event": "KITCHEN_TICKET_UPDATED",
                "ticket": ticket_data,
            },
        },
    )