from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal
import json

# Django Channels (for real-time socket updates)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

# from .models import Table, MenuItem, Category, Order, OrderItem
from .print_utils import send_to_printer, PRINTERS


from .models import Restaurant, Table, MenuItem, Category, Order, OrderItem


# =============================================================================
# TABLE OVERVIEW DASHBOARD
# =============================================================================
from .models import Restaurant, Table, Company  # Import Company

def pos_dashboard(request):
    """Display all tables and their current status."""
    from .models import Restaurant, Table, Company

    # Try to get the user's restaurant, or fall back to the first
    restaurant = getattr(request.user, "restaurant", None)

    if restaurant is None:
        restaurant = Restaurant.objects.first()
        if not restaurant:
            # --- Ensure a default company exists ---
            company, _ = Company.objects.get_or_create(name="Default Company")

            # --- Auto-create default restaurant linked to company ---
            restaurant = Restaurant.objects.create(
                name="Default Restaurant",
                company=company
            )

    # --- Ensure some tables exist for this restaurant ---
    tables = Table.objects.filter(restaurant=restaurant)
    if not tables.exists():
        for i in range(1, 6):  # Create 5 default tables
            Table.objects.create(
                restaurant=restaurant,
                table_number=str(i),
                capacity=2  # optional default value
            )
        tables = Table.objects.filter(restaurant=restaurant)

    return render(request, "core/pos/dashboard.html", {"tables": tables})

# --- POS REST-LIKE API endpoints ---

def api_categories(request):
    """Return all categories for the menu screen."""
    data = list(Category.objects.values("id", "name"))
    return JsonResponse(data, safe=False)


def api_menu_items(request):
    """Return menu items with their category and price."""
    data = list(MenuItem.objects.values("id", "name", "price", "category_id"))
    return JsonResponse(data, safe=False)


@csrf_exempt
def api_create_order(request):
    """Handle AJAX order submission from the Direct Order UI."""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        payload = json.loads(request.body)
        items = payload.get("items", [])
        table_id = payload.get("table")
        table = Table.objects.filter(id=table_id).first() if table_id else None

        order = Order.objects.create(table=table, created_at=timezone.now())

        for i in items:
            item = MenuItem.objects.get(id=i["id"])
            qty = int(i.get("qty", 1))
            OrderItem.objects.create(order=order, item=item, quantity=qty)

        # --- PRINTER routing example ---
        for it in order.orderitem_set.all():
            if it.item.category.name.lower() in ["drinks", "beverages"]:
                send_to_printer(order, PRINTERS["bar"])
            elif it.item.category.name.lower() in ["snacks", "food"]:
                send_to_printer(order, PRINTERS["kitchen"])
        send_to_printer(order, PRINTERS["receipt"])

        if table:
            table.status = "pending"
            table.save(update_fields=["status"])

        return JsonResponse({"status": "ok", "order_id": order.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# =============================================================================
# ORDER SCREEN
# =============================================================================
def pos_order_screen(request, table_id):
    """Show menu and active ordering interface for a table."""
    table = get_object_or_404(Table, id=table_id)
    menu = MenuItem.objects.filter(restaurant=table.restaurant, available=True)
    categories = menu.values_list("category__name", flat=True).distinct()

    return render(
        request,
        "core/pos/order_screen.html",
        {"table": table, "menu": menu, "categories": categories,
},
    )


# =============================================================================
# ORDER CREATION API
# =============================================================================
@csrf_exempt  # ⚠️ Replace with proper CSRF token protection in production
@require_POST
def create_order(request):
    """Create a new order via the POS interface and broadcast to KDS + Customer."""
    data = json.loads(request.body.decode("utf-8"))
    table_id = data.get("table_id")
    items = data.get("items", [])

    if not items:
        return JsonResponse({"error": "No items in order"}, status=400)

    table = get_object_or_404(Table, id=table_id)
    restaurant = table.restaurant

    # Create the order and order items
    order = Order.objects.create(restaurant=restaurant, table=table, status="pending")

    for itm in items:
        try:
            menu = MenuItem.objects.get(id=itm["id"])
            qty = int(itm.get("quantity", 1))
            price = Decimal(str(menu.base_price)) * qty
            OrderItem.objects.create(
                order=order,
                menu_item=menu,
                quantity=qty,
                final_price=price,
            )
        except MenuItem.DoesNotExist:
            continue

    # -------------------------------------------------------------------------
    # Real-time broadcast via Django Channels to KDS + Customer Display
    # -------------------------------------------------------------------------
    channel_layer = get_channel_layer()

    payload = {
        "order_id": order.id,
        "table": table.name,
        "items": [
            {"name": oi.menu_item.name, "qty": oi.quantity}
            for oi in order.orderitem_set.all()
        ],
        "total": float(order.total_price()),
    }

    # Send to Kitchen Display (KDS)
    async_to_sync(channel_layer.group_send)(
        "kds_group",
        {"type": "new_order", "data": payload},
    )

    # Send to the Customer Display screen for this table
    async_to_sync(channel_layer.group_send)(
        f"customer_display_{table.id}",
        {"type": "new_update", "data": {"status": "new_order", **payload}},
    )

    # Optionally, send to POS group (other terminals)
    async_to_sync(channel_layer.group_send)(
        "pos_group",
        {"type": "order_status_update", "data": {"status": "pending", **payload}},
    )

    # Return success JSON
    return JsonResponse(
        {
            "success": True,
            "order_id": order.id,
            "total": order.total_price(),
        }
    )


# =============================================================================
# KITCHEN DISPLAY PAGE RENDER
# =============================================================================
def kds_screen(request):
    """Render the Kitchen Display Screen UI."""
    return render(request, "core/pos/kds.html")


# =============================================================================
# CUSTOMER DISPLAY PAGE RENDER
# =============================================================================
def customer_display(request, table_id):
    """Render the customer-facing display screen."""
    table = get_object_or_404(Table, id=table_id)
    return render(request, "core/pos/customer_display.html", {"table": table})

# =============================================================================
# TABLE DETAIL VIEW (used by QR codes)
# =============================================================================
def table_detail_view(request, access_token):
    """
    Public page reached when a customer scans a table's QR code.
    Used by Table.get_absolute_url() to generate its QR URL.
    """
    table = get_object_or_404(Table, access_token=access_token)

    # You can reuse the view’s own customer screen or a simpler template.
    return render(request, "core/pos/table_detail.html", {"table": table})

