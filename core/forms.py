from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Shift, CustomUser, OrderItem, InventoryItem, Restaurant, Order, MenuItem, Table


# ==============================================================================
# SHIFT FORM
# ==============================================================================
class ShiftForm(forms.ModelForm):
    """Form for creating or updating work shifts."""
    class Meta:
        model = Shift
        fields = ["employee", "restaurant", 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }


# ==============================================================================
# USER FORMS
# ==============================================================================
class CustomUserCreationForm(UserCreationForm):
    """Extended registration form with additional custom fields."""
    phone_number = forms.CharField(max_length=17, required=False, label="Phone number")
    passport_id_card_number = forms.CharField(max_length=50, required=False, label="Passport/ID")

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'role', 'avatar', 'phone_number', 'passport_id_card_number'
        )


class CustomUserChangeForm(UserChangeForm):
    """Form for editing existing user profiles (admin & self-service)."""
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'email',
            'role', 'avatar', 'phone_number', 'passport_id_card_number'
        )


# ==============================================================================
# ORDER MANAGEMENT FORMS
# ==============================================================================
class OrderItemForm(forms.ModelForm):
    """Used within admin or custom order creation views."""
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'variant', 'quantity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class OrderForm(forms.ModelForm):
    """Form used for creating orders in POS or manager interfaces."""
    restaurant = forms.ModelChoiceField(
        queryset=Restaurant.objects.all(),
        empty_label="Select Restaurant",
        label="Restaurant"
    )

    class Meta:
        model = Order
        fields = ["customer", "restaurant", "table"]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only available tables
        self.fields['table'].queryset = Table.objects.filter(status=Table.Status.AVAILABLE)
        self.fields['table'].help_text = "Select an available table for this order."
        self.fields['table'].label = "Table"

    def clean_table(self):
        table = self.cleaned_data.get('table')
        if not table:
            raise forms.ValidationError("You must select a table.")
        return table


# ==============================================================================
# INVENTORY MANAGEMENT FORMS
# ==============================================================================
class InventoryItemForm(forms.ModelForm):
    """Form for managing restaurant inventory items."""
    class Meta:
        model = InventoryItem
        fields = ["name", "category", "quantity", "unit", "reorder_level", "restaurant"]

        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Tomato'}),
            'unit': forms.TextInput(attrs={'placeholder': 'kg / L / boxes'}),
        }
        help_texts = {
            'low_stock_threshold': "Threshold for triggering low-stock alerts.",
        }