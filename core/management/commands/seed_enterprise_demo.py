from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import random

from core.models import (
    Company,
    Restaurant,
    Settings,
    Menu,
    Category,
    Product,
    Table,
    Order,
    OrderItem,
    Payment,
    CashierShift,
)


class Command(BaseCommand):
    help = "Seeds fully aligned enterprise demo dataset."

    def handle(self, *args, **kwargs):
        User = get_user_model()
        PASSWORD = "Ent3rprise!Demo#2026"

        self.stdout.write(self.style.WARNING("🚀 Building enterprise dataset..."))

        # =====================================================
        # COMPANY
        # =====================================================
        company, _ = Company.objects.get_or_create(
            name="Enterprise Demo Company"
        )

        # =====================================================
        # RESTAURANT
        # =====================================================
        restaurant, _ = Restaurant.objects.get_or_create(
            company=company,
            name="Enterprise Demo Restaurant",
            defaults={
                "address_line_1": "123 Demo Street",
                "city": "New York",
                "country": "USA",
            }
        )

        # =====================================================
        # SETTINGS
        # =====================================================
        Settings.objects.get_or_create(
            restaurant=restaurant,
            defaults={
                "restaurant_display_name": restaurant.name,
                "tax_percentage": Decimal("8.00"),
                "service_charge_percentage": Decimal("5.00"),
            }
        )

        # =====================================================
        # USERS
        # =====================================================
        roles = [
            ("manager1", User.Roles.MANAGER),
            ("cashier1", User.Roles.CASHIER),
            ("server1", User.Roles.SERVER),
            ("cook1", User.Roles.COOK),
        ]

        created_users = {}

        for username, role in roles:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@demo.com",
                    "restaurant": restaurant,
                    "role": role,
                },
            )
            user.set_password(PASSWORD)
            user.save()
            created_users[role] = user

        # =====================================================
        # CASHIER SHIFT (ACTIVE)
        # =====================================================
        cashier = created_users[User.Roles.CASHIER]

        shift, _ = CashierShift.objects.get_or_create(
            user=cashier,
            restaurant=restaurant,
            is_active=True,
            defaults={
                "starting_cash": Decimal("300.00")
            }
        )

        # =====================================================
        # TABLES
        # =====================================================
        tables = []
        for i in range(1, 6):
            table, _ = Table.objects.get_or_create(
                restaurant=restaurant,
                table_number=str(i)
            )
            tables.append(table)

        # =====================================================
        # MENU STRUCTURE
        # =====================================================
        menu, _ = Menu.objects.get_or_create(
            restaurant=restaurant,
            name="Main Menu"
        )

        mains_category, _ = Category.objects.get_or_create(
            menu=menu,
            name="Main Dishes"
        )

        drinks_category, _ = Category.objects.get_or_create(
            menu=menu,
            name="Drinks"
        )

        # =====================================================
        # PRODUCTS
        # =====================================================
        products_data = [
            ("Burger", Decimal("15.00"), mains_category),
            ("Pizza", Decimal("20.00"), mains_category),
            ("Pasta", Decimal("18.00"), mains_category),
            ("Cola", Decimal("5.00"), drinks_category),
            ("Coffee", Decimal("4.00"), drinks_category),
        ]

        products = []

        for name, price, category in products_data:
            product, _ = Product.objects.get_or_create(
                category=category,
                name=name,
                defaults={"base_price": price}
            )
            products.append(product)

        # =====================================================
        # GENERATE ORDERS + PAYMENTS (LINKED TO SHIFT)
        # =====================================================
        total_orders = 40

        for _ in range(total_orders):

            table = random.choice(tables)

            order = Order.create_for_table(
                restaurant=restaurant,
                table=table,
                order_type=Order.OrderType.DINE_IN,
                status=Order.Status.IN_PROGRESS,
            )

            # Add random items
            for _ in range(random.randint(1, 4)):
                product = random.choice(products)
                quantity = random.randint(1, 3)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity
                )

            # Calculate totals
            order.tax = order.subtotal * Decimal("0.08")
            order.service_charge = order.subtotal * Decimal("0.05")
            order.calculate_totals()

            order.status = Order.Status.COMPLETED
            order.payment_status = Order.PaymentStatus.PAID
            order.save()

            # ✅ LINK PAYMENT TO SHIFT
            Payment.objects.create(
                order=order,
                shift=shift,
                method=random.choice(["cash", "card"]),
                amount=order.total,
                status=Payment.Status.PAID,
                reference=f"ENT-{random.randint(1000,9999)}"
            )

        # =====================================================
        # CLOSE SHIFT (REAL CALCULATION)
        # =====================================================

        payments = shift.payments.filter(status=Payment.Status.PAID)

        total_sales = payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        total_cash = payments.filter(
            method="cash"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        total_card = total_sales - total_cash

        shift.total_sales = total_sales
        shift.total_cash_sales = total_cash
        shift.total_card_sales = total_card
        shift.closing_cash = shift.starting_cash + total_cash
        shift.cash_difference = Decimal("0.00")

        shift.is_active = False
        shift.end_time = timezone.now()
        shift.save()

        self.stdout.write(self.style.SUCCESS("✅ Enterprise dataset ready"))
        self.stdout.write(self.style.WARNING(f"\n🔐 Password: {PASSWORD}\n"))