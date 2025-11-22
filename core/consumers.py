import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("channels")


# ==============================================================================
# Base Helper
# ==============================================================================
class SafeConsumer(AsyncWebsocketConsumer):
    """Base consumer with safe JSON sending method."""

    async def safe_send(self, data: dict):
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as exc:
            logger.error(f"{self.__class__.__name__} failed to send data: {exc}")


# ==============================================================================
# Enhanced Global Chat Consumer
# ==============================================================================
class ChatConsumer(SafeConsumer):
    """Authenticated, persistent staff chat with full audit trail."""

    # --------------------------------------------------------------------------
    # Connection lifecycle
    # --------------------------------------------------------------------------
    async def connect(self):
        user = self.scope.get("user")

        if not await self._is_authorized(user):
            await self.close(code=4001)
            logger.warning("❌ Chat connect refused (unauthorized user)")
            return

        self.group_name = "staff_chat"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info(f"✅ Chat connected: {user.username} ({user.get_full_name() or '-'})")

        # Send last 50 messages for quick context/history
        history = await self._get_recent_messages(limit=50)
        await self.safe_send({"type": "history", "messages": history})

        # Broadcast join notice
        await self._broadcast_system_message(f"{user.username} joined the chat.")

    async def disconnect(self, code):
        user = self.scope.get("user")
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if user and not user.is_anonymous:
            await self._broadcast_system_message(f"{user.username} left the chat.")
            logger.info(f"👋 Chat disconnected: {user.username}")

    # --------------------------------------------------------------------------
    # Message reception & broadcast
    # --------------------------------------------------------------------------
    async def receive(self, text_data):
        """Process and broadcast a new chat message."""
        user = self.scope["user"]

        try:
            data = json.loads(text_data)
            message = (data.get("message") or "").strip()
        except Exception as exc:
            await self.safe_send({"error": "Invalid JSON payload"})
            logger.error(f"❌ Invalid chat payload from {user}: {exc}")
            return

        if not message:
            await self.safe_send({"error": "Message text required"})
            return

        logger.debug(f"💬 Chat message from {user.username}: {message}")

        # Persist message to DB
        msg_obj = await self._save_message(user, message)

        payload = {
            "sender": user.username,
            "message": message,
            "timestamp": msg_obj.timestamp.isoformat(),
        }

        await self.channel_layer.group_send(
            self.group_name, {"type": "chat_message", "payload": payload}
        )

    async def chat_message(self, event):
        """Emit broadcasted message to the WebSocket client."""
        await self.safe_send({"type": "chat", **event["payload"]})

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    async def _broadcast_system_message(self, text):
        """Send system-generated notices to all participants."""
        payload = {
            "sender": "System",
            "message": text,
            "timestamp": now().isoformat(),
        }
        await self.channel_layer.group_send(
            self.group_name, {"type": "chat_message", "payload": payload}
        )

    @database_sync_to_async
    def _save_message(self, user, text):
        """Persist message to DB (sync helper)."""
        return ChatMessage.objects.create(sender=user, content=text)

    @database_sync_to_async
    def _get_recent_messages(self, limit=50):
        """Return serialized list of recent chat messages."""
        qs = ChatMessage.objects.select_related("sender").order_by("-timestamp")[:limit]
        # return chronological (oldest first) for display
        return [
            {
                "sender": m.sender.username if m.sender else "System",
                "message": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in reversed(list(qs))
        ]

    @database_sync_to_async
    def _is_authorized(self, user):
        """Allow only authenticated staff/manager-type accounts."""
        if not user or user.is_anonymous:
            return False
        try:
            role = getattr(user, "profile", None)
            role = getattr(role, "role", "").lower() if role else ""
        except Exception:
            role = ""
        return role in ("staff", "manager", "chef", "supervisor")
        
# ==============================================================================
# Kitchen Display (KDS) Consumer
# ==============================================================================
class KitchenDisplayConsumer(SafeConsumer):
    async def connect(self):
        self.room_group_name = "kds_group"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"KDS connected: {self.channel_name}")

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def new_order(self, event):
        """Called when waiter places new order."""
        await self.safe_send(event["data"])

    async def order_status_update(self, event):
        """Handles updates like Cooking/Ready/Served/Paid."""
        await self.safe_send(event["data"])

    async def receive(self, text_data):
        logger.debug(f"KDS inbound: {text_data}")


# ==============================================================================
# POS Terminal Consumer
# ==============================================================================
class POSConsumer(SafeConsumer):
    async def connect(self):
        self.room_group_name = "pos_group"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"POS connected: {self.channel_name}")

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def order_status_update(self, event):
        await self.safe_send(event["data"])


# ==============================================================================
# Customer Display (Per Table)
# ==============================================================================
class CustomerDisplayConsumer(SafeConsumer):
    async def connect(self):
        # support ?table_id=<id> querystring
        query_params = self.scope.get("query_string", b"").decode()
        table_id = None
        if "table_id=" in query_params:
            try:
                table_id = int(query_params.split("table_id=")[1].split("&")[0])
            except ValueError:
                pass

        if table_id is None:
            # fallback generic
            self.group_name = "customer_display_all"
        else:
            self.group_name = f"customer_display_{table_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"CustomerDisplay connected ({self.group_name})")

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def new_update(self, event):
        """Handles new order or status broadcast to a specific table."""
        await self.safe_send(event["data"])

    async def order_status_update(self, event):
        """Handles order status changes for that table."""
        await self.safe_send(event["data"])


# ==============================================================================
# Generic Order / Ticket Streams (Optional Future Use)
# ==============================================================================
class OrderConsumer(SafeConsumer):
    async def connect(self):
        await self.channel_layer.group_add("orders_group", self.channel_name)
        await self.accept()

    async def disconnect(self, _):
        await self.channel_layer.group_discard("orders_group", self.channel_name)

    async def order_status_update(self, event):
        await self.safe_send(event["data"])


class TicketConsumer(SafeConsumer):
    async def connect(self):
        await self.channel_layer.group_add("tickets_group", self.channel_name)
        await self.accept()

    async def disconnect(self, _):
        await self.channel_layer.group_discard("tickets_group", self.channel_name)

    async def ticket_update(self, event):
        await self.safe_send(event["data"])