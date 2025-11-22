import uuid, csv, json
from datetime import timedelta, datetime

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum, F, Avg, Q, Case, When, BooleanField
from django.db.models.functions import TruncDay
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView

from rest_framework import viewsets, permissions

from core.utils import broadcast_kitchen_ticket
from django.contrib.auth.forms import UserCreationForm

from .forms import CustomUserCreationForm, ShiftForm, OrderForm, InventoryItemForm
from .models import (
    CustomUser, Restaurant, Table, MenuItem, MenuVariant, Order, OrderItem,
    KitchenTicket, Payment, Shift, InventoryItem, Attendance
)
from .serializers import CustomUserSerializer


# ==============================================================================
# AUTHENTICATION & REGISTRATION
# ==============================================================================

class LoginView(auth_views.LoginView):
    template_name = 'core/registration/login.html'
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('core:home')


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('core:login')
    template_name = 'core/registration/register.html'

    def form_valid(self, form):
        messages.success(self.request, "Registration successful! Please log in.")
        return super().form_valid(form)


# ==============================================================================
# DASHBOARDS
# ==============================================================================

def home(request):
    return render(request, 'core/home.html', {
        'welcome_message': 'Welcome to the Restaurant Management System'
    })


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()
        attendance_today = Attendance.objects.filter(staff=user, date=today).first()
        context.update({
            'user': user,
            'attendance_today': attendance_today,
            'recent_orders': Order.objects.filter(user=user).select_related('table').order_by('-created_at')[:5],
            'today_orders_count': Order.objects.filter(user=user, created_at__date=today).count(),
        })
        return context


class ManagerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/manager_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        end_date = timezone.now()
        start_date_str = self.request.GET.get('start_date', (end_date - timedelta(days=30)).strftime('%Y-%m-%d'))
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        orders_in_range = Order.objects.filter(created_at__range=[start_date, end_date]).annotate(
            total_price=Sum(F('items__quantity') * F('items__menu_item__base_price'))
        )
        paid_orders = orders_in_range.filter(status=Order.Status.PAID)

        kpis = {
            'total_revenue': paid_orders.aggregate(val=Sum(F('items__quantity') * F('items__menu_item__base_price')))['val'] or 0,
            'total_orders': paid_orders.count(),
            'avg_order_value': paid_orders.aggregate(val=Avg(F('items__quantity') * F('items__menu_item__base_price')))['val'] or 0,
        }

        sales_by_day = (
            paid_orders.annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(daily_revenue=Sum(F('items__quantity') * F('items__menu_item__base_price')))
            .order_by('day')
        )
        top_items = (
            OrderItem.objects.filter(order__in=paid_orders)
            .values('menu_item__name')
            .annotate(total_sold=Sum('quantity'))
            .order_by('-total_sold')[:5]
        )
        low_stock = InventoryItem.objects.annotate(
            is_low=Case(When(quantity__lt=F('low_stock_threshold'), then=True), default=False, output_field=BooleanField())
        ).filter(is_low=True)[:10]

        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'kpis': kpis,
            'sales_over_time_json': json.dumps({
                'labels': [s['day'].strftime('%b %d') for s in sales_by_day],
                'values': [float(s['daily_revenue'] or 0) for s in sales_by_day],
            }),
            'top_selling_items_json': json.dumps({
                'labels': [i['menu_item__name'] for i in top_items],
                'values': [i['total_sold'] for i in top_items],
            }),
            'low_stock_items': low_stock,
        })
        return context


# ==============================================================================
# CLOCK-IN / CLOCK-OUT
# ==============================================================================

