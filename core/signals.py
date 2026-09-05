from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Order,
    OrderItem,
    KitchenTicket,
    ProductIngredient,
    Restaurant, PaymentMethod
 
)
from .serializers import OrderSerializer, KitchenTicketSerializer

# =====================================================
# ✅ 1. ORDER BROADCASTING & KITCHEN FLOW
# =====================================================

@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, update_fields=None, **kwargs):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # Only trigger on creation or status change to save resources
    if not created and update_fields is not None:
        if "status" not in update_fields:
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
        return

    order_data = OrderSerializer(order_obj).data
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

    for group in groups:
        async_to_sync(channel_layer.group_send)(group, message)

    # --- Kitchen Ticket Lifecycle ---
    kitchen_group = f"kitchen_{restaurant_id}"

    # Order enters kitchen flow
    if instance.status in [Order.Status.PLACED, Order.Status.IN_PROGRESS]:
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

    # Order completed or cancelled - Remove from KDS
    elif instance.status in [Order.Status.COMPLETED, Order.Status.CANCELED]:
        try:
            # Use hasattr to safely check for one-to-one relation
            if hasattr(instance, 'kitchen_ticket'):
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
        except Exception as e:
            print(f"Error removing kitchen ticket: {e}")


# =====================================================
# ✅ 2. ORDER ITEM CHANGES → UPDATE KITCHEN
# =====================================================

@receiver([post_save, post_delete], sender=OrderItem)
def update_kitchen_ticket_on_item_change(sender, instance, **kwargs):
    order = instance.order

    # Only update active kitchen orders
    if order.status not in [Order.Status.PLACED, Order.Status.IN_PROGRESS]:
        return

    if not hasattr(order, 'kitchen_ticket'):
        return

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    kitchen_group = f"kitchen_{order.restaurant_id}"
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


# =====================================================
# ✅ 3. ATOMIC INVENTORY DEDUCTION
# =====================================================

@receiver(post_save, sender=Order)
def auto_deduct_inventory(sender, instance, created, **kwargs):
    """
    Deducts ingredients from inventory when an order is PLACED.
    Uses the 'inventory_deducted' flag to prevent double-deduction.
    """
    # Trigger deduction when order is sent to kitchen (PLACED)
    # or when PAID, depending on your business logic.
    target_statuses = [Order.Status.PLACED, 'paid', 'PAID']
    
    if instance.status in target_statuses and not getattr(instance, 'inventory_deducted', False):
        try:
            with transaction.atomic():
                # Iterate through all items in the order
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
                print(f"Inventory successfully deducted for Order {instance.id}")
                
        except Exception as e:
            print(f"CRITICAL INVENTORY ERROR for Order {instance.id}: {str(e)}")
            
@receiver(post_save, sender=Restaurant)
def create_default_payment_methods(sender, instance, created, **kwargs):
    if created:
        PaymentMethod.objects.create(restaurant=instance, name="Cash", active=True)
        PaymentMethod.objects.create(restaurant=instance, name="Card", active=True)