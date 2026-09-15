# core/management/commands/update_payment_methods.py

from django.core.management.base import BaseCommand
from core.models import PaymentMethod

class Command(BaseCommand):
    help = 'Update payment method names'

    def handle(self, *args, **options):
        name_map = {
            "cash": ["cash", "Cash"],
            "card": ["card", "Card", "Credit_card"],
            "mobile": ["mobile", "Mobile", "Mobile pay", "Mobile pay"]
        }

        payment_methods = PaymentMethod.objects.all()
        for method in payment_methods:
            for standard_name, variations in name_map.items():
                if method.name.lower() in [v.lower() for v in variations]:
                    method.name = standard_name
                    method.save()
                    break

        self.stdout.write(self.style.SUCCESS('Payment method names updated successfully'))
