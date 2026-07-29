import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction

from .models import Order, Payment, PaymentIntentLog
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import Subscription

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
            
     # ===============================
    # ✅ CHECKOUT SESSION COMPLETED (Subscription Created)
    # ===============================
    elif event["type"] == "checkout.session.completed":

        session = intent_data

        if session.get("mode") == "subscription":

            stripe_sub_id = session.get("subscription")
            stripe_customer_id = session.get("customer")

            metadata = session.get("metadata", {})
            restaurant_id = metadata.get("restaurant_id")
            plan_id = metadata.get("plan_id")

            if not stripe_sub_id or not restaurant_id or not plan_id:
                return HttpResponse(status=200)

            try:
                from core.models import Restaurant, Plan

                restaurant = Restaurant.objects.get(id=restaurant_id)
                plan = Plan.objects.get(id=plan_id)

                # ✅ Retrieve full subscription from Stripe
                stripe_subscription = stripe.Subscription.retrieve(
                    stripe_sub_id
                )

                Subscription.objects.update_or_create(
                    restaurant=restaurant,
                    defaults={
                        "plan": plan,
                        "stripe_subscription_id": stripe_sub_id,
                        "stripe_customer_id": stripe_customer_id,
                        "status": stripe_subscription.get("status"),  # trialing
                        "current_period_start": timezone.datetime.fromtimestamp(
                            stripe_subscription.get("current_period_start"),
                            tz=timezone.utc
                        ),
                        "current_period_end": timezone.datetime.fromtimestamp(
                            stripe_subscription.get("current_period_end"),
                            tz=timezone.utc
                        ),
                        "cancel_at_period_end": stripe_subscription.get(
                            "cancel_at_period_end"
                        ),
                    },
                )

            except Exception:
                pass       
    
    # ===============================
    # ✅ SUBSCRIPTION UPDATED
    # ===============================
    elif event["type"] == "customer.subscription.updated":

        sub = intent_data
        stripe_sub_id = sub.get("id")

        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub_id
            )

            subscription.status = sub.get("status")
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                sub.get("current_period_start"),
                tz=timezone.utc
            )
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                sub.get("current_period_end"),
                tz=timezone.utc
            )
            subscription.cancel_at_period_end = sub.get("cancel_at_period_end")

            subscription.save()

        except Subscription.DoesNotExist:
            pass


    # ===============================
    # ✅ SUBSCRIPTION CANCELED
    # ===============================
    elif event["type"] == "customer.subscription.deleted":

        sub = intent_data
        stripe_sub_id = sub.get("id")

        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub_id
            )
            subscription.status = "canceled"
            subscription.save(update_fields=["status"])

        except Subscription.DoesNotExist:
            pass
    return HttpResponse(status=200)