# restaurant_management/asgi.py

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import WebSocket routing from core app
from core import routing

# -----------------------------------------------------------------------------
# Environment setup
# -----------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_management.settings')
django.setup()

# -----------------------------------------------------------------------------
# ASGI application configuration
# -----------------------------------------------------------------------------
application = ProtocolTypeRouter({
    # Handles traditional HTTP requests
    "http": get_asgi_application(),

    # Handles WebSocket connections via Django Channels
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns  # Core/WebSocket routes
        )
    ),
})

# -----------------------------------------------------------------------------
# Optional: Debug diagnostic
# -----------------------------------------------------------------------------
# You can enable this check during local development to confirm the app loads properly.
if os.getenv("DEBUG_CHANNELS", "false").lower() == "true":
    print("✅ ASGI: Django Channels routing loaded successfully.")