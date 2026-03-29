import os
from django.conf import settings

# Development printer file simulation
PRINTERS = {
    "bar": "bar_printer.txt",
    "kitchen": "kitchen_printer.txt",
    "drinks": "drinks_printer.txt",
    "pos": "receipt_printer.txt",
}


def send_to_printer(printer_name: str, content: str):
    """
    Send formatted text to a printer.

    In development: writes to a text file.
    In production: can be replaced with ESC/POS or network printing.
    """

    if printer_name not in PRINTERS:
        raise ValueError(f"Unknown printer: {printer_name}")

    file_name = PRINTERS[printer_name]

    # Store inside project directory (safe path)
    printer_path = os.path.join(settings.BASE_DIR, file_name)

    try:
        with open(printer_path, "a", encoding="utf-8") as f:
            f.write(content)
            f.write("\n")

    except Exception as e:
        raise Exception(f"Printer write failed: {e}")