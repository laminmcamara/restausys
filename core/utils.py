from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.db.models import Sum, F
from datetime import timedelta
import logging

from .models import Order, DailyReport

logger = logging.getLogger(__name__)

# Optional printer import (safe)
try:
    from core.print_utils import send_to_printer
except ImportError:
    send_to_printer = None


# ==============================================================
# ================== KITCHEN BROADCAST =========================
# ==============================================================

def broadcast_kitchen_ticket(ticket, action="create"):
    if not ticket:
        return

    try:
        layer = get_channel_layer()
        if not layer:
            logger.warning("No channel layer configured.")
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

        logger.info(f"Kitchen ticket #{ticket.id} broadcasted.")

        # Optional printing
        if action == "create" and callable(send_to_printer):
            header = (
                f"========== NEW TICKET ==========\n"
                f"ORDER #{order.id}\n"
                f"Time: {timezone.localtime(ticket.created_at).strftime('%H:%M')}\n"
                f"---------------------------------\n"
            )

            line = f"{order_item.quantity}x {menu_item.name}\n"
            footer = "---------------------------------\n\n"

            text = header + line + footer

            try:
                if is_drink:
                    send_to_printer("drinks", text)
                else:
                    send_to_printer("kitchen", text)

                send_to_printer("pos", text)

            except Exception as e:
                logger.error(f"Printer error: {e}")

    except Exception as exc:
        logger.error("Kitchen broadcast failed", exc_info=True)


# ==============================================================
# ================== DAILY REPORT ==============================
# ==============================================================

def generate_daily_report(restaurant):
    if not restaurant:
        return {
            "total_orders": 0,
            "total_revenue": 0,
        }

    today = timezone.now().date()

    # ✅ Better to use stored unit_price instead of menu price
    total_expr = F("items__quantity") * F("items__unit_price")

    orders = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.PAID,
        created_at__date=today,
    )

    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum(total_expr))["total"] or 0

    DailyReport.objects.update_or_create(
        restaurant=restaurant,
        date=today,
        defaults={
            "total_orders": total_orders,
            "total_revenue": total_revenue,
        },
    )

    return {
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
    }


# ==============================================================
# ================== PERIOD SUMMARY ============================
# ==============================================================

def calculate_period_summary(restaurant, days):
    date_from = timezone.now().date() - timedelta(days=days)

    total_expr = F("items__quantity") * F("items__unit_price")

    orders = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.PAID,
        created_at__date__gte=date_from,
    )

    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum(total_expr))["total"] or 0

    return {
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
    }