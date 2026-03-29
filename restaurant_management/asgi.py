# restaurant_management/asgi.py
"""
ASGI entrypoint for Django + Channels.
Handles:
- HTTP requests via Django's ASGI application
- WebSocket connections via Channels routing
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# --------------------------------------------------------------------------
# Environment Setup
# --------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant_management.settings")

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# --------------------------------------------------------------------------
# WebSocket Routing (import AFTER Django setup)
# --------------------------------------------------------------------------
from core import routing as core_routing

# --------------------------------------------------------------------------
# Combined ASGI Application
# --------------------------------------------------------------------------
application = ProtocolTypeRouter({
    # Standard HTTP traffic
    "http": django_asgi_app,

    # WebSocket traffic
    "websocket": AuthMiddlewareStack(
        URLRouter(
            core_routing.websocket_urlpatterns
        )
    ),
})

# --------------------------------------------------------------------------
# Optional Debug Log
# --------------------------------------------------------------------------
if os.getenv("DEBUG_CHANNELS", "false").lower() == "true":
    print("✅ ASGI loaded: Channels WebSocket routing active.")