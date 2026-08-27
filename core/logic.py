from django.db import transaction
from .models import Order

def deduct_inventory_for_order(order):
    """
    Loops through all items in an order and subtracts 
    the required ingredients from the InventoryItem stock.
    """
    with transaction.atomic():
        for item in order.items.all():
            # Find ingredients linked to this menu item
            ingredients = item.menu_item.ingredients.all()
            
            for ingredient in ingredients:
                inv_item = ingredient.inventory_item
                # Subtract: Stock = Stock - (Quantity ordered * Quantity per item)
                reduction = item.quantity * ingredient.quantity_needed
                inv_item.quantity -= reduction
                inv_item.save()