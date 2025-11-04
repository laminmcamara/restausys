# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
# Import the models you defined in core/models.py
from .models import Shift, CustomUser, OrderItem, InventoryItem, Restaurant




class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'start_time', 'end_time']
        # Use widgets for HTML5 time input for better user experience
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role',) # Include the custom 'role' field

    # Optional: Add this method to ensure the 'email' field is required in the form
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity', 'variant', 'notes']
        
class InventoryItemForm(forms.ModelForm):
    restaurant = forms.ModelChoiceField(
        queryset=Restaurant.objects.all(),
        label="Restaurant *",
        help_text="The restaurant this inventory item belongs to."
    )
    name = forms.CharField(
        max_length=255,
        label="Name *",
        help_text="Enter the name of the inventory item."
    )
    quantity = forms.IntegerField(
        min_value=0,
        label="Quantity *",
        help_text="Enter the quantity of the inventory item."
    )
    unit = forms.CharField(
        max_length=50,
        label="Unit *",
        help_text="e.g., kg, L, units, boxes"
    )
    low_stock_threshold = forms.IntegerField(
        min_value=0,
        label="Low stock threshold *",
        help_text="Threshold for low stock alerts."
    )
    
    class Meta:
        model = InventoryItem
        fields = ['restaurant', 'name', 'quantity', 'unit', 'low_stock_threshold']