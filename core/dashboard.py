from datetime import timedelta
from django.contrib import admin
from django.template.response import TemplateResponse
from django.utils import timezone
from django.db.models import Sum, F, Count, FloatField
from django.db.models.functions import TruncDay
import json

from core.models import (
    Order,
    MenuItem,
    Restaurant,
    InventoryItem,
    CustomUser,
    Table,
    KitchenTicket,
    Payment,
    Shift,
)


class RestaurantAdminDashboard(admin.AdminSite):
    """Custom Django Admin Dashboard with interactive Chart.js analytics."""

    site_header = "Restaurant Management Admin"
    site_title = "Restaurant Dashboard"
    index_title = "Overview"

    def index(self, request, extra_context=None):
        context = {
            **self.each_context(request),
            "title": "Restaurant Performance Overview",
        }

        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)

        recent_orders = Order.objects.filter(created_at__gte=start_date)
        paid_orders = recent_orders.filter(status=Order.Status.PAID)

        total_revenue = (
            paid_orders.aggregate(total=Sum(F("items__quantity") * F("items__menu_item__base_price")))["total"] or 0
        )
        total_orders = paid_orders.count()
        avg_order_value = (
            paid_orders.aggregate(
                avg=Sum(F("items__quantity") * F("items__menu_item__base_price")) / (total_orders or 1)
            )["avg"]
            or 0
        )

        sales_by_day = (
            paid_orders.annotate(day=TruncDay("created_at"))
            .values("day")
            .annotate(
                revenue=Sum(F("items__quantity") * F("items__menu_item__base_price")),
                order_count=Count("id", distinct=True),
            )
            .order_by("day")
        )

        labels = [s["day"].strftime("%b %d") for s in sales_by_day]
        revenues = [float(s["revenue"] or 0) for s in sales_by_day]
        order_counts = [s["order_count"] for s in sales_by_day]
        avg_values = [
            (rev / count if count > 0 else 0) for rev, count in zip(revenues, order_counts)
        ]

        context.update(
            {
                "kpis": {
                    "total_revenue": round(total_revenue, 2),
                    "total_orders": total_orders,
                    "avg_order_value": round(avg_order_value, 2),
                    "active_menu_items": MenuItem.objects.filter(is_active=True).count(),
                    "restaurants": Restaurant.objects.count(),
                    "low_stock": InventoryItem.objects.filter(
                        quantity__lt=F("low_stock_threshold")
                    ).count(),
                },
                "recent_orders": recent_orders.order_by("-created_at")[:10],
                "chart_json": json.dumps(
                    {
                        "labels": labels,
                        "revenue": revenues,
                        "orders": order_counts,
                        "average": avg_values,
                    }
                ),
            }
        )

        if extra_context:
            context.update(extra_context)

        return TemplateResponse(request, "admin/restaurant_dashboard.html", context)


restaurant_admin_site = RestaurantAdminDashboard(name="restaurant_admin")

restaurant_admin_site.register(CustomUser)
restaurant_admin_site.register(Table)
restaurant_admin_site.register(MenuItem)
restaurant_admin_site.register(Order)
restaurant_admin_site.register(InventoryItem)
restaurant_admin_site.register(KitchenTicket)
restaurant_admin_site.register(Payment)
restaurant_admin_site.register(Shift)
restaurant_admin_site.register(Restaurant)