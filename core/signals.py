from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import pdb
import threading

from .models import (
    Order,
    OrderItem,
    KitchenTicket,
    ProductIngredient,
    Restaurant, 
    PaymentMethod,
    Table,
    TableSession
)
from .serializers import OrderSerializer, KitchenTicketSerializer

import logging

logger = logging.getLogger(__name__)

# =====================================================
# 1. ORDER BROADCASTING & KITCHEN FLOW
# =====================================================

@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, update_fields=None, **kwargs):
    logger.info(
        f"broadcast_order_update: order_id={instance.id}, created={created}, "
        f"update_fields={update_fields}, status={instance.status!r}, "
        f"restaurant_id={instance.restaurant_id!r}, table_id={instance.table_id!r}"
    )

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.error("Channel layer not found")
            return

        if not created and update_fields is not None:
            if "status" not in update_fields:
                logger.info("Status not updated, skipping")
                return

        order_obj = (
            Order.objects
            .select_related("restaurant", "table", "created_by")
            .prefetch_related("items", "items__product", "items__modifiers")
            .get(pk=instance.pk)
        )

        logger.info("Order object retrieved")

        try:
            order_data = OrderSerializer(order_obj).data
            logger.info("Order data serialized")
        except Exception as e:
            logger.error(f"Serialization error for order {order_obj.id}: {e}")
            raise

        restaurant_id = instance.restaurant_id
        groups = [
            f"restaurant_{restaurant_id}",
            f"pos_{restaurant_id}",
            f"kitchen_{restaurant_id}",
            f"display_{restaurant_id}",
        ]
        if instance.table_id:
            groups.append(f"table_{instance.table_id}")

        logger.info(f"Groups: {groups}")

        # Only trigger on creation or status change to save resources
        if not created and update_fields is not None:
            if "status" not in update_fields:
                logger.info("Status not updated, skipping")
                return

        # Reload order with relations for full serialization
        try:
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
        except Order.DoesNotExist:
            logger.error("Order not found")
            return

        logger.info("Order object retrieved")
        order_data = OrderSerializer(order_obj).data
        logger.info("Order data serialized")
        restaurant_id = instance.restaurant_id

        # Universal message format for WebSockets
        message = {
            "type": "order_status_update",
            "data": {
                "event": "ORDER_STATUS_UPDATED",
                "order": order_data,
            },
        }

        # Broadcast to relevant groups
        groups = [
            f"restaurant_{restaurant_id}",
            f"pos_{restaurant_id}",
            f"kitchen_{restaurant_id}",
            f"display_{restaurant_id}",
        ]
        if instance.table_id:
            groups.append(f"table_{instance.table_id}")

        logger.info("Groups determined")
        for group in groups:
            logger.info(f"Sending message to group {group}")
            try:
                async_to_sync(channel_layer.group_send)(group, message)
                logger.info(f"Message sent to group {group}")
            except Exception as e:
                logger.error(f"Error sending message to group {group}: {str(e)}")

        # --- Kitchen Ticket Lifecycle ---
        kitchen_group = f"kitchen_{restaurant_id}"

        # Order enters kitchen flow
        if instance.status in [Order.Status.PLACED, Order.Status.IN_PROGRESS]:
            logger.info("Order enters kitchen flow")
            try:
                ticket, _ = KitchenTicket.objects.get_or_create(order=instance)
                logger.info(f"Kitchen ticket created for order {instance.id}")
                ticket_data = KitchenTicketSerializer(ticket).data

                logger.info(f"Sending kitchen ticket update to group {kitchen_group}")
                try:
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
                    logger.info(f"Kitchen ticket update sent to group {kitchen_group}")
                except Exception as e:
                    logger.error(f"Error sending kitchen ticket update to group {kitchen_group}: {str(e)}")
            except Exception as e:
                logger.error(f"Error updating kitchen ticket: {str(e)}")

        # Order completed or cancelled - Remove from KDS
        elif instance.status in [Order.Status.COMPLETED, Order.Status.CANCELED]:
            try:
                # Use hasattr to safely check for one-to-one relation
                if hasattr(instance, 'kitchen_ticket'):
                    ticket = instance.kitchen_ticket
                    logger.info(f"Sending kitchen ticket removal to group {kitchen_group}")
                    try:
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
                        logger.info(f"Kitchen ticket removal sent to group {kitchen_group}")
                    except Exception as e:
                        logger.error(f"Error sending kitchen ticket removal to group {kitchen_group}: {str(e)}")
                    ticket.delete()
                    logger.info(f"Kitchen ticket deleted for order {instance.id}")
            except Exception as e:
                logger.error(f"Error removing kitchen ticket: {str(e)}")

    except Exception as e:
        logger.error(f"Error broadcasting order update: {str(e)}")

# =====================================================
# 2. ORDER ITEM CHANGES → UPDATE KITCHEN
# =====================================================

