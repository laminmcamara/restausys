from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Profile, Order

User = get_user_model()

class DashboardTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='password123',
            is_manager=True
        )
        self.client.login(username='manager', password='password123')

    def test_manager_dashboard_access(self):
        response = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'manager_dashboard.html')

    def test_manager_dashboard_data(self):
        # Mock data for testing
        # Assuming sales_data, inventory_levels, and staff_performance are context variables
        response = self.client.get(reverse('manager_dashboard'))
        self.assertContains(response, 'Sales')  # Check if the sales data is present
        self.assertContains(response, 'Inventory')  # Check if inventory levels are present

class KitchenDisplayTests(TestCase):
    def setUp(self):
        self.kitchen_staff = User.objects.create_user(
            username='kitchen',
            password='password123',
            is_kitchen_staff=True
        )
        self.client.login(username='kitchen', password='password123')

    def test_kitchen_display_access(self):
        response = self.client.get(reverse('kitchen_display'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kitchen_display.html')

    def test_kitchen_display_orders(self):
        # Create a sample order
        order = Order.objects.create(
            status='in_kitchen'
        )
        response = self.client.get(reverse('kitchen_display'))
        self.assertContains(response, order.id)

class ProfileAttendanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='staff',
            password='password123'
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='staff', password='password123')

    def test_clock_in(self):
        response = self.client.post(reverse('clock_in'))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.attendance_status)
        self.assertRedirects(response, reverse('dashboard'))

    def test_clock_out(self):
        # First clock in
        self.profile.attendance_status = True
        self.profile.save()
        
        response = self.client.post(reverse('clock_out'))
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.attendance_status)
        self.assertRedirects(response, reverse('dashboard'))

    def test_manage_shifts_access(self):
        response = self.client.get(reverse('manage_shifts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'manage_shifts.html')

class PayrollTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='payroll_manager',
            password='password123',
            is_manager=True
        )
        self.client.login(username='payroll_manager', password='password123')
        
        # Create profiles for payroll calculation
        self.staff_user = User.objects.create_user(username='staff1', password='password123')
        self.staff_profile = Profile.objects.create(user=self.staff_user, attendance_status=True)

    def test_payroll_calculation(self):
        # Implement logic to test payroll calculation
        # This is a placeholder for actual payroll calculation logic
        # You can assert expected values based on your payroll calculation method
        self.assertIsNotNone(self.staff_profile)  # Ensure staff profile exists

# Add more tests as needed for your application
