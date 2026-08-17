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