from django.urls import re_path
from . import consumers

websocket_urlpatterns = [

    # Kitchen Display System (KDS)
    re_path(r"^ws/kds/$", consumers.KitchenDisplayConsumer.as_asgi()),

    # Customer Display (requires ?table_id=)
    re_path(r"^ws/customer_display/$", consumers.CustomerDisplayConsumer.as_asgi()),

    # POS Terminals
    re_path(r"^ws/pos/$", consumers.POSConsumer.as_asgi()),

    # Staff Chat
    re_path(r"^ws/chat/$", consumers.ChatConsumer.as_asgi()),
]