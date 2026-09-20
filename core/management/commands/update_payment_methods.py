from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from core.models import PaymentMethod


class Command(BaseCommand):
    help = "Normalize existing payment method names"

    STANDARD_NAMES = {
        "cash": "cash",
        "card": "card",
        "mobile": "mobile",
    }

    def normalize_name(self, value):
        if not value:
            return ""

        return (
            str(value)
            .strip()
            .lower()
            .replace("-", " ")
            .replace("_", " ")
        )

    def get_standard_name(self, value):
        name = self.normalize_name(value)

        if not name:
            return None

        if "cash" in name:
            return "cash"

        if (
            "card" in name
            or "credit" in name
            or "debit" in name
            or "visa" in name
            or "mastercard" in name
            or "master card" in name
        ):
            return "card"

        if (
            "mobile" in name
            or "momo" in name
            or "mtn" in name
            or "airtel" in name
            or "orange" in name
        ):
            return "mobile"

        return None

    @transaction.atomic
    def handle(self, *args, **options):
        updated_count = 0
        unchanged_count = 0
        unknown_count = 0
        duplicate_count = 0

        methods_by_restaurant_and_name = defaultdict(list)

        payment_methods = PaymentMethod.objects.all().order_by("id")

        for method in payment_methods:
            standard_name = self.get_standard_name(method.name)

            if not standard_name:
                unknown_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        "Unknown payment method: "
                        f"id={method.id}, "
                        f"restaurant_id={method.restaurant_id}, "
                        f"name={method.name!r}"
                    )
                )

                continue

            methods_by_restaurant_and_name[
                (method.restaurant_id, standard_name)
            ].append(method)

        for (
            restaurant_id,
            standard_name,
        ), methods in methods_by_restaurant_and_name.items():
            methods.sort(key=lambda item: item.id)

            keeper = methods[0]

            if len(methods) > 1:
                duplicate_count += len(methods) - 1

                self.stdout.write(
                    self.style.WARNING(
                        "Duplicate payment methods found for "
                        f"restaurant_id={restaurant_id}, "
                        f"name={standard_name!r}. "
                        f"Keeping id={keeper.id}."
                    )
                )

                for duplicate in methods[1:]:
                    self.stdout.write(
                        self.style.WARNING(
                            "Duplicate record: "
                            f"id={duplicate.id}, "
                            f"name={duplicate.name!r}"
                        )
                    )

                self.stdout.write(
                    self.style.WARNING(
                        "Orders using duplicate records must be reassigned "
                        "before those records are deleted."
                    )
                )

            old_name = keeper.name
            old_slug = keeper.slug

            new_slug = slugify(standard_name)

            if old_name != standard_name or old_slug != new_slug:
                keeper.name = standard_name
                keeper.slug = new_slug

                keeper.save(
                    update_fields=[
                        "name",
                        "slug",
                    ]
                )

                updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated payment method id={keeper.id}: "
                        f"{old_name!r} -> {standard_name!r}"
                    )
                )
            else:
                unchanged_count += 1

            for duplicate in methods[1:]:
                # Do not delete duplicates automatically.
                # Existing orders may still point to them.
                pass

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Payment method normalization completed."
            )
        )
        self.stdout.write(
            f"Updated: {updated_count} | "
            f"Unchanged: {unchanged_count} | "
            f"Unknown: {unknown_count} | "
            f"Duplicates: {duplicate_count}"
        )