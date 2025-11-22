import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order, Table
from .serializers import serialize_order_for_channels
# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Auto-assign Table if Missing
# -----------------------------------------------------------------------------
@receiver(pre_save, sender=Order)
def assign_table_if_missing(sender, instance, **kwargs):
    """
    Assign the first available table if none provided.
    """
    if instance.pk or instance.table or not instance.restaurant:
        return  # only assign when creating a new order

    try:
        available_table = (
            Table.objects.filter(restaurant=instance.restaurant, is_occupied=False)
            .order_by("number")
            .first()
        )
        if available_table:
            instance.table = available_table
            available_table.is_occupied = True
            available_table.save(update_fields=["is_occupied"])
            logger.info(
                f"🪑 Assigned Table {available_table.number} to order {instance.id}"
            )
    except Exception as e:
        logger.error(f"Table auto-assign failed: {e}", exc_info=True)

# -----------------------------------------------------------------------------
# Store previous Order status
# -----------------------------------------------------------------------------
@receiver(pre_save, sender=Order)
def store_previous_order_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Order.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except Order.DoesNotExist:
            instance._previous_status = None

# -----------------------------------------------------------------------------
# Notify via WebSocket (Channels)
# -----------------------------------------------------------------------------
@receiver(post_save, sender=Order)
def notify_on_order_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("⚠️ Channels layer not found. Skipping real-time broadcast.")
        return

    order_data = serialize_order_for_channels(instance)

    # --- New Order Created ---
    if created:
        logger.info(f"🆕 New order ({instance.id}) created, status={instance.status}.")
        async_to_sync(channel_layer.group_send)(
            'kitchen_display',
            {'type': 'send_order_update', 'order': order_data},
        )
        async_to_sync(channel_layer.group_send)(
            'pos_system',
            {'type': 'send_pos_update', 'data': {'event': 'order_created', 'order': order_data}},
        )
        async_to_sync(channel_layer.group_send)(
            'customer_display',
            {'type': 'send_display_update', 'data': {'event': 'order_created', 'order': order_data}},
        )
        return

    # --- Existing Order updated ---
    previous_status = getattr(instance, '_previous_status', None)
    if previous_status == instance.status:
        return

    logger.info(f"🔄 Order {instance.id} status changed: {previous_status} → {instance.status}")

    if instance.status == Order.Status.IN_PROGRESS:
        async_to_sync(channel_layer.group_send)(
            'kitchen_display',
            {'type': 'send_order_update', 'order': order_data},
        )

    elif instance.status == Order.Status.READY:
        async_to_sync(channel_layer.group_send)(
            'pos_system',
            {'type': 'send_pos_update', 'data': {'event': 'order_ready', 'order': order_data}},
        )
        async_to_sync(channel_layer.group_send)(
            'customer_display',
            {'type': 'send_display_update', 'data': {'event': 'order_ready', 'order': order_data}},
        )

    elif instance.status in [Order.Status.COMPLETED, Order.Status.PAID]:
        async_to_sync(channel_layer.group_send)(
            'pos_system',
            {'type': 'send_pos_update', 'data': {'event': 'order_completed', 'order': order_data}},
        )
        async_to_sync(channel_layer.group_send)(
            'customer_display',
            {'type': 'send_display_update', 'data': {'event': 'order_completed', 'order': order_data}},
        )

        # Free up the table when order is paid/completed
        if instance.table:
            table = instance.table
            if table.is_occupied:
                table.is_occupied = False
                table.save(update_fields=["is_occupied"])
                logger.info(f"🪑 Table {table.number} is now available again.")

# -----------------------------------------------------------------------------
# Deduct stock on OrderItem creation
# -----------------------------------------------------------------------------
@receiver(post_save, sender="core.OrderItem")
def deduct_stock(sender, instance, created, **kwargs):
    if not created:
        return

    menu_item = instance.menu_item
    if not menu_item:
        return
    
    recipe_items = menu_item.recipe_items.select_related("ingredient")
    for recipe in recipe_items:
        ingredient = recipe.ingredient
        total_used = recipe.quantity_used * instance.quantity
        old_qty = ingredient.quantity
        ingredient.quantity = max(old_qty - total_used, 0)
        ingredient.save(update_fields=["quantity"])
        logger.info(
            f"[Inventory] Deducted {total_used} {ingredient.unit} of {ingredient.name} "
            f"({old_qty} → {ingredient.quantity}) for {menu_item.name}"
        )