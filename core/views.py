# --- Python Standard Library Imports ---
import csv
from datetime import timedelta

# --- Django Imports ---
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncHour, TruncDay
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.core.exceptions import ObjectDoesNotExist

# --- Third-Party Imports ---
from rest_framework import viewsets

# --- Local Application Imports ---
from .forms import CustomUserCreationForm, ShiftForm # Assuming ShiftForm exists in forms.py
from .models import (
    CustomUser,
    Restaurant,
    Table,
    MenuItem,
    MenuVariant,
    Order,
    OrderItem,
    KitchenTicket,
    Payment,
    QRToken,
    Shift,
    Inventory,
    Attendance,
)
from .serializers import CustomUserSerializer

# ==============================================================================
# CUSTOM MIXINS
# ==============================================================================

class ManagerRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user has the 'manager' role.
    Redirects to the login page if the test fails.
    """
    def test_func(self) -> bool:
        """Check if the user is authenticated and has the 'manager' role."""
        return self.request.user.is_authenticated and self.request.user.role == 'manager'

# ==============================================================================
# AUTHENTICATION & REGISTRATION VIEWS
# ==============================================================================

# Using Django's built-in views for robustness and security.
login_view = auth_views.LoginView.as_view(
    template_name='core/registration/login.html',
    redirect_authenticated_user=True # Prevent logged-in users from seeing the login page
)

logout_view = auth_views.LogoutView.as_view(
    next_page=reverse_lazy('home') # Redirect to home after logout
)

class RegisterView(CreateView):
    """
    Handles new user registration.
    """
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'core/registration/register.html'

    def form_valid(self, form):
        messages.success(self.request, "Registration successful! Please log in.")
        return super().form_valid(form)

# ==============================================================================
# CORE DASHBOARD & STATIC VIEWS
# ==============================================================================

def home(request: HttpRequest) -> HttpResponse:
    """
    Renders the main landing page. This view determines whether to show
    the guest landing page or redirect an authenticated user to their dashboard.
    """
    if request.user.is_authenticated:
        # Redirect users to the appropriate dashboard based on their role
        if request.user.role == 'manager':
            return redirect('core:manager_dashboard')
            return render(request, 'core/home.html')

        # return redirect('core:user_dashboard')
    
    # For unauthenticated guests
    print("Unauthenticated user, rendering home.html")
    return render(request, 'core/home.html')


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the dashboard for a standard logged-in user (e.g., staff).
    """
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        # Fetch the current attendance for the user
        
        current_attendance = Attendance.objects.filter(
        staff=user, 
        # Access the 'shift' relationship, then its 'end_time' field
        shift__end_time__lte=timezone.now().time()
        # Add any other required filters here
    )
        # current_attendance = Attendance.objects.filter(user=user, 
        #                                               start_time__lte=timezone.now(), 
        #                                               end_time__gte=timezone.now()).first()

        context.update({
            'recent_orders': Order.objects.filter(user=user).order_by('-created_at')[:10],
            'today_orders_count': Order.objects.filter(user=user, created_at__date=today).count(),
            'active_menu_items': MenuItem.objects.filter(is_active=True),
            'current_shift': Shift.objects.filter(attendance=current_attendance).first() if current_attendance else None,
        })
        return context

