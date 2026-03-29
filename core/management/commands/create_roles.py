from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = "Create staff roles with permissions"

    def handle(self, *args, **kwargs):
        # Create groups
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        cashier_group, _ = Group.objects.get_or_create(name="Cashier")
        waiter_group, _ = Group.objects.get_or_create(name="Waiter")
        chef_group, _ = Group.objects.get_or_create(name="Chef")

        # Get permissions
        all_perms = Permission.objects.all()

        # Admin gets everything
        admin_group.permissions.set(all_perms)

        # Manager gets everything except system-level
        manager_group.permissions.set(
            all_perms.exclude(codename__startswith="delete_")
        )

        # Cashier permissions
        cashier_group.permissions.set(Permission.objects.filter(
            codename__in=[
                "view_order",
                "change_order",
                "view_table",
                "view_payment",
                "add_payment",
            ]
        ))

        # Waiter permissions
        waiter_group.permissions.set(Permission.objects.filter(
            codename__in=[
                "view_order",
                "add_order",
                "change_order",
                "view_menuitem",
                "view_table",
            ]
        ))

        # Chef permissions
        chef_group.permissions.set(Permission.objects.filter(
            codename__in=[
                "view_order",
                "change_order",
                "view_orderitem",
                "change_orderitem",
            ]
        ))

        self.stdout.write(self.style.SUCCESS("Role permissions assigned."))