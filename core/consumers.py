import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils.timezone import now
from core.models import ChatMessage, Table, Order
from django.forms.models import model_to_dict
logger = logging.getLogger("channels")


# ==============================================================================
# Base Safe Consumer
# ==============================================================================

class SafeConsumer(AsyncWebsocketConsumer):
    """
    Base consumer with safe JSON sending and authentication helpers.
    """

    async def safe_send(self, data: dict):
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as exc:
            logger.error(f"{self.__class__.__name__} send failed: {exc}")

    async def get_authenticated_user(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            return None
        return user

    async def get_restaurant_id(self):
        user = await self.get_authenticated_user()
        if not user:
            return None
        return getattr(user, "restaurant_id", None)


# ==============================================================================
# Staff Chat (Restaurant-Isolated)
# ==============================================================================

class ChatConsumer(SafeConsumer):

    async def connect(self):
        user = await self.get_authenticated_user()
        if not user:
            await self.close(code=4001)
            return

        role = getattr(getattr(user, "profile", None), "role", "").lower()
        if role not in ("staff", "manager", "chef", "supervisor"):
            await self.close(code=4003)
            return

        restaurant_id = await self.get_restaurant_id()
        if not restaurant_id:
            await self.close(code=4004)
            return

        self.group_name = f"chat_{restaurant_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        history = await self._get_recent_messages(restaurant_id)
        await self.safe_send({"type": "history", "messages": history})

        await self._broadcast_system_message(
            restaurant_id,
            f"{user.username} joined."
        )

    async def disconnect(self, code):
        user = self.scope.get("user")
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if user and not user.is_anonymous:
            restaurant_id = getattr(user, "restaurant_id", None)
            if restaurant_id:
                await self._broadcast_system_message(
                    restaurant_id,
                    f"{user.username} left."
                )

    async def receive(self, text_data):
        user = await self.get_authenticated_user()
        if not user:
            return

        try:
            data = json.loads(text_data)
            message = (data.get("message") or "").strip()
        except Exception:
            return await self.safe_send({"error": "Invalid JSON"})

        if not message:
            return await self.safe_send({"error": "Empty message"})

        restaurant_id = user.restaurant_id
        msg_obj = await self._save_message(user, message, restaurant_id)

        payload = {
            "type": "chat",
            "sender": user.username,
            "message": message,
            "timestamp": msg_obj.timestamp.isoformat(),
        }

        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat_message", "payload": payload}
        )

    async def chat_message(self, event):
        await self.safe_send(event["payload"])

    async def _broadcast_system_message(self, restaurant_id, text):
        payload = {
            "type": "chat",
            "sender": "System",
            "message": text,
            "timestamp": now().isoformat(),
        }

        await self.channel_layer.group_send(
            f"chat_{restaurant_id}",
            {"type": "chat_message", "payload": payload}
        )

    @database_sync_to_async
    def _save_message(self, user, text, restaurant_id):
        return ChatMessage.objects.create(
            sender=user,
            content=text,
            restaurant_id=restaurant_id
        )

    @database_sync_to_async
    def _get_recent_messages(self, restaurant_id, limit=50):
        qs = (
            ChatMessage.objects
            .filter(restaurant_id=restaurant_id)
            .select_related("sender")
            .order_by("-timestamp")[:limit]
        )
        return [
            {
                "sender": m.sender.username if m.sender else "System",
                "message": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in reversed(list(qs))
        ]


# ==============================================================================
# POS Consumer (Restaurant-Isolated)
# ==============================================================================

class POSConsumer(SafeConsumer):

    async def connect(self):
        user = await self.get_authenticated_user()
        if not user:
            await self.close(code=4001)
            return

        restaurant_id = await self.get_restaurant_id()
        if not restaurant_id:
            await self.close(code=4004)
            return

        self.group_name = f"pos_{restaurant_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_status_update(self, event):
        await self.safe_send(event["data"])

    async def table_update(self, event):
        await self.safe_send(event["data"])

    async def table_flash(self, event):
        await self.safe_send(event["data"])


# ==============================================================================
# Kitchen Display Consumer (Role Restricted)
# ==============================================================================

class KitchenDisplayConsumer(SafeConsumer):

    async def connect(self):
        user = await self.get_authenticated_user()
        if not user:
            await self.close(code=4001)
            return

        role = getattr(getattr(user, "profile", None), "role", "").lower()
        if role not in ("chef", "manager", "supervisor"):
            await self.close(code=4003)
            return

        restaurant_id = await self.get_restaurant_id()
        self.group_name = f"kitchen_{restaurant_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_update(self, event):
        await self.safe_send(event["data"])


# ==============================================================================
# Customer Display Consumer (Per Table + Validated)
# ==============================================================================


class CustomerDisplayConsumer(SafeConsumer):

    async def connect(self):
        query = self.scope.get("query_string", b"").decode()

        table_id = None
        if "table_id=" in query:
            try:
                table_id = int(query.split("table_id=")[1].split("&")[0])
            except Exception:
                await self.close(code=4002)
                return

        if not table_id:
            await self.close(code=4002)
            return

        valid = await self._validate_table(table_id)
        if not valid:
            await self.close(code=4004)
            return

        self.table_id = table_id
        self.group_name = f"customer_table_{table_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # ✅ SEND CURRENT ACTIVE ORDER IMMEDIATELY
        order_data = await self._get_active_order(table_id)

        if order_data:
            await self.safe_send({
                "type": "order_update",
                "order": order_data
            })
        else:
            await self.safe_send({
                "type": "no_order_found"
            })

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_update(self, event):
        await self.safe_send(event["data"])

    async def order_status_update(self, event):
        await self.safe_send(event["data"])

    @database_sync_to_async
    def _validate_table(self, table_id):
        return Table.objects.filter(id=table_id).exists()

    @database_sync_to_async
    def _get_active_order(self, table_id):
        order = (
            Order.objects
            .filter(table_id=table_id, status__in=["preparing", "ready"])
            .prefetch_related("items__product")
            .order_by("-created_at")
            .first()
        )

        if not order:
            return None

        return {
            "id": order.id,
            "table": order.table.name,
            "status": order.status,
            "items": [
                {
                    "name": item.product.name,
                    "qty": item.quantity,
                    "price": float(item.price),
                }
                for item in order.items.all()
            ]
        }