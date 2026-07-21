from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, CashierShift, Order, OrderItem, InventoryItem, Product, Category
from django.contrib.auth import get_user_model


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

# ✅ Add it RIGHT HERE
from django.contrib.auth.forms import AuthenticationForm

class StyledAuthenticationForm(AuthenticationForm):
    """
    Styled login form (Tailwind friendly)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            })




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
        fields = ["product", "modifiers", "quantity", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "product": "Menu Item",
            "notes": "Special Instructions",
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
        fields = ['name', 'quantity', 'unit', 'reorder_level']
        

User = get_user_model()

class StaffCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role"]

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)

        if current_user and not current_user.is_platform_owner:
            self.fields["role"].choices = [
                (User.Roles.CASHIER, "Cashier"),
                (User.Roles.SERVER, "Server"),
                (User.Roles.COOK, "Cook"),
            ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, *, restaurant, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.restaurant = restaurant
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

        return user
    
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "base_price",
            "image",
            "is_available",
            "display_order",
            "halal",
        ]

    def __init__(self, *args, **kwargs):
        restaurant = kwargs.pop("restaurant", None)
        super().__init__(*args, **kwargs)

        if restaurant:
            self.fields["category"].queryset = Category.objects.filter(
                menu__restaurant=restaurant
            ).order_by("name")
        
# ==============================================================================
# Restaurant Registration (SaaS Onboarding)
# ==============================================================================

class RestaurantRegistrationForm(forms.Form):
    restaurant_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")

        if password and len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")

        return cleaned_data