@receiver([post_save, post_delete], sender=OrderItem)
def update_kitchen_ticket_on_item_change(sender, instance, **kwargs):
    try:
        logger.info(f"update_kitchen_ticket_on_item_change: order_item_id={instance.id}, order_id={instance.order.id}")
        order = instance.order

        # Only update active kitchen orders
        if order.status not in [Order.Status.PLACED, Order.Status.IN_PROGRESS]:
            logger.info(f"Order {order.id} status is not active, skipping")
            return

        if hasattr(order, 'kitchen_ticket'):
            logger.info(f"Kitchen ticket found for order {order.id}")
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.error("Channel layer not found")
                return

            kitchen_group = f"kitchen_{order.restaurant_id}"
            logger.info(f"Sending kitchen ticket update to group {kitchen_group}")
            try:
                ticket_data = KitchenTicketSerializer(order.kitchen_ticket).data
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
                logger.info(f"Kitchen ticket update sent to group {kitchen_group}")
            except Exception as e:
                logger.error(f"Error sending kitchen ticket update to group {kitchen_group}: {str(e)}")

    except Exception as e:
        logger.error(f"Error updating kitchen ticket: {str(e)}")

@receiver(post_save, sender=Order)
def update_kitchen_display(sender, instance, **kwargs):
    # Send a signal to the KitchenDisplayConsumer to update the kitchen display
    channel_layer = get_channel_layer()
    kitchen_group = f"kitchen_{instance.restaurant_id}"
    message = {
        "type": "order_status_update",
        "data": {
            "event": "ORDER_STATUS_UPDATED",
            "order": OrderSerializer(instance).data,
        },
    }
    async_to_sync(channel_layer.group_send)(kitchen_group, message)

# =====================================================
# 3. ATOMIC INVENTORY DEDUCTION
# =====================================================

@receiver(post_save, sender=Order)
def auto_deduct_inventory(sender, instance, created, **kwargs):
    try:
        # Trigger deduction when order is sent to kitchen (PLACED)
        # or when PAID, depending on your business logic.
        target_statuses = [Order.Status.PLACED, 'paid', 'PAID']
        
        if instance.status in target_statuses and not getattr(instance, 'inventory_deducted', False):
            with transaction.atomic():
                # Iterate through all items in the order
                if hasattr(instance, 'items'):
                    for order_item in instance.items.all():
                        # Get ingredients mapped to the product (Recipe)
                        recipe = ProductIngredient.objects.filter(product=order_item.product)
        
                        for ingredient in recipe:
                            inv_item = ingredient.inventory_item
                            # Total = (Qty needed for 1) * (Qty ordered)
                            total_deduction = ingredient.quantity_required * order_item.quantity
                            
                            inv_item.quantity -= total_deduction
                            inv_item.save(update_fields=['quantity'])
                
                # Mark as deducted using update() to avoid re-triggering post_save
                Order.objects.filter(id=instance.id).update(inventory_deducted=True)
                logger.info(f"Inventory successfully deducted for Order {instance.id}")

    except Exception as e:
        logger.error(f"CRITICAL INVENTORY ERROR for Order {instance.id}: {str(e)}")


# =====================================================
# 4. CREATE DEFAULT PAYMENT METHODS FOR RESTAURANT
# =====================================================

@receiver(post_save, sender=Restaurant)
def create_default_payment_methods(sender, instance, created, **kwargs):
    try:
        if created:
            PaymentMethod.objects.create(restaurant=instance, name="Cash", active=True)
            PaymentMethod.objects.create(restaurant=instance, name="Card", active=True)
            PaymentMethod.objects.create(restaurant=instance, name="Mobile Payment", active=True)

    except Exception as e:
        logger.error(f"Error creating default payment methods for Restaurant {instance.id}: {str(e)}")


# Here's how you can use a signal to update the order instance:


@receiver(post_save, sender=Restaurant)
def create_default_payment_methods(
    sender,
    instance,
    created,
    **kwargs,
):
    if not created:
        return

    default_methods = [
        {
            "name": PaymentMethod.MethodType.CASH,
            "active": True,
            "requires_reference": False,
        },
        {
            "name": PaymentMethod.MethodType.CARD,
            "active": True,
            "requires_reference": False,
        },
        {
            "name": PaymentMethod.MethodType.MOBILE,
            "active": True,
            "requires_reference": True,
        },
    ]

    try:
        for method_data in default_methods:
            PaymentMethod.objects.get_or_create(
                restaurant=instance,
                name=method_data["name"],
                defaults={
                    "active": method_data["active"],
                    "requires_reference": method_data[
                        "requires_reference"
                    ],
                },
            )

    except Exception:
        logger.exception(
            "Error creating default payment methods for restaurant %s",
            instance.id,
        )
        
@receiver(post_save, sender=Table)
def broadcast_table_status(sender, instance, **kwargs):
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()

        # Broadcast the updated table status to all connected clients
        async_to_sync(channel_layer.group_send)(
            f"table_status_{instance.restaurant_id}",
            {
                "type": "table_status_update",
                "data": {
                    "table_id": instance.id,
                    "status": instance.status,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error broadcasting table status: {str(e)}")
        
        
@receiver(post_save, sender=TableSession)
def update_table_status(sender, instance, **kwargs):
    if not instance.is_active:
        instance.table.status = Table.Status.AVAILABLE
        instance.table.save()

