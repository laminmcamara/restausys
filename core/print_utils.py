import os
PRINTERS = {
    "bar": "bar_printer.txt",
    "kitchen": "kitchen_printer.txt",
    "receipt": "receipt_printer.txt",
}

def send_to_printer(order, printer_path):
    """In development, just write to text file."""
    with open(printer_path, "a", encoding="utf-8") as f:
        f.write(f"\n=== ORDER #{order.id} ===\n")
        for oi in order.orderitem_set.all():
            f.write(f"{oi.quantity} x {oi.item.name}\n")
        f.write("===========================\n")