import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction

from .models import Order, Payment, PaymentIntentLog
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig:
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception:
        return HttpResponse(status=400)

    # ✅ Log all incoming intents
    PaymentIntentLog.objects.create(
        intent_id=event["data"]["object"].get("id"),
        payload=event,
    )

    # ✅ Process successful payment
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        order_id = intent["metadata"].get("order_id")

        if not order_id:
            return HttpResponse(status=200)

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)

                # ✅ Idempotency check
                if order.status == Order.Status.PAID:
                    return HttpResponse(status=200)

                order.status = Order.Status.PAID
                order.save()

                payment, _ = Payment.objects.get_or_create(order=order)
                payment.status = Payment.Status.PAID
                payment.stripe_payment_intent = intent["id"]
                payment.amount = intent["amount"] / 100
                payment.save()

        except Order.DoesNotExist:
            return HttpResponse(status=200)

        # ✅ WebSocket notification
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            "pos_system",
            {
                "type": "send_pos_update",
                "data": {
                    "event": "order_paid",
                    "order_id": order_id,
                },
            },
        )

    return HttpResponse(status=200)