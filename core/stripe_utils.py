import stripe
from django.conf import settings
from django.db import transaction

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(order):
    """
    Create a Stripe PaymentIntent safely.
    Uses idempotency key to prevent duplicates.
    """

    try:
        # ✅ total_price is a property now
        amount_cents = int(order.total_price * 100)

        # ✅ Deterministic idempotency key
        idempotency_key = f"order-{order.id}"

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=getattr(order.restaurant, "currency", "usd"),
            metadata={
                "order_id": str(order.id),
                "restaurant_id": str(order.restaurant.id),
            },
            automatic_payment_methods={"enabled": True},
            idempotency_key=idempotency_key,  # ✅ prevents duplicates
        )

        return intent

    except stripe.error.StripeError as e:
        # Log properly in production
        # logger.exception("Stripe PaymentIntent failed")
        raise Exception(f"Stripe error: {str(e)}")