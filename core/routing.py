from django.urls import re_path, path
from . import consumers


websocket_urlpatterns = [

    # ✅ Restaurant-wide updates
    path(
        "ws/restaurant/<int:restaurant_id>/",
        consumers.RestaurantConsumer.as_asgi(),
    ),

    # ✅ Table updates
    path(
        "ws/table/<int:table_id>/",
        consumers.TableConsumer.as_asgi(),
    ),

    # ✅ Kitchen Display (per restaurant)
    path(
        "ws/kitchen/<int:restaurant_id>/",
        consumers.KitchenDisplayConsumer.as_asgi(),
    ),

    # ✅ POS
    path(
        "ws/pos/<int:restaurant_id>/",
        consumers.POSConsumer.as_asgi(),
    ),

    # ✅ Internal Chat
    path(
        "ws/chat/<int:restaurant_id>/",
        consumers.ChatConsumer.as_asgi(),
    ),

    # ✅ Public Customer Display
    path(
        "ws/display/<int:restaurant_id>/",
        consumers.DisplayConsumer.as_asgi(),
    ),
    
]