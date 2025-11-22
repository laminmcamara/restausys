from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging

# Try to import the printer utility
try:
    from core.utils import send_to_printer
except ImportError:
    send_to_printer = None

logger = logging.getLogger(__name__)


def broadcast_kitchen_ticket(ticket, action="create"):
    """
    Broadcast a kitchen ticket event over the 'kitchen_display' WebSocket group
    and (optionally) print corresponding tickets to kitchen, drinks, and POS printers.

    Args:
        ticket (KitchenTicket): The kitchen ticket instance to broadcast.
        action (str): "create", "update", or "delete".
    """
    if not ticket:
        return

    try:
        # ------------------------------------------------------------------
        # Build data for WebSocket broadcast
        # ------------------------------------------------------------------
        layer = get_channel_layer()
        if not layer:
            logger.warning("No channel layer configured; broadcast skipped.")
            return

        order_item = ticket.order_item
        order = order_item.order
        menu_item = order_item.menu_item
        is_drink = getattr(menu_item, "is_drink", False)

        data = {
            "action": action,
            "ticket": {
                "id": ticket.id,
                "order_id": str(order.id)[:8],
                "item_name": menu_item.name,
                "quantity": order_item.quantity,
                "status": order.status,
                "priority": getattr(ticket, "priority", None),
                "station": getattr(ticket, "station", None),
                "due_at": ticket.due_at.strftime("%H:%M") if ticket.due_at else None,
                "time": timezone.localtime(ticket.created_at).strftime("%H:%M"),
            },
        }

        async_to_sync(layer.group_send)(
            "kitchen_display",
            {"type": "kitchen_update", "data": data},
        )
        logger.info(
            f"Broadcasted kitchen ticket #{ticket.id} ({action}) to WebSocket group."
        )

        # ------------------------------------------------------------------
        # PRINTING SECTION (KITCHEN / DRINKS / POS)
        # ------------------------------------------------------------------
        if action == "create" and callable(send_to_printer):
            text_header = (
                f"========== NEW TICKET ==========\n"
                f"ORDER #{order.id}\n"
                f"Created: {timezone.localtime(ticket.created_at).strftime('%H:%M')}\n"
                f"---------------------------------\n"
            )
            item_line = f"{order_item.quantity}x {menu_item.name}\n"
            footer = "---------------------------------\n\n"

            ticket_text = text_header + item_line + footer

            # --- Print to Kitchen printer (food or default) ---
            # Print food items or everything as default
            if not is_drink:
                try:
                    send_to_printer("kitchen", ticket_text)
                    logger.info(f"Printed ticket #{ticket.id} to Kitchen printer.")
                except Exception as e:
                    logger.error(
                        f"Error printing to Kitchen printer for ticket #{ticket.id}: {e}"
                    )

            # --- Print to Drinks printer (if item is a drink) ---
            if is_drink:
                try:
                    send_to_printer("drinks", ticket_text)
                    logger.info(f"Printed ticket #{ticket.id} to Drinks printer.")
                except Exception as e:
                    logger.error(
                        f"Error printing to Drinks printer for ticket #{ticket.id}: {e}"
                    )

            # --- Always print customer copy / receipt at POS printer ---
            try:
                receipt_text = (
                    f"====== POS RECEIPT ======\n"
                    f"Order #{order.id}\n"
                    f"Item: {menu_item.name}\n"
                    f"Qty: {order_item.quantity}\n"
                    f"-------------------------\n\n"
                )
                send_to_printer("pos", receipt_text)
                logger.info(f"Printed ticket #{ticket.id} to POS printer.")
            except Exception as e:
                logger.error(
                    f"Error printing to POS printer for ticket #{ticket.id}: {e}"
                )

    except Exception as exc:
        logger.error(f"Kitchen broadcast failed: {exc}", exc_info=True)