class ClockInOutView(LoginRequiredMixin, View):
    template_name = 'core/clock_in_out.html'
    login_url = reverse_lazy('core:login')

    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        attendance = Attendance.objects.filter(staff=user, date=today).first()
        context = {
            'has_clocked_in': bool(attendance),
            'has_clocked_out': getattr(attendance, 'clock_out', None) is not None if attendance else False,
            'clock_in_time': getattr(attendance, 'clock_in', None),
            'clock_out_time': getattr(attendance, 'clock_out', None),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        now = timezone.now()

        attendance, created = Attendance.objects.get_or_create(
            staff=user, date=today,
            defaults={'clock_in': now, 'status': Attendance.Status.PRESENT}
        )
        if created:
            messages.success(request, f"Clocked in at {now.strftime('%I:%M %p')}.")
        elif attendance.clock_in and not attendance.clock_out:
            attendance.clock_out = now
            attendance.save()
            messages.success(request, f"Clocked out at {now.strftime('%I:%M %p')}. Duration: {attendance.duration}")
        else:
            messages.info(request, "You have already clocked in and out today.")
        return redirect('core:user-dashboard')


# ==============================================================================
# SHIFT MANAGEMENT
# ==============================================================================

class ShiftListView(LoginRequiredMixin, ListView):
    model = Shift
    template_name = 'core/shifts/shift_list.html'
    context_object_name = 'shifts'


class ShiftCreateView(LoginRequiredMixin, CreateView):
    form_class = ShiftForm
    template_name = 'core/shifts/shift_form.html'
    success_url = reverse_lazy('core:shift-list')


class ShiftUpdateView(LoginRequiredMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'core/shifts/shift_form.html'
    success_url = reverse_lazy('core:shift-list')


class ShiftDeleteView(LoginRequiredMixin, DeleteView):
    model = Shift
    template_name = 'core/shifts/shift_confirm_delete.html'
    success_url = reverse_lazy('core:shift-list')


# ==============================================================================
# MENU MANAGEMENT
# ==============================================================================

class MenuItemListView(LoginRequiredMixin, ListView):
    model = MenuItem
    template_name = 'core/menu/menu_list.html'
    context_object_name = 'menu_items'


class MenuItemCreateView(LoginRequiredMixin, CreateView):
    model = MenuItem
    fields = ['name', 'category', 'description', 'base_price', 'is_active']
    template_name = 'core/menu/menu_form.html'
    success_url = reverse_lazy('core:menu-list')


class MenuItemUpdateView(LoginRequiredMixin, UpdateView):
    model = MenuItem
    fields = ['name', 'category', 'description', 'base_price', 'is_active']
    template_name = 'core/menu/menu_form.html'
    success_url = reverse_lazy('core:menu-list')


class MenuItemDeleteView(LoginRequiredMixin, DeleteView):
    model = MenuItem
    template_name = 'core/menu/menu_confirm_delete.html'
    success_url = reverse_lazy('core:menu-list')


# ==============================================================================
# ORDERING & PAYMENT
# ==============================================================================

class TableOrderView(View):
    def get(self, request, token: uuid.UUID):
        table = get_object_or_404(Table.objects.select_related('restaurant'), access_token=token)
        menu_items = MenuItem.objects.filter(restaurant=table.restaurant, is_active=True).prefetch_related('variants')
        categorized = {}
        for item in menu_items:
            cat = item.get_category_display()
            categorized.setdefault(cat, []).append(item)
        return render(request, 'core/table_order_form.html', {'table': table, 'categorized_menu': categorized})

    @transaction.atomic
    def post(self, request, token: uuid.UUID):
        table = get_object_or_404(Table, access_token=token)
        order_data = json.loads(request.body or "[]")
        if not isinstance(order_data, list):
            return JsonResponse({'error': 'Invalid request body'}, status=400)

        order = Order.objects.create(table=table, user=request.user if request.user.is_authenticated else None,
                                     status=Order.Status.PLACED)
        for item_data in order_data:
            menu_item = get_object_or_404(MenuItem, id=item_data.get('item_id'), is_active=True)
            variant = MenuVariant.objects.filter(id=item_data.get('variant_id')).first()
            qty = int(item_data.get('quantity', 0))
            if qty > 0:
                oi = OrderItem.objects.create(order=order, menu_item=menu_item, variant=variant, quantity=qty)
                ticket = KitchenTicket.objects.create(order_item=oi)
                broadcast_kitchen_ticket(ticket, action="create")

        table.status = Table.Status.OCCUPIED
        table.save(update_fields=['status'])
        order.status = Order.Status.IN_PROGRESS
        order.save(update_fields=['status'])
        return JsonResponse({'status': 'success', 'order_id': order.id})


class OrderSuccessView(TemplateView):
    template_name = 'core/order_success.html'

    def get_context_data(self, **kwargs):
        order = get_object_or_404(Order, id=self.kwargs.get('order_id'))
        return {'order': order}

from django.views.generic import DetailView
from core.models import Table

class TableDetailView(DetailView):
    model = Table
    slug_field = "access_token"
    slug_url_kwarg = "access_token"
    template_name = "core/table_detail.html"

def table_list_view(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
    tables = restaurant.tables.all()
    return render(request, "tables.html", {"tables": tables, "restaurant": restaurant})


def table_dashboard_view(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
    tables = restaurant.tables.all().order_by("table_number")
    return render(
        request,
        "core/tables.html",
        {"restaurant": restaurant, "tables": tables},
    )

class OrderPaymentView(View):
    @transaction.atomic
    def post(self, request, order_id: uuid.UUID):
        order = get_object_or_404(Order.objects.annotate_with_total_price(), id=order_id)
        if order.status == Order.Status.PAID:
            messages.info(request, "Order already paid.")
            return redirect('core:user-dashboard')

        method = request.POST.get('payment_method', 'Cash')
        total = getattr(order, 'calculated_total', order.total_price or 0)

        Payment.objects.create(order=order, amount=total, method=method, status=Payment.Status.PAID)
        order.status = Order.Status.PAID
        order.save(update_fields=['status'])

        messages.success(request, f"Payment successful for order {str(order.id)[:8]}.")
        return redirect('core:user-dashboard')


@require_POST
def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    for order_item in order.items.all():
        ticket = getattr(order_item, "kitchenticket", None)
        if ticket:
            broadcast_kitchen_ticket(ticket, action="delete")

    order.delete()
    messages.success(request, f"Order #{str(pk)[:8]} deleted successfully and removed from Kitchen Display.")
    return redirect("core:order-list")


# ==============================================================================
# OPERATIONAL DISPLAYS (KDS, POS, Customer)
# ==============================================================================

class KitchenDisplayView(LoginRequiredMixin, TemplateView):
    template_name = 'core/kitchen_display.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Optional filtering by order status (placed, ready, etc.)
        status_filter = self.request.GET.get('status')

        # Select related order, table, and restaurant for performance
        tickets = (
            KitchenTicket.objects
            .select_related('order__table', 'order__restaurant')
            .order_by('created_at')
        )

        if status_filter:
            # Filter by order status since tickets represent full orders
            tickets = tickets.filter(order__status=status_filter)

        context['tickets'] = tickets
        context['status_filter'] = status_filter
        context['status_choices'] = Order.Status.choices  # use order statuses instead
        return context
    
class POSView(TemplateView):
    template_name = "core/pos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = MenuItem.objects.filter(is_active=True)
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body or "{}")
        item_id = data.get("item_id")
        qty = int(data.get("quantity", 1))
        payment_method = data.get("payment_method")

        if not item_id or not payment_method:
            return JsonResponse({"status": "error", "message": "Missing required fields."})

        try:
            item = MenuItem.objects.select_for_update().get(id=item_id)

            if item.quantity < qty:
                return JsonResponse({"status": "error", "message": "Not enough stock."})

            order = Order.objects.create(status=Order.Status.PLACED, payment_method=payment_method)
            order_item = OrderItem.objects.create(order=order, menu_item=item, quantity=qty)

            item.quantity -= qty
            item.save(update_fields=["quantity"])

            ticket = KitchenTicket.objects.create(order_item=order_item)
            broadcast_kitchen_ticket(ticket, action="create")

            return JsonResponse({
                "status": "success",
                "order_id": order.id,
                "ticket_id": ticket.id,
            })

        except MenuItem.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Item not found."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})


class CustomerDisplayView(LoginRequiredMixin, TemplateView):
    template_name = 'core/displays/customer_display.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ready_orders'] = Order.objects.filter(status=Order.Status.READY)
        return context


# ==============================================================================
# INVENTORY MANAGEMENT
# ==============================================================================

class InventoryListView(LoginRequiredMixin, ListView):
    model = InventoryItem
    template_name = 'core/inventory/inventory_list.html'
    context_object_name = 'items'


class InventoryItemCreateView(LoginRequiredMixin, CreateView):
    form_class = InventoryItemForm
    template_name = 'core/inventory/inventory_form.html'
    success_url = reverse_lazy('core:inventory-list')


class InventoryItemUpdateView(LoginRequiredMixin, UpdateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = 'core/inventory/inventory_form.html'
    success_url = reverse_lazy('core:inventory-list')


# ==============================================================================
# UPDATE KITCHEN TICKET STATUS (AJAX)
# ==============================================================================

class UpdateKitchenTicketStatusView(View):
    @transaction.atomic
    def post(self, request, ticket_id: int):
        ticket = get_object_or_404(KitchenTicket, id=ticket_id)
        data = json.loads(request.body or "{}")
        new_status = data.get('status')
        if new_status not in dict(KitchenTicket.Status.choices):
            return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)

        ticket.status = new_status
        ticket.save(update_fields=['status'])
        broadcast_kitchen_ticket(ticket, action="update")

        order = ticket.order_item.order
        complete = not order.items.exclude(kitchenticket__status=KitchenTicket.Status.READY).exists()
        if complete:
            order.status = Order.Status.READY
            order.save(update_fields=['status'])
            broadcast_kitchen_ticket(ticket, action="order_complete")

        return JsonResponse({'status': 'success', 'new_status': ticket.get_status_display()})


# ==============================================================================
# API VIEWSETS
# ==============================================================================

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().order_by('id')
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=user.id)


# ==============================================================================
# EXPORT SALES DATA
# ==============================================================================

class ExportSalesDataView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_data.csv"'

        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Date', 'Total', 'Status'])

        orders = Order.objects.filter(status=Order.Status.PAID).annotate(
            total_price=Sum(F('items__quantity') * F('items__menu_item__base_price'))
        )

        for o in orders:
            writer.writerow([o.id, o.created_at.strftime('%Y-%m-%d %H:%M'), o.total_price or 0, o.status])
        return response


class OrderDetailView(DetailView):
    model = Order
    template_name = "core/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = OrderItem.objects.filter(order=self.object)
        return context


def order_status_json(request, pk):
    order = get_object_or_404(Order, pk=pk)
    data = {
        "status": order.status,
        "status_display": order.get_status_display(),
        "updated_at": timezone.localtime(order.updated_at).strftime("%Y-%m-%d %H:%M:%S"),
    }
    return JsonResponse(data)


class OrderListView(ListView):
    model = Order
    template_name = "core/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        qs = Order.objects.select_related('table', 'customer', 'restaurant').order_by("-created_at")
        q = self.request.GET.get("q")
        status = self.request.GET.get("status")
        payment = self.request.GET.get("payment")

        if q:
            qs = qs.filter(Q(id__icontains=q) | Q(table__number__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if payment:
            qs = qs.filter(payment_method=payment)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_statuses"] = Order.Status.choices
        return context


class OrderHistoryView(ListView):
    template_name = "core/order_history.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.order_by("-created_at")[:50]


@require_POST
def complete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.status = Order.Status.COMPLETED
    order.save()

    messages.success(request, f"Order #{order.id} marked as completed.")
    broadcast_kitchen_ticket(None, action="order_completed", order_id=str(order.pk))
    return redirect("core:order-detail", pk=order.pk)

# ==============================================================================
# CHAT & SETTINGS
# ==============================================================================

class ChatRoomView(LoginRequiredMixin, TemplateView):
    template_name = 'core/chat_room.html'


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/settings.html'