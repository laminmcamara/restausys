import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Import models from the core app
from .models import Order
# Import the serializers we just created in the core app
# from .serializers import OrderSerializer 

# Get an instance of a logger for better debugging
logger = logging.getLogger(__name__)

# --- Order State Tracking Signal ---

@receiver(pre_save, sender=Order)
def store_previous_order_status(sender, instance, **kwargs):
    """
    Before saving an order, attach its 'old' status to the instance.
    This allows us to detect a status *change* in the post_save signal.
    """
    if instance.pk:  # Only run on updates, not on creation
        try:
            # Store the status from the database before the save happens
            instance._previous_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            # This case should ideally not be hit on an update, but it's safe to handle
            instance._previous_status = None

# --- Main Notification Signals ---

@receiver(post_save, sender=Order)
def notify_on_order_update(sender, instance, created, **kwargs):
    """
    Sends notifications to different groups based on the order's
    status change. This is the central hub for order notifications.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Channels layer not found. Skipping real-time notification.")
        return

    # Serialize the order data once using our robust serializer
    # Uncomment and implement the OrderSerializer if needed
    # serializer = OrderSerializer(instance)
    # order_data = serializer.data

    # Case 1: A new order is created and sent directly to the kitchen
    if created and instance.status == Order.Status.IN_KITCHEN:
        logger.info(f"New order {instance.id} created for kitchen.")
        async_to_sync(channel_layer.group_send)(
            'kitchen_display',  # Group name for all kitchen screens
            {'type': 'send_order_update', 'order': instance}  # Use instance directly if serializer is not used
        )
        return  # Stop further processing as this is the primary event

    # Case 2: An existing order's status is changed
    previous_status = getattr(instance, '_previous_status', None)
    if not created and previous_status != instance.status:
        
        # Notify KITCHEN when an order is moved to 'In Kitchen'
        if instance.status == Order.Status.IN_KITCHEN:
            logger.info(f"Order {instance.id} sent to kitchen.")
            async_to_sync(channel_layer.group_send)(
                'kitchen_display',
                {'type': 'send_order_update', 'order': instance}  # Use instance directly if serializer is not used
            )

        # Notify SERVERS when an order is 'Ready' for pickup
        elif instance.status == Order.Status.READY:
            logger.info(f"Order {instance.id} is ready for pickup.")
            # Example: notify the specific server who created the order
            # Assumes your Order model has a 'created_by' field linked to a User
            if hasattr(instance, 'created_by') and instance.created_by:
                server_group_name = f"server_{instance.created_by.id}"
                async_to_sync(channel_layer.group_send)(
                    server_group_name,
                    {'type': 'send_order_ready', 'order': instance}  # Use instance directly if serializer is not used
                )
            
            # Also send to a general 'servers' group for anyone to see
            async_to_sync(channel_layer.group_send)(
                'servers',
                {'type': 'send_order_ready', 'order': instance}  # Use instance directly if serializer is not used
            )

# The HR and System Logging Signal Example has been removed since Profile is not used anymore.
