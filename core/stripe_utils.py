# core/stripe_utils.py

import stripe
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum
from django.views.decorators.http import require_POST

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(order):
    """
    Create a Stripe PaymentIntent safely.
    - Charges only remaining balance
    - Supports partial payments
    - Prevents duplicate charges
    - Safe for retries
    """

    # ✅ Recalculate total paid (only successful payments)
    total_paid = (
        order.payments
        .filter(status="SUCCEEDED")
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    remaining = order.total - total_paid

    if remaining <= 0:
        raise ValueError("Order is already fully paid.")

    amount_cents = int(remaining * 100)

    # ✅ Idempotency key must match exact amount
    idempotency_key = f"order-{order.id}-amount-{amount_cents}"

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=getattr(order.restaurant, "currency", "usd"),
            metadata={
                "order_id": str(order.id),
                "restaurant_id": str(order.restaurant.id),
                "session_id": str(order.session.id) if order.session else "",
            },
            automatic_payment_methods={"enabled": True},
            idempotency_key=idempotency_key,
        )

        return intent

    except stripe.error.StripeError as e:
        # ✅ In production use logging instead
        raise Exception(f"Stripe error: {str(e)}")