
# Restaurant Management System

## Table of Contents
- [Restaurant Management System](#restaurant-management-system)
  - [Table of Contents](#table-of-contents)
  - [Project Overview](#project-overview)
  - [Features](#features)
  - [Technologies Used](#technologies-used)
  - [Installation](#installation)
- [🛠️ Fixing the Django Admin “Access Denied” Issue](#️-fixing-the-django-admin-access-denied-issue)
  - [Overview](#overview)
  - [⚠️ Problem Summary](#️-problem-summary)
    - [1. Cause](#1-cause)
- [🛠️ Fixing the Django Admin “Access Denied” Issue](#️-fixing-the-django-admin-access-denied-issue-1)
  - [Overview](#overview-1)
  - [⚠️ Problem Summary](#️-problem-summary-1)
    - [1. Cause](#1-cause-1)

## Project Overview
The Restaurant Management System is a web application designed to help restaurant managers and staff manage their operations effectively. It includes features for managing users, orders, menu items, tables, and sales data.

## Features
- User authentication and role management (managers, kitchen staff, servers, etc.)
- Profile management for users
- Restaurant and table management
- Menu item management with variants
- Order management including kitchen tickets and payment processing
- Sales data tracking for reporting

## Technologies Used
- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL (or any other database supported by Django)
- **Frontend**: HTML, CSS, JavaScript (if applicable)
- **Others**: Git, Docker (optional for containerization)

## Installation
To set up the project locally, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/restaurant-management-system.git
   cd restaurant-management-system

Create a virtual environment:

Copy
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
Install dependencies:

Copy
pip install -r requirements.txt
Set up the database:

Configure your database settings in settings.py.
Run migrations:
Copy
python manage.py migrate
Create a superuser (for admin access):

Copy
python manage.py createsuperuser
Run the development server:

Copy
python manage.py runserver
Access the application:
Open your web browser and navigate to http://127.0.0.1:8000.

Usage
Admin Panel: Access the admin panel at http://127.0.0.1:8000/admin to manage users, profiles, and other entities.
API Endpoints: Use the provided API endpoints for integrating with frontend applications or for testing.
API Endpoints
User Management
Create User: POST /api/users/
Retrieve User: GET /api/users/{id}/
Update User: PUT /api/users/{id}/
Delete User: DELETE /api/users/{id}/
Profile Management
Create Profile: POST /api/profiles/
Retrieve Profile: GET /api/profiles/{id}/
Update Profile: PUT /api/profiles/{id}/
Delete Profile: DELETE /api/profiles/{id}/
Restaurant Management
Create Restaurant: POST /api/restaurants/
Retrieve Restaurant: GET /api/restaurants/{id}/
Update Restaurant: PUT /api/restaurants/{id}/
Delete Restaurant: DELETE /api/restaurants/{id}/
Order Management
Create Order: POST /api/orders/
Retrieve Order: GET /api/orders/{id}/
Update Order: PUT /api/orders/{id}/
Delete Order: DELETE /api/orders/{id}/
Sales Data
Retrieve Sales Data: GET /api/salesdata/
Models
CustomUser
Inherits from AbstractUser.
Fields: is_manager, is_staff, is_kitchen_staff, etc.
Profile
User profile details.
Fields: user, name, email, role, shift_start, shift_end, attendance_date, attendance_status.
Location
Represents the location of a restaurant.
Fields: address.
Restaurant
Represents a restaurant entity.
Fields: name, location, address, phone_number.
Table
Represents tables in a restaurant.
Fields: restaurant, table_number, capacity, status, coordinates.
MenuItem
Represents menu items.
Fields: restaurant, name, category, base_price, is_active, description.
Order
Represents customer orders.
Fields: table, created_at, status.
OrderItem
Represents items within an order.
Fields: order, menu_item, quantity, status, timestamp.
KitchenTicket
Represents kitchen tickets for order items.
Fields: order_item, station, status, priority, due_at.
Payment
Represents payment details for orders.
Fields: order, amount, method, status, gateway_ref, paid_at.
QRToken
Represents QR tokens associated with orders or tables.
Fields: token, order, table.
ScreenDisplay
Represents content for screen displays.
Fields: content, configuration.
SalesData
Represents sales data for reporting.
Fields: month, amount, date.
Serializers
ProfileSerializer
Serializes the Profile model.
Includes nested serialization for CustomUser.
Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.
Create a new branch (git checkout -b feature/YourFeature).
Make your changes and commit them (git commit -m 'Add some feature').
Push to the branch (git push origin feature/YourFeature).
Open a Pull Request.
License
This project is licensed under the MIT License - see the LICENSE file for details.



# 🛠️ Fixing the Django Admin “Access Denied” Issue

## Overview

After introducing a customized `CustomUser` model to handle multiple staff roles (manager, server, cook, cashier, etc.), the Django Admin login began rejecting even valid **superuser** credentials with the error:

> **“Access denied”**

This README describes **why** that happened, and the exact **fix** that resolved it.

---

## ⚠️ Problem Summary

### 1. Cause

In the original `CustomUser` model, the `save()` method automatically overwrote the `is_staff` flag based on the user’s role:

```python
def save(self, *args, **kwargs):
    self.is_staff = self.role in [self.Roles.MANAGER, self.Roles.SERVER, self.Roles.CASHIER]
    super().save(*args, **kwargs)





    markdown

# 🛠️ Fixing the Django Admin “Access Denied” Issue

## Overview

After introducing a customized `CustomUser` model to handle multiple staff roles (manager, server, cook, cashier, etc.), the Django Admin login began rejecting even valid **superuser** credentials with the error:

> **“Access denied”**

This README describes **why** that happened, and the exact **fix** that resolved it.

---

## ⚠️ Problem Summary

### 1. Cause

In the original `CustomUser` model, the `save()` method automatically overwrote the `is_staff` flag based on the user’s role:

```python
def save(self, *args, **kwargs):
    self.is_staff = self.role in [self.Roles.MANAGER, self.Roles.SERVER, self.Roles.CASHIER]
    super().save(*args, **kwargs)
That means:

Situation	Result
Superuser created via createsuperuser	is_staff=True initially
Any subsequent save (even automatically)	is_staff reset to False (if role not in the list)
Admin login check	Fails because user.is_staff is now False
So, even true superusers could not pass Django’s internal check:

python

Run

if user.is_active and user.is_staff:
Hence, no access to /admin/.

🧠 Root Cause
The save() method unintentionally overrode the is_staff flag for all users, including superusers.

This broke the logic Django uses for admin permission checks.

✅ The Solution
Modify the save() method to:

Only apply automatic is_staff logic for non–superusers.
Allow Django’s built‑in superuser privileges to remain untouched.
✅ Fixed code:
python

Run

def save(self, *args, **kwargs):
    # Only auto-set is_staff for non-superusers
    if not self.is_superuser:
        self.is_staff = self.role in [
            self.Roles.MANAGER, self.Roles.SERVER, self.Roles.CASHIER
        ]
    super().save(*args, **kwargs)
This ensures:

Superusers keep both is_superuser=True and is_staff=True.
Role-based staff (e.g., Manager, Cashier) automatically get admin access.
Regular users remain non-staff safely.
🧩 How to Apply the Fix
Open your models.py file.
Locate your CustomUser model.
Replace its save() method with the one shown above.
Re-run migrations (none likely needed):
bash

python manage.py makemigrations
python manage.py migrate
Re-save or recreate your superuser:
bash

python manage.py shell
>>> from core.models import CustomUser
>>> u = CustomUser.objects.get(username='admin')
>>> u.is_staff = True
>>> u.is_superuser = True
>>> u.save()
Log in again at:
👉 http://127.0.0.1:8000/admin/
You should now successfully access the Django Admin panel.

🧾 Verification Steps
Check	Expected
Admin login URL	✅ Works again
Superuser flags in database	✅ is_staff=True, is_superuser=True
Role-based staff (e.g., Manager)	✅ is_staff=True automatically
Non-staff employees (Cook, etc.)	✅ is_staff=False
🔒 Additional Notes
Keep is_staff and is_superuser consistent. Django relies on these fields for admin permission checks.
Avoid overriding them in save() unless protecting superusers.
If you use signals (e.g., post_save), ensure they also respect this logic.
