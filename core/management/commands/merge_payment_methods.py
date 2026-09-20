from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Order, Payment, PaymentMethod


class Command(BaseCommand):
    help = (
        "Merge duplicate payment methods and reassign "
        "related orders and payments"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without modifying the database.",
        )

    def normalize_name(self, name):
        return " ".join(
            str(name or "")
            .strip()
            .lower()
            .replace("_", " ")
            .replace("-", " ")
            .split()
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: no database changes will be made."
                )
            )

        payment_methods = (
            PaymentMethod.objects
            .all()
            .order_by("restaurant_id", "id")
        )

        grouped_methods = defaultdict(list)

        for method in payment_methods:
            normalized_name = self.normalize_name(method.name)

            grouped_methods[
                (
                    method.restaurant_id,
                    normalized_name,
                )
            ].append(method)

        duplicate_groups = [
            methods
            for methods in grouped_methods.values()
            if len(methods) > 1
        ]

        if not duplicate_groups:
            self.stdout.write(
                self.style.SUCCESS(
                    "No duplicate payment methods found."
                )
            )
            return

        total_order_reassignments = 0
        total_payment_reassignments = 0
        total_deleted = 0

        for methods in duplicate_groups:
            methods.sort(key=lambda method: method.id)

            keeper = methods[0]
            duplicates = methods[1:]

            self.stdout.write("")
            self.stdout.write(
                f"Restaurant ID: {keeper.restaurant_id}"
            )
            self.stdout.write(
                f"Payment method: {keeper.name}"
            )
            self.stdout.write(
                f"Keeping ID: {keeper.id}"
            )

            for duplicate in duplicates:
                order_count = Order.objects.filter(
                    payment_method_id=duplicate.id
                ).count()

                payment_count = Payment.objects.filter(
                    method_id=duplicate.id
                ).count()

                self.stdout.write(
                    f"Merging ID {duplicate.id} "
                    f"({order_count} orders, "
                    f"{payment_count} payments)"
                )

                if dry_run:
                    continue

                updated_orders = (
                    Order.objects
                    .filter(payment_method_id=duplicate.id)
                    .update(payment_method_id=keeper.id)
                )

                updated_payments = (
                    Payment.objects
                    .filter(method_id=duplicate.id)
                    .update(method_id=keeper.id)
                )

                duplicate.delete()

                total_order_reassignments += updated_orders
                total_payment_reassignments += updated_payments
                total_deleted += 1

        if dry_run:
            transaction.set_rollback(True)

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN completed. No records were changed."
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Payment method merge completed."
            )
        )
        self.stdout.write(
            f"Orders reassigned: {total_order_reassignments}"
        )
        self.stdout.write(
            f"Payments reassigned: {total_payment_reassignments}"
        )
        self.stdout.write(
            f"Duplicate methods deleted: {total_deleted}"
        )