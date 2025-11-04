from django.db import models

class Table(models.Model):
    table_number = models.IntegerField(unique=True)  # Unique identifier for the table
    seats = models.IntegerField(default=2)  # Number of seats at the table
    is_available = models.BooleanField(default=True)  # Availability status of the table
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for when the table was created
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for when the table was last updated

    def __str__(self):
        return f"Table {self.table_number} (Seats: {self.seats})"
