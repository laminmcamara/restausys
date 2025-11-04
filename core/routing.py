# core/routing.py

from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/kitchen_display/$', consumers.KitchenDisplayConsumer.as_asgi()),
    re_path(r'ws/chat/$', ChatConsumer.as_asgi()),  # WebSocket URL for chat
]
