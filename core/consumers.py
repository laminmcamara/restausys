import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils.timezone import now
from core.models import ChatMessage, Table, Order
from django.forms.models import model_to_dict
logger = logging.getLogger("channels")
from asgiref.sync import sync_to_async
from core.serializers import OrderSerializer
from django.core.serializers.json import DjangoJSONEncoder


logger = logging.getLogger(__name__)

# ==============================================================================
# Base Safe Consumer
# ==============================================================================

class SafeConsumer(AsyncWebsocketConsumer):
    """
    Base consumer with safe JSON sending and authentication helpers.
    Fully async-safe (no ORM access in async context).
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
        """
        Safely retrieve restaurant ID without triggering ORM queries
        inside async context.
        """
        user = await self.get_authenticated_user()
        if not user:
            return None

        # ✅ SAFE: direct FK id access (no DB query)
        if hasattr(user, "restaurant_id") and user.restaurant_id:
            return user.restaurant_id

        # ✅ If restaurant is on profile (requires DB lookup)
        return await self._get_profile_restaurant_id(user)

    @database_sync_to_async
    def _get_profile_restaurant_id(self, user):
        """
        Runs in thread pool. Safe to access ORM here.
        """
        if hasattr(user, "profile") and hasattr(user.profile, "restaurant_id"):
            return user.profile.restaurant_id
        return None

# ==============================================================================
# Staff Chat (Restaurant-Isolated)
# ==============================================================================

class ChatConsumer(SafeConsumer):

    async def connect(self):
        user = await self.get_authenticated_user()
        print("DEBUG USER:", user)

        if not user:
            print("REJECT: no authenticated user")
            await self.close(code=4001)
            return

        role = getattr(user, "role", "").lower()
        print("DEBUG ROLE:", role)

        if role not in ("staff", "manager", "chef", "supervisor"):
            print("REJECT: invalid role")
            await self.close(code=4003)
            return

        restaurant_id = await self.get_restaurant_id()
        print("DEBUG RESTAURANT ID:", restaurant_id)

        if not restaurant_id:
            print("REJECT: no restaurant")
            await self.close(code=4004)
            return

        self.group_name = f"chat_{restaurant_id}"
        print("DEBUG GROUP NAME:", self.group_name)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        print("✅ Chat WebSocket accepted")

        history = await self._get_recent_messages(restaurant_id)
        await self.safe_send({
            "type": "history",
            "messages": history
        })

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

        role = getattr(user, "role", "").lower()
        if role not in ("chef", "manager", "supervisor"):
            await self.close(code=4003)
            return

        restaurant_id = await self.get_restaurant_id()
        if not restaurant_id:
            await self.close(code=4004)
            return

        self.group_name = f"kitchen_{restaurant_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def order_update(self, event):
        await self.safe_send(event["data"])
        
        
class RestaurantConsumer(SafeConsumer):

    async def connect(self):
        user = await self.get_authenticated_user()
        if not user:
            await self.close(code=4001)
            return

        requested_restaurant_id = self.scope["url_route"]["kwargs"]["restaurant_id"]

        user_restaurant_id = await self.get_restaurant_id()
        if not user_restaurant_id:
            await self.close(code=4004)
            return

        # 🚨 Prevent cross‑restaurant access
        if str(user_restaurant_id) != str(requested_restaurant_id):
            await self.close(code=4003)
            return

        self.restaurant_id = requested_restaurant_id
        self.group_name = f"restaurant_{self.restaurant_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def order_update(self, event):
        await self.safe_send(event["data"])
        
class TableConsumer(SafeConsumer):

    async def connect(self):
        user = await self.get_authenticated_user()
        if not user:
            await self.close(code=4001)
            return

        self.table_id = int(self.scope["url_route"]["kwargs"]["table_id"])

        # ✅ Fetch table safely
        table = await sync_to_async(
            lambda: Table.objects.select_related("restaurant").filter(id=self.table_id).first()
        )()

        if not table:
            await self.close(code=4004)
            return

        user_restaurant_id = await self.get_restaurant_id()
        if not user_restaurant_id:
            await self.close(code=4004)
            return

        # 🚨 Prevent cross-restaurant access
        if table.restaurant_id != user_restaurant_id:
            await self.close(code=4003)
            return

        self.group_name = f"table_{self.table_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # ✅ Send latest active order
        order = await sync_to_async(
            lambda: Order.objects.filter(
                table_id=self.table_id
            ).exclude(
                status__in=["CANCELED"]
            ).order_by("-created_at").first()
        )()

        if order:
            data = await sync_to_async(
                lambda: OrderSerializer(order).data
            )()

            await self.safe_send({
                "type": "order_update",
                "order": data
            })
        else:
            await self.safe_send({
                "type": "order_update",
                "order": None
            })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def order_update(self, event):
        await self.safe_send(event["data"])
        
class CustomerDisplayConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.restaurant_id = self.scope["url_route"]["kwargs"]["restaurant_id"]
        self.group_name = f"customer_{self.restaurant_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def order_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))