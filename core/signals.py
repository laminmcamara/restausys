from decimal import Decimal

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models import Sum
from django.utils import timezone
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Order,
    OrderItem,
    Attendance,
    Restaurant,
    Menu,
    Category,
    KitchenTicket,
)


# ==============================
# ✅ ORDER BROADCASTING
# ==============================
@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, update_fields=None, **kwargs):

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    from django.template.loader import render_to_string
    from .serializers import OrderSerializer

    # ✅ Only react to creation OR status change
    if not created and update_fields is not None:
        if "status" not in update_fields:
            return

    # ==============================
    # ✅ SEND TO RESTAURANT DASHBOARD
    # ==============================

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

    async_to_sync(channel_layer.group_send)(
        f"restaurant_{instance.restaurant_id}",
        {
            "type": "order_update",
            "data": {
                "type": "order_update",
                "order": order_data,
            },
        },
    )

    # ==============================
    # ✅ KITCHEN DISPLAY LOGIC
    # ==============================

    kitchen_group = f"kitchen_{instance.restaurant_id}"

    # ✅ ORDER ENTERS KITCHEN FLOW
    if instance.status in [
        Order.Status.PLACED,
        Order.Status.IN_PROGRESS,
    ]:

        ticket, ticket_created = KitchenTicket.objects.get_or_create(
            order=instance
        )

        if ticket_created:
            ticket_html = render_to_string(
                "core/partials/kds_ticket.html",
                {"ticket": ticket}
            )

            async_to_sync(channel_layer.group_send)(
                kitchen_group,
                {
                    "type": "kitchen_update",
                    "data": {
                        "type": "update_ticket",
                        "ticket_id": ticket.id,
                        "ticket_html": ticket_html,
                    },
                },
            )

        else:
            async_to_sync(channel_layer.group_send)(
                kitchen_group,
                {
                    "type": "status_update",
                    "data": {
                        "type": "status_update",
                        "ticket_id": ticket.id,
                        "new_status": ticket.status,
                    },
                },
            )

    # ✅ ORDER COMPLETED OR CANCELLED
    elif instance.status in [
        Order.Status.COMPLETED,
        Order.Status.CANCELED,
    ]:
        try:
            ticket = instance.kitchen_ticket

            async_to_sync(channel_layer.group_send)(
                kitchen_group,
                {
                    "type": "kitchen_update",
                    "data": {
                        "type": "remove_ticket",
                        "ticket_id": ticket.id,
                    },
                },
            )

            ticket.delete()

        except KitchenTicket.DoesNotExist:
            pass




    # ==============================
    # ✅ POS SCREENS
    # ==============================

    async_to_sync(channel_layer.group_send)(
        f"pos_{instance.restaurant_id}",
        {
            "type": "order_status_update",
            "data": {
                "type": "order_update",
                "order": order_data,
            },
        },
    )

    # ==============================
    # ✅ TABLE SCREEN
    # ==============================

    if instance.table_id:
        async_to_sync(channel_layer.group_send)(
            f"table_{instance.table_id}",
            {
                "type": "order_update",
                "data": {
                    "type": "order_update",
                    "order": order_data,
                },
            },
        )
        
        
@receiver([post_save, post_delete], sender=OrderItem)
def update_kitchen_ticket_on_item_change(sender, instance, **kwargs):

    order = instance.order

    # Only update active kitchen orders
    if order.status not in [
        order.Status.PLACED,
        order.Status.IN_PROGRESS,
    ]:
        return

    try:
        ticket = order.kitchen_ticket
    except KitchenTicket.DoesNotExist:
        return

    channel_layer = get_channel_layer()
    kitchen_group = f"kitchen_{order.restaurant_id}"

    ticket_html = render_to_string(
        "core/partials/kds_ticket.html",
        {"ticket": ticket}
    )

    async_to_sync(channel_layer.group_send)(
        kitchen_group,
        {
            "type": "kitchen_update",
            "data": {
                "type": "new_ticket",
                "ticket_id": ticket.id,
                "ticket_html": ticket_html,
            },
        },
    )