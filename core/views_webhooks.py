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

    intent_data = event.get("data", {}).get("object", {})

    # ✅ Log webhook event
    PaymentIntentLog.objects.create(
        intent_id=intent_data.get("id"),
        payload=event,
    )

    # ===============================
    # ✅ PAYMENT SUCCEEDED
    # ===============================
    if event["type"] == "payment_intent.succeeded":

        intent = intent_data
        order_id = intent.get("metadata", {}).get("order_id")
        restaurant_id = intent.get("metadata", {}).get("restaurant_id")

        if not order_id or not restaurant_id:
            return HttpResponse(status=200)

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)

                # ✅ Multi-tenant check
                if str(order.restaurant.id) != str(restaurant_id):
                    return HttpResponse(status=400)

                # ✅ Idempotency
                if order.payment_status == Order.PaymentStatus.PAID:
                    return HttpResponse(status=200)

                # ✅ Amount validation
                expected_amount = int(order.total * 100)
                if intent["amount"] != expected_amount:
                    return HttpResponse(status=400)

                # ✅ Update order
                order.payment_status = Order.PaymentStatus.PAID
                order.save(update_fields=["payment_status"])

                order.mark_as_placed()

                # ✅ Update payment record
                payment, _ = Payment.objects.get_or_create(order=order)
                payment.status = Payment.Status.PAID
                payment.stripe_payment_intent = intent["id"]
                payment.amount = intent["amount"] / 100
                payment.save()

        except Order.DoesNotExist:
            return HttpResponse(status=200)

        # ✅ WebSocket notify
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            "pos_system",
            {
                "type": "send_pos_update",
                "data": {
                    "event": "order_paid",
                    "order_id": str(order_id),
                },
            },
        )

    # ===============================
    # ✅ PAYMENT FAILED
    # ===============================
    elif event["type"] == "payment_intent.payment_failed":

        intent = intent_data
        order_id = intent.get("metadata", {}).get("order_id")

        if order_id:
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)

                    if order.payment_status != Order.PaymentStatus.PAID:
                        order.payment_status = Order.PaymentStatus.FAILED
                        order.save(update_fields=["payment_status"])

            except Order.DoesNotExist:
                pass

    return HttpResponse(status=200)