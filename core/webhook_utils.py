import hmac
import hashlib
import json
import requests
import uuid
from django.utils import timezone
from .models import WebhookConfiguration, WebhookEvent

def trigger_outbound_webhook(restaurant, event_type, payload):
    """
    Sends a webhook notification to the restaurant's configured URL.
    """
    try:
        config = restaurant.webhook_config
    except WebhookConfiguration.DoesNotExist:
        return # No webhook configured for this restaurant

    # Determine environment and URL
    # For now, we'll default to Live if enabled, otherwise Test
    if config.is_live_enabled and config.live_webhook_url:
        url = config.live_webhook_url
        secret = config.live_secret
        env = 'LIVE'
    elif config.is_test_enabled and config.test_webhook_url:
        url = config.test_webhook_url
        secret = config.test_secret
        env = 'TEST'
    else:
        return # Webhooks not enabled or URLs missing

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    
    # Prepare the wrapper payload
    final_payload = {
        "id": event_id,
        "event": event_type,
        "created_at": timezone.now().isoformat(),
        "restaurant_id": str(restaurant.id),
        "data": payload
    }

    # Create the signature (HMAC SHA256)
    # This allows the receiver to verify the message is authentic
    payload_bytes = json.dumps(final_payload).encode('utf-8')
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    # Log the event in our database
    webhook_event = WebhookEvent.objects.create(
        restaurant=restaurant,
        event_id=event_id,
        event_type=event_type,
        payload=final_payload,
        environment=env,
        status='PENDING'
    )

    # Send the request
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-BeePOS-Signature': signature,
            'X-BeePOS-Event-Id': event_id
        }
        
        response = requests.post(url, json=final_payload, headers=headers, timeout=10)
        
        webhook_event.status = 'SENT' if response.status_code < 300 else 'FAILED'
        webhook_event.response_code = response.status_code
        webhook_event.save()
        
    except Exception as e:
        webhook_event.status = 'FAILED'
        webhook_event.save()
        print(f"Webhook delivery failed: {str(e)}")