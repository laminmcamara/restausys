import os
from django.conf import settings


# Development printer file simulation
PRINTERS = {
    "bar": "bar_printer.txt",
    "kitchen": "kitchen_printer.txt",
    "drinks": "drinks_printer.txt",
    "pos": "receipt_printer.txt",
    "cashier": "receipt_printer.txt",
    "receipt": "receipt_printer.txt",
}


def send_to_printer(printer_name: str, content: str):
    """
    Send formatted text to a printer.

    In development:
        Writes to a text file inside BASE_DIR.

    In production:
        Replace this with ESC/POS, network socket printing,
        Windows printer spooler, or cloud printer integration.
    """

    if not printer_name:
        raise ValueError("Printer name is required.")

    printer_name = printer_name.lower().strip()

    if printer_name not in PRINTERS:
        raise ValueError(f"Unknown printer: {printer_name}")

    file_name = PRINTERS[printer_name]
    printer_path = os.path.join(settings.BASE_DIR, file_name)

    try:
        with open(printer_path, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write("=" * 40)
            f.write("\n")
            f.write(content)
            f.write("\n")
            f.write("=" * 40)
            f.write("\n")

    except Exception as e:
        raise Exception(f"Printer write failed: {e}")
    

def build_kitchen_ticket_text(order):
    """Formats the order for the kitchen display/printer"""
    lines = []
    lines.append("KITCHEN ORDER")
    lines.append("=" * 32)
    
    short_id = str(order.id).split('-')[-1][-4:].upper()
    lines.append(f"Order: #{short_id}")
    
    table_name = "Takeout"
    if order.table:
        table_name = getattr(order.table, 'table_number', str(order.table))
    lines.append(f"Table: {table_name}")
    
    lines.append(f"Time: {order.created_at.strftime('%H:%M:%S')}")
    lines.append("-" * 32)

    # Get items (handle different related names if necessary)
    items = order.items.all()
    for item in items:
        qty = item.quantity
        # Use product_name if available, otherwise product.name
        name = getattr(item, 'product_name', None) or (item.product.name if item.product else "Item")
        lines.append(f"{qty}x {name}")
        
        if item.notes:
            lines.append(f"  * NOTE: {item.notes}")
        
        if hasattr(item, 'modifiers') and item.modifiers.exists():
            for mod in item.modifiers.all():
                lines.append(f"    + {mod.name}")

    lines.append("-" * 32)
    lines.append("\n")
    return "\n".join(lines)

def build_receipt_text(order):
    """Formats the order for the customer receipt"""
    lines = []
    lines.append(getattr(order.restaurant, 'name', 'BEEPOS').upper())
    lines.append("RECEIPT")
    lines.append("=" * 32)
    lines.append(f"Order: #{str(order.id)[-4:].upper()}")
    lines.append(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("-" * 32)
    
    for item in order.items.all():
        name = getattr(item, 'product_name', None) or (item.product.name if item.product else "Item")
        price = float(item.final_price)
        lines.append(f"{item.quantity}x {name[:18]:<18} ${price * item.quantity:>7.2f}")
    
    lines.append("-" * 32)
    total = float(getattr(order, 'total_price', getattr(order, 'total_amount', 0)))
    lines.append(f"TOTAL: {' ' * 16} ${total:>7.2f}")
    lines.append("=" * 32)
    lines.append("THANK YOU FOR VISITING!")
    return "\n".join(lines)