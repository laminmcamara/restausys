from django.core.management.base import BaseCommand
from core.models import Location, Restaurant, Table, User, Profile, MenuItem, MenuVariant, Order, OrderItem, KitchenTicket, Payment
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Seed the database with initial data'

    def handle(self, *args, **kwargs):
        # Create a location
        location = Location.objects.create(address="MONG KOK LADIES MARKET OTTOMAN HALAL RESTO HK")

        # Create a restaurant
        restaurant = Restaurant.objects.create(name="Sample Restaurant", location=location)

        # Create tables
        for i in range(1, 6):
            table = Table.objects.create(restaurant=restaurant, table_number=i, capacity=4, status='available', coordinates={'x': random.randint(1, 100), 'y': random.randint(1, 100)})
            print(f"Creating Table: restaurant={restaurant}, table_number={i}, capacity=4, status='available'")

        # Create staff
        users = [
            User.objects.create_user(username='manager', password='password'),
            User.objects.create_user(username='server1', password='password'),
            User.objects.create_user(username='server2', password='password'),
        ]
        for user in users:
            Profile.objects.create(user=user, role='server')

        # Create menu items
        menu_items = [
            MenuItem.objects.create(restaurant=restaurant, name='Burger', category='main', base_price=9.99, description='A delicious beef burger.'),
            MenuItem.objects.create(restaurant=restaurant, name='Pizza', category='main', base_price=12.99, description='Cheesy pizza with fresh toppings.'),
            MenuItem.objects.create(restaurant=restaurant, name='Fries', category='appetizer', base_price=3.99, description='Crispy fries.'),
        ]

        # Create menu variants
        for item in menu_items:
            MenuVariant.objects.create(menu_item=item, name='Large', price_modifier=1.50, stock=100)
            MenuVariant.objects.create(menu_item=item, name='Extra Cheese', price_modifier=2.00, stock=50)

        # Simulate daily cycles of orders
        for _ in range(10):  # Simulate 10 orders
            table = random.choice(Table.objects.filter(status='available'))
            order = Order.objects.create(table=table)

            # Create order items
            order_items = []
            for _ in range(random.randint(1, 3)):  # Random number of items per order
                menu_item = random.choice(menu_items)
                quantity = random.randint(1, 3)
                print(f"Creating OrderItem: order={order.id}, menu_item={menu_item.id}, quantity={quantity}")
                order_item = OrderItem.objects.create(order=order, menu_item=menu_item, quantity=quantity)
                order_items.append(order_item)

            # Create kitchen tickets for each order item
            for order_item in order_items:
                due_at = datetime.now() + timedelta(minutes=random.randint(5, 30))
                print(f"Creating KitchenTicket for OrderItem {order_item.id} with due_at {due_at}")
                KitchenTicket.objects.create(order_item=order_item, station='Kitchen', due_at=due_at)

            # Process payment
            amount = sum(item.menu_item.base_price * item.quantity for item in order_items) + random.uniform(0, 10)  # Add some random additional cost
            Payment.objects.create(order=order, amount=amount, method=random.choice(['credit_card', 'cash']), status=random.choice(['success', 'failed']))

            # Update table status
            table.status = 'occupied'
            table.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded the database with realistic data'))