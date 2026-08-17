from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import PrintJob
from core.print_utils import send_to_printer


class Command(BaseCommand):
    help = "Process pending print jobs and send them to printers."

    def handle(self, *args, **options):
        jobs = PrintJob.objects.filter(
            status=PrintJob.PrintJobStatus.PENDING
        ).select_related(
            "printer",
            "restaurant"
        ).order_by("created_at")

        if not jobs.exists():
            self.stdout.write(self.style.WARNING("No pending print jobs."))
            return

        for job in jobs:
            try:
                printer_name = self.get_printer_name(job)

                send_to_printer(
                    printer_name=printer_name,
                    content=job.raw_text
                )

                job.status = PrintJob.PrintJobStatus.PRINTED

                if hasattr(job, "printed_at"):
                    job.printed_at = timezone.now()

                job.save(update_fields=["status", "printed_at"] if hasattr(job, "printed_at") else ["status"])

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Printed job #{job.id} to {printer_name}"
                    )
                )

            except Exception as e:
                job.status = PrintJob.PrintJobStatus.FAILED

                if hasattr(job, "error_message"):
                    job.error_message = str(e)
                    job.save(update_fields=["status", "error_message"])
                else:
                    job.save(update_fields=["status"])

                self.stdout.write(
                    self.style.ERROR(
                        f"Failed job #{job.id}: {e}"
                    )
                )

    def get_printer_name(self, job):
        """
        Map database printer role/job type to print_utils printer key.
        """

        if job.printer:
            role = getattr(job.printer, "role", "").lower()

            if role == "kitchen":
                return "kitchen"

            if role == "cashier":
                return "receipt"

        job_type = getattr(job, "job_type", "").upper()

        if job_type in ["KITCHEN_ORDER", "KITCHEN"]:
            return "kitchen"

        if job_type in ["RECEIPT", "BILL"]:
            return "receipt"

        return "pos"kitchen_printer.txt
receipt_printer.txt