class ManagerDashboardView(ManagerRequiredMixin, TemplateView):
    """
    Renders the manager's dashboard with comprehensive data analysis and KPIs.
    Accessible only by users with the 'manager' role.
    """
    template_name = 'core/manager_dashboard.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        
        # --- Date Range Filtering ---
        end_date = timezone.now()
        start_date_str = self.request.GET.get('start_date')
        if start_date_str:
            try:
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = end_date - timedelta(days=30) # Default on invalid format
        else:
            start_date = end_date - timedelta(days=30) # Default to the last 30 days

        orders_in_range = Order.objects.filter(created_at__range=[start_date, end_date])

        # --- 1. Key Performance Indicators (KPIs) ---
        kpis = orders_in_range.aggregate(
            total_revenue=Sum('total_price'),
            total_orders=Count('id'),
            avg_order_value=Avg('total_price')
        )

        # --- 2. Sales Over Time (for charts) ---
        sales_by_day = (
            orders_in_range.annotate(day=TruncDay('created_at'))
            .values('day').annotate(daily_revenue=Sum('total_price')).order_by('day')
        )
        
        # --- 3. Top Selling Menu Items (for charts) ---
        top_items = (
            OrderItem.objects.filter(order__in=orders_in_range)
            .values('menu_item__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]
        )

        # --- 4. Peak Business Hours (for charts) ---
        peak_hours = (
            orders_in_range.annotate(hour=TruncHour('created_at'))
            .values('hour').annotate(order_count=Count('id')).order_by('hour')
        )

        # --- 5. Staff Performance ---
        staff_performance = (
            CustomUser.objects.filter(role='staff', order__in=orders_in_range)
            .annotate(total_sales=Sum('order__total_price'), orders_handled=Count('order__id'))
            .order_by('-total_sales')
        )

        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'kpis': kpis,
            'sales_over_time': {
                'labels': [s['day'].strftime('%b %d') for s in sales_by_day],
                'values': [float(s['daily_revenue'] or 0) for s in sales_by_day],
            },
            'top_selling_items': {
                'labels': [item['menu_item__name'] for item in top_items],
                'values': [item['total_sold'] for item in top_items],
            },
            'peak_hours_data': {
                'labels': [p['hour'].strftime('%I %p') for p in peak_hours],
                'values': [p['order_count'] for p in peak_hours],
            },
            'staff_performance_data': staff_performance,
        })
        return context

# ==============================================================================
# STAFF MANAGEMENT VIEWS
# ==============================================================================

class ClockInOutView(LoginRequiredMixin, View):
    """
    Handles a staff member clocking in or out. Toggles their attendance status.
    Assumes a boolean field `attendance_status` on the CustomUser model.
    """

    def get(self, request: HttpRequest, *args, **kwargs):
        # Render a template with the current attendance status
        return render(request, 'core/clock.html')

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponseRedirect:
        user = request.user
        
        try:
            # Check if the user has an 'attendance_status' field
            if hasattr(user, 'attendance_status'):
                # Toggle attendance status
                user.attendance_status = not user.attendance_status
                user.save()
                
                # Set success message based on the new status
                message = "You have successfully clocked in." if user.attendance_status else "You have successfully clocked out."
                messages.success(request, message)
            else:
                messages.error(request, "Your user profile does not support attendance tracking.")
        
        except Exception as e:
            # Handle any unexpected errors
            messages.error(request, f"An error occurred: {str(e)}")
        
        return redirect('core:user_dashboard')
    
class ShiftListView(ManagerRequiredMixin, ListView):
    """
    Displays a list of all shifts. For managers only.
    """
    model = Shift
    template_name = 'core/manage_shifts.html'
    context_object_name = 'shifts'
    ordering = ['-start_time']

class ShiftCreateView(ManagerRequiredMixin, CreateView):
    """
    View to create a new shift. For managers only.
    """
    model = Shift
    form_class = ShiftForm # Make sure this form is defined in forms.py
    template_name = 'core/shift_form.html' # Use a generic form template
    success_url = reverse_lazy('manage_shifts')

    def form_valid(self, form):
        messages.success(self.request, "Shift created successfully!")
        return super().form_valid(form)

class ShiftUpdateView(ManagerRequiredMixin, UpdateView):
    """
    View to edit an existing shift. For managers only.
    """
    model = Shift
    form_class = ShiftForm
    template_name = 'core/shift_form.html'
    success_url = reverse_lazy('manage_shifts')

    def form_valid(self, form):
        messages.success(self.request, "Shift updated successfully!")
        return super().form_valid(form)

class ShiftDeleteView(ManagerRequiredMixin, DeleteView):
    """
    View to delete a shift. For managers only.
    """
    model = Shift
    template_name = 'core/confirm_delete.html' # Generic confirmation template
    success_url = reverse_lazy('core:manage_shifts')
    context_object_name = 'object' # Use 'object' for generic template compatibility

    def post(self, request, *args, **kwargs):
        # Use post for success message to avoid issues with form_valid in DeleteView
        response = super().post(request, *args, **kwargs)
        messages.success(self.request, f"Shift '{self.object.name}' has been deleted.")
        return response

