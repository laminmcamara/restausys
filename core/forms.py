from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Shift, Order, OrderItem, InventoryItem


# ==============================================================================
# Utility: Base Styled Form (Tailwind Friendly)
# ==============================================================================

class StyledModelForm(forms.ModelForm):
    """
    Base form that automatically applies Tailwind styling
    to all fields.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            })


# ==============================================================================
# Custom User Forms
# ==============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating new users with role selection.
    """

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name", "role")


class CustomUserChangeForm(UserChangeForm):
    """
    Form for updating users in admin.
    """

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
        )


# ==============================================================================
# Shift Management Form
# ==============================================================================

class ShiftForm(StyledModelForm):
    """
    Form for creating and updating employee shifts.
    """

    class Meta:
        model = Shift
        fields = ['employee', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


# ==============================================================================
# Order and OrderItem Forms
# ==============================================================================

class OrderForm(StyledModelForm):
    """
    Form for creating or updating an order.
    """

    class Meta:
        model = Order
        fields = ['table', 'status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class OrderItemForm(StyledModelForm):
    """
    Form for adding/editing an item inside an order.
    """

    class Meta:
        model = OrderItem
        fields = ["menu_item", "variant", "quantity", "notes"]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


# ==============================================================================
# Inventory Management Form
# ==============================================================================

class InventoryItemForm(StyledModelForm):
    """
    Form for managing inventory items.
    """

    class Meta:
        model = InventoryItem
        fields = ['name', 'quantity', 'unit', 'low_stock_threshold']