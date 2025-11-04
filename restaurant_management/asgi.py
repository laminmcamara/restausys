import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from core import routing  # Ensure you have a routing.py in your core app

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_management.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Handle HTTP requests
    "websocket": AuthMiddlewareStack(  # Handle WebSocket connections
        URLRouter(
            routing.websocket_urlpatterns  # Include your WebSocket URL patterns
        )
    ),
})
