from core.models import Printer, PrintJob


def get_target_printer_role(job_type):
    job_type = job_type.upper()

    if job_type in [
        PrintJob.PrintJobType.KITCHEN_ORDER,
        "KITCHEN",
        "KITCHEN_ORDER",
    ]:
        return Printer.PrinterRole.KITCHEN

    if job_type in [
        PrintJob.PrintJobType.RECEIPT,
        "RECEIPT",
        "BILL",
    ]:
        return Printer.PrinterRole.CASHIER

    return None


def get_default_printer(restaurant, job_type):
    target_role = get_target_printer_role(job_type)

    if not restaurant or not target_role:
        return None

    return Printer.objects.filter(
        restaurant=restaurant,
        role=target_role,
        is_active=True,
    ).first()


def build_kitchen_ticket_text(order):
    lines = []

    lines.append("KITCHEN ORDER")
    lines.append("=" * 32)
    lines.append(f"Order #{order.id}")

    table = getattr(order, "table", None)
    if table:
        table_name = getattr(table, "name", None) or getattr(table, "number", None) or str(table)
        lines.append(f"Table: {table_name}")

    created_by = getattr(order, "created_by", None)
    if created_by:
        full_name = created_by.get_full_name()
        server_name = full_name or created_by.username
        lines.append(f"Server: {server_name}")

    lines.append("-" * 32)

    if hasattr(order, "items"):
        order_items = order.items.all()
    elif hasattr(order, "order_items"):
        order_items = order.order_items.all()
    else:
        order_items = []

    for item in order_items:
        quantity = getattr(item, "quantity", 1)

        menu_item = (
            getattr(item, "menu_item", None)
            or getattr(item, "product", None)
            or getattr(item, "item", None)
        )

        item_name = (
            getattr(menu_item, "name", None)
            or getattr(item, "name", None)
            or "Item"
        )

        lines.append(f"{quantity}x {item_name}")

        notes = (
            getattr(item, "notes", "")
            or getattr(item, "special_instructions", "")
            or getattr(item, "comment", "")
        )

        if notes:
            lines.append(f"  Note: {notes}")

    lines.append("-" * 32)
    lines.append("")

    return "\n".join(lines)


def create_kitchen_print_job(order):
    order_id = str(order.id)
    table_id = str(order.table_id) if getattr(order, "table_id", None) else None

    existing_job = PrintJob.objects.filter(
        restaurant=order.restaurant,
        job_type=PrintJob.PrintJobType.KITCHEN_ORDER,
        payload__order_id=order_id,
    ).exclude(
        status=PrintJob.PrintJobStatus.CANCELLED
    ).first()

    if existing_job:
        return existing_job

    return PrintJob.objects.create(
        restaurant=order.restaurant,
        job_type=PrintJob.PrintJobType.KITCHEN_ORDER,
        title=f"Kitchen Ticket #{order_id}",
        raw_text=build_kitchen_ticket_text(order),
        payload={
            "order_id": order_id,
            "order_number": getattr(order, "order_number", None),
            "table_id": table_id,
        },
    )