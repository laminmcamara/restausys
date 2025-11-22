from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Category, Order, OrderItem, MenuItem, Table

def api_categories(request):
    data = list(Category.objects.values("id", "name"))
    return JsonResponse(data, safe=False)

def api_menu_items(request):
    data = list(MenuItem.objects.values("id", "name", "price", "category_id"))
    return JsonResponse(data, safe=False)



@csrf_exempt
def new_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
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

        # ======== PRINTER LOGIC ========
        # Example pseudo‑routing:
        from .print_utils import send_to_printer, PRINTERS
        if any(mi.category.name.lower() in ["drinks", "beverages"]
               for mi in MenuItem.objects.filter(id__in=[i["id"] for i in items])):
            send_to_printer(order, PRINTERS["bar"])
        if any(mi.category.name.lower() in ["food", "snacks"]
               for mi in MenuItem.objects.filter(id__in=[i["id"] for i in items])):
            send_to_printer(order, PRINTERS["kitchen"])
        send_to_printer(order, PRINTERS["receipt"])
        # ===============================

        return JsonResponse({"status": "ok", "order_id": order.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)