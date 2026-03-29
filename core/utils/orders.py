from decimal import Decimal
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_order_update(order):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kitchen_display",
        {
            "type": "send_order_update",
            "order": {
                "id": str(order.id),
                "status": order.status,
                "items": [
                    {
                        "name": i.menu_item.name,
                        "variant": i.variant.name if i.variant else None,
                        "qty": i.quantity,
                        "status": i.status,
                    }
                    for i in order.items.all()
                ],
            },
        },
    )
    

def serialize_order(order):
    return {
        "id": str(order.id),
        "status": order.status,
        "table": order.table.name if order.table else None,
        "type": order.order_type,
        "items": [
            {
                "id": str(i.id),
                "name": i.menu_item.name,
                "variant": i.variant.name if i.variant else None,
                "qty": i.quantity,
                "status": i.status,
            }
            for i in order.items.all()
        ]
    }