from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Order, Payment
from .stripe_utils import create_payment_intent


@api_view(["POST"])
def generate_qr_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    intent = create_payment_intent(order)

    pay_obj, _ = Payment.objects.update_or_create(
        order=order,
        defaults={
            "stripe_payment_intent": intent.id,
            "amount": order.total_price(),
        }
    )

    qr_url = f"http://localhost:8000/pay/{order.id}/"

    return Response({"qr_url": qr_url, "client_secret": intent.client_secret})