# ==============================================================================
# OPERATIONAL VIEWS (KDS, Customer Display)
# ==============================================================================

class KitchenDisplayView(LoginRequiredMixin, ListView):
    """
    Kitchen Display System (KDS) view showing active tickets.
    """
    model = KitchenTicket
    template_name = 'core/kitchen_display.html'
    context_object_name = 'tickets'

    def get_queryset(self):
        """Return only 'pending' or 'in_progress' tickets, oldest first."""
        return KitchenTicket.objects.filter(
            status__in=[KitchenTicket.Status.PENDING, KitchenTicket.Status.PREPARING]  # Use enum for clarity
        ).select_related('order_item').order_by('created_at')

class CustomerDisplayView(TemplateView):
    """
    Public-facing display screen for customers to see order statuses.
    """
    template_name = 'core/customer_display.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['ready_orders'] = Order.objects.filter(status='ready_for_pickup').order_by('-updated_at')[:10]
        context['preparing_orders'] = Order.objects.filter(status='preparing').order_by('created_at')[:10]
        # You could also add promotional items here
        # context['promo_items'] = MenuItem.objects.filter(is_on_promo=True)
        return context

# ==============================================================================
# API, AJAX & DATA EXPORT
# ==============================================================================

@login_required
@require_POST
def update_ticket_status(request: HttpRequest, ticket_id: int) -> JsonResponse:
    """
    AJAX endpoint for the KDS to update a ticket's status.
    """
    try:
        ticket = get_object_or_404(KitchenTicket, id=ticket_id)
        new_status = request.POST.get('status')

        if new_status not in ['in_progress', 'completed', 'cancelled']:
            return JsonResponse({'status': 'error', 'message': 'Invalid status provided.'}, status=400)

        ticket.status = new_status
        ticket.save()
        
        # If ticket is complete, update the parent order status
        if new_status == 'completed':
            order = ticket.order
            order.status = 'ready_for_pickup'
            order.save()

        return JsonResponse({'status': 'success', 'message': f'Ticket {ticket_id} updated to {new_status}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def export_sales_data(request: HttpRequest) -> HttpResponse:
    """
    Exports order data within a specified date range to a CSV file.
    Accessible only by managers.
    """
    if request.user.role != 'manager':
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('user_dashboard')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sales_export_{timezone.now().strftime("%Y-%m-%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Date', 'Time', 'User', 'Total Price', 'Status', 'Table Number'])

    # Use select_related for efficiency to avoid extra DB hits in the loop
    orders = Order.objects.select_related('user', 'table').all()

    for order in orders:
        writer.writerow([
            order.id,
            order.created_at.strftime('%Y-%m-%d'),
            order.created_at.strftime('%H:%M:%S'),
            order.user.username if order.user else 'N/A',
            order.total_price,
            order.get_status_display(),
            order.table.number if order.table else 'N/A'
        ])

    return response

# ==============================================================================
# DJANGO REST FRAMEWORK VIEWSETS
# ==============================================================================

class CustomUserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    Consider adding permission classes for security.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    # permission_classes = [permissions.IsAdminUser] # Example permission

# Note: ProfileViewSet was removed as it appeared to be a duplicate of CustomUserViewSet.
# If your Profile model is different from CustomUser, you should define a separate ViewSet for it.

# ==============================================================================
# MISCELLANEOUS VIEWS
# ==============================================================================

@login_required
def chat_room(request: HttpRequest) -> HttpResponse:
    """Renders the staff chat room page."""
    return render(request, 'core/chat.html')

@login_required
def inventory_list(request: HttpRequest) -> HttpResponse:
    """Displays a list of all inventory items."""
    items = Inventory.objects.all()
    return render(request, 'core/inventory_list.html', {'items': items})

def create_inventory_item(request):
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            inventory_item = form.save(commit=False)  # Create the instance but don't save to the database yet
            # last_updated will be automatically set by Django when the model is saved
            inventory_item.save()  # Now save the instance
            return redirect('inventory_list')  # Redirect to a list view after saving
    else:
        form = InventoryItemForm()
    
    return render(request, 'inventory/create_item.html', {'form': form})

@login_required
def pos_view(request):
    return render(request, 'pos/pos.html')