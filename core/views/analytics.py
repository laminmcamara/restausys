from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils.timezone import localdate
from pos.models import Order, OrderItem

def analytics_summary(request):
    today = localdate()
    orders = Order.objects.filter(created_at__date=today)

    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum("total"))["total"] or 0
    avg_order = total_revenue / total_orders if total_orders > 0 else 0

    status_counts = {
        s: orders.filter(status=s).count()
        for s in ["pending", "cooking", "ready", "served", "paid"]
    }

    # Revenue by hour
    hourly = (
        orders.extra(select={"hour": "strftime('%H', created_at)"})
        .values("hour")
        .annotate(total=Sum("total"))
        .order_by("hour")
    )

    # Best selling items
    best_items = (
        OrderItem.objects.filter(order__created_at__date=today)
        .values("name")
        .annotate(qty=Sum("qty"))
        .order_by("-qty")[:5]
    )

    return JsonResponse({
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "avg_order": float(avg_order),
        "status_counts": status_counts,
        "hourly_revenue": list(hourly),
        "best_items": list(best_items),
    })

