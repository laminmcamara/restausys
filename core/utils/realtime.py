from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_notification(group, title, message, sound=None):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        group,
        {
            "type": "notify",
            "title": title,
            "message": message,
            "sound": sound,
        }
    )