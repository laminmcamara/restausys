from django.urls import re_path, path
from . import consumers
from django.urls import re_path
from .consumers import KitchenDisplayConsumer


websocket_urlpatterns = [

    path("ws/restaurant/<int:restaurant_id>/", consumers.RestaurantConsumer.as_asgi()),
    path("ws/table/<int:table_id>/", consumers.TableConsumer.as_asgi()),

    path("ws/kds/", consumers.KitchenDisplayConsumer.as_asgi()),
    path("ws/pos/", consumers.POSConsumer.as_asgi()),
    path("ws/chat/", consumers.ChatConsumer.as_asgi()),

    # ✅ Public Customer Display
    path(
    "ws/display/<int:restaurant_id>/",
    consumers.DisplayConsumer.as_asgi(),
    ),
    
    


    re_path(
        r"ws/kitchen/(?P<restaurant_id>\d+)/$",
        KitchenDisplayConsumer.as_asgi(),
    ),

    
]