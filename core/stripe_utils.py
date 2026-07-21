# core/stripe_utils.py

import stripe
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(order):
    """
    Create a Stripe PaymentIntent safely.
    - Charges only remaining balance
    - Supports partial payments
    - Prevents duplicate charges
    """

    try:
        # ✅ Calculate how much has already been paid
        total_paid = order.payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        remaining = order.total_price - total_paid

        if remaining <= 0:
            raise ValueError("Order is already fully paid.")

        amount_cents = int(remaining * 100)

        # ✅ Idempotency key must match exact amount attempt
        idempotency_key = f"order-{order.id}-remaining-{amount_cents}"

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=getattr(order.restaurant, "currency", "usd"),
            metadata={
                "order_id": str(order.id),
                "restaurant_id": str(order.restaurant.id),
                "session_id": str(order.session.id),
            },
            automatic_payment_methods={"enabled": True},
            idempotency_key=idempotency_key,
        )

        return intent

    except stripe.error.StripeError as e:
        # In production, use proper logging
        raise Exception(f"Stripe error: {str(e)}")
    