"""
core/routing.py
=====================================================================================
Defines all WebSocket route mappings for Django Channels.
Each endpoint connects to a corresponding AsyncWebsocketConsumer subclass in
core/consumers.py, enabling real-time communication between the server
and clients such as kitchen displays, POS terminals, and customer screens.
=====================================================================================
"""

from django.urls import re_path
from . import consumers

# =============================================================================
# Real-time WebSocket route map for Django Channels
# =============================================================================
websocket_urlpatterns = [
    # -------------------------------------------------------------------------
    # Kitchen Display System (KDS)
    # Real-time stream for incoming orders and status changes in kitchen view
    # -------------------------------------------------------------------------
    re_path(r"^ws/kitchen_display/$", consumers.KitchenDisplayConsumer.as_asgi()),

    # -------------------------------------------------------------------------
    # Customer Display
    # Real-time notifications for customer-facing screens per table/order
    # -------------------------------------------------------------------------
    # Example connection: ws://host/ws/customer_display/?table_id=3
    # (table_id can be passed via querystring or via a dedicated consumer param)
    re_path(r"^ws/customer_display/$", consumers.CustomerDisplayConsumer.as_asgi()),

    # -------------------------------------------------------------------------
    # POS Terminals
    # Cashier or waiter interfaces receive updates and broadcast actions
    # -------------------------------------------------------------------------
    re_path(r"^ws/pos/$", consumers.POSConsumer.as_asgi()),

    # -------------------------------------------------------------------------
    # Staff Chat and Internal Messaging
    # Enables live staff communication by room (e.g. ws/chat/general/)
    # -------------------------------------------------------------------------
    # re_path(r"^ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/chat/$", consumers.ChatConsumer.as_asgi()),

    # -------------------------------------------------------------------------
    # Global Order Status Stream
    # Multi-purpose event bus for order life-cycle updates
    # -------------------------------------------------------------------------
    re_path(r"^ws/orders/$", consumers.OrderConsumer.as_asgi()),

    # -------------------------------------------------------------------------
    # Ticket Tracking (optional future enhancement)
    # Used for kitchen or service tickets monitoring
    # -------------------------------------------------------------------------
    re_path(r"^ws/tickets/$", consumers.TicketConsumer.as_asgi()),
]