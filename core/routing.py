from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [

    path("ws/restaurant/<int:restaurant_id>/", consumers.RestaurantConsumer.as_asgi()),
    path("ws/table/<int:table_id>/", consumers.TableConsumer.as_asgi()),

    path("ws/kds/", consumers.KitchenDisplayConsumer.as_asgi()),
    path("ws/pos/", consumers.POSConsumer.as_asgi()),
    path("ws/chat/", consumers.ChatConsumer.as_asgi()),

    # ✅ Public Customer Display
    path(
    "ws/customer/<int:restaurant_id>/",
    consumers.CustomerDisplayConsumer.as_asgi()
),
    
]