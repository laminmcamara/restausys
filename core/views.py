# core/views.py

import uuid, csv, json
from datetime import timedelta, datetime

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    TemplateView, ListView, DetailView
)
from django.db import transaction
from django.db.models import Sum
from openpyxl import Workbook

# DRF
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.decorators import api_view, permission_classes
from django.urls import reverse

from .stripe_utils import create_payment_intent

# TENANT BASE
from core.tenant import TenantModelViewSet

# CORE IMPORTS
from .models import (
    Order, OrderItem, Category, Product,
    Table, Payment, KitchenTicket, Settings
)
from .serializers import (
    OrderSerializer, OrderItemSerializer,
    CategorySerializer, ProductSerializer,
    TableSerializer, PaymentSerializer
)
from .permissions import IsStaffOfRestaurant



# ======================================================================
# AUTHENTICATION
# ======================================================================

class LoginView(auth_views.LoginView):
    template_name = "core/registration/login.html"
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("core:home")


class IndexView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            context["featured_products"] = (
                Product.objects.filter(
                    category__menu__restaurant=self.request.user.restaurant,
                    is_available=True
                )
                .select_related("category", "category__menu")
                .order_by("name")[:3]
            )
        else:
            context["featured_products"] = Product.objects.none()

        return context
# ======================================================================
# POS DASHBOARD (TEMPLATE)
# ======================================================================

class PosDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/pos/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        restaurant = self.request.user.restaurant

        payments = Payment.objects.filter(
            order__restaurant=restaurant,
            status=Payment.Status.PAID
        )

        context.update({
            "total_sales": payments.aggregate(total=Sum("amount"))["total"] or 0,
            "payment_count": payments.count(),
            "recent_payments": payments.order_by("-created_at")[:5],
            "current_year": timezone.now().year,
        })

        return context


# ======================================================================
# CUSTOMER DISPLAY (SECURED)
# ======================================================================

class CustomerDisplayView(LoginRequiredMixin, TemplateView):
    template_name = "core/displays/customer_display.html"

    def get_context_data(self, **kwargs):
        restaurant = self.request.user.restaurant
        return {
            "ready_orders": Order.objects.filter(
                restaurant=restaurant,
                status=Order.Status.READY
            )
        }


@login_required
def customer_display_refresh(request):
    restaurant = request.user.restaurant

    ready = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.READY
    )[:10]

    pending = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.PREPARING
    )[:10]

    return JsonResponse({
        "ready_orders": [o.short_id() for o in ready],
        "pending_orders": [o.short_id() for o in pending]
    })


# ======================================================================
# KITCHEN DISPLAY (SECURED)
# ======================================================================

class KitchenDisplayView(LoginRequiredMixin, TemplateView):
    template_name = "core/kitchen/kds.html"

    def get_context_data(self, **kwargs):
        restaurant = self.request.user.restaurant

        tickets = KitchenTicket.objects.filter(
            order__restaurant=restaurant
        ).select_related("order__table").order_by("created_at")

        return {"tickets": tickets}


class UpdateKitchenTicketStatusView(View):
    @transaction.atomic
    def post(self, request, ticket_id):
        ticket = get_object_or_404(
            KitchenTicket,
            id=ticket_id,
            order__restaurant=request.user.restaurant
        )

        data = json.loads(request.body or "{}")
        new_status = data.get("status")

        if new_status not in dict(KitchenTicket.Status.choices):
            return JsonResponse({"status": "error"}, status=400)

        ticket.status = new_status
        ticket.save()

        if new_status == KitchenTicket.Status.COMPLETED:
            ticket.order.status = Order.Status.READY
            ticket.order.save()

        return JsonResponse({"status": "success"})


# ======================================================================
# DAILY REPORTS (SECURED)
# ======================================================================
def _get_today_paid_orders_and_total(user):
    today = timezone.now().date()

    orders = Order.objects.filter(
        restaurant=user.restaurant,
        created_at__date=today,
        status=Order.Status.PAID
    )

    total_revenue = orders.aggregate(
        total=Sum("items__final_price")
    )["total"] or 0

    return today, orders, total_revenue


class DailyReportsListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "core/daily_reports.html"
    context_object_name = "orders"

    def get_queryset(self):
        today = timezone.now().date()
        return Order.objects.filter(
            restaurant=self.request.user.restaurant,
            created_at__date=today
        )


@login_required
def DailyReportCSV(request):
    today, orders, total_revenue = _get_today_paid_orders_and_total(request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="daily_report_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(["Order ID", "Table", "Total Amount", "Status", "Created At"])

    for order in orders:
        writer.writerow([
            order.id,
            getattr(order.table, "name", "N/A"),
            order.total_price,
            order.status,
            order.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    writer.writerow([])
    writer.writerow(["", "", "TOTAL:", total_revenue])

    return response

@login_required
def DailyReportExcel(request):
    today, orders, total_revenue = _get_today_paid_orders_and_total(request.user)

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Order ID", "Table", "Total Amount", "Status", "Created At"])

    for order in orders:
        sheet.append([
            order.id,
            getattr(order.table, "name", "N/A"),
            order.total_price,
            order.status,
            order.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    sheet.append([])
    sheet.append(["", "", "TOTAL:", total_revenue])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="daily_report_{today}.xlsx"'

    workbook.save(response)
    return response

class PeriodSummaryView(LoginRequiredMixin, View):
    def get(self, request):
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        if not start_date or not end_date:
            return JsonResponse({"error": "start and end dates required"}, status=400)

        orders = Order.objects.filter(
            restaurant=request.user.restaurant,
            created_at__date__range=[start_date, end_date],
            status=Order.Status.PAID
        )

        total_revenue = orders.aggregate(
            total=Sum("items__final_price")
        )["total"] or 0

        return JsonResponse({
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": total_revenue,
            "orders_count": orders.count()
        })


# ======================================================================
# ORDER TEMPLATE VIEWS (SECURED)
# ======================================================================

class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "core/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        return Order.objects.filter(
            restaurant=self.request.user.restaurant
        ).order_by("-created_at")


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/order_detail.html"

    def get_queryset(self):
        return Order.objects.filter(
            restaurant=self.request.user.restaurant
        )
        
class PosOrderScreenTakeoutView(LoginRequiredMixin, TemplateView):
    template_name = "core/pos_takeout_screen.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        restaurant = self.request.user.restaurant

        # Categories
        categories = Category.objects.filter(
            restaurant=restaurant
        ).order_by("name")

        # Products
        products = Product.objects.filter(
            restaurant=restaurant,
            is_available=True
        ).select_related("category").order_by("name")

        # Active takeout orders (not paid yet)
        active_orders = Order.objects.filter(
            restaurant=restaurant,
            order_type=Order.OrderType.TAKEOUT,  # adjust if your enum differs
            status=Order.Status.PENDING
        ).order_by("-created_at")

        context.update({
            "categories": categories,
            "products": products,
            "active_orders": active_orders,
        })

        return context

class OrderSuccessView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "core/order_success.html"
    context_object_name = "order"
    pk_url_kwarg = "order_id"

    def get_queryset(self):
        return Order.objects.filter(
            restaurant=self.request.user.restaurant
        )
        
# ======================================================================
# ======================== API VIEWSETS ================================
# ======================================================================
class TableViewSet(TenantModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated, IsStaffOfRestaurant]

class OrderViewSet(TenantModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsStaffOfRestaurant]

    def perform_create(self, serializer):
        serializer.save(
            restaurant=self.request.user.restaurant,
            staff=self.request.user
        )


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(
            order__restaurant=self.request.user.restaurant
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        ).select_related("menu", "parent").prefetch_related("products")


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            category__menu__restaurant=self.request.user.restaurant,
            is_available=True
        ).select_related("category").prefetch_related(
            "modifier_groups__options"
        )


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(
            order__restaurant=self.request.user.restaurant
        )


# ======================================================================
# POS API ENDPOINTS
# ======================================================================

class PosDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = request.user.restaurant

        categories = Category.objects.filter(menu__restaurant=restaurant)
        products = Product.objects.filter(category__menu__restaurant=restaurant)
        tables = Table.objects.filter(restaurant=restaurant)

        return Response({
            "categories": CategorySerializer(categories, many=True).data,
            "products": ProductSerializer(products, many=True).data,
            "tables": TableSerializer(tables, many=True).data,
        })


class PosSaveOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = serializer.save(
            restaurant=request.user.restaurant,
            staff=request.user,
        )

        return Response(OrderSerializer(order).data)
    
    
# ======================================================================
# ======================== PAYMENTS API ================================
# ======================================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_qr_payment(request, order_id):
    """
    Generate Stripe payment intent and QR payment URL.
    Tenant-secured.
    """

    # ✅ Tenant-safe order lookup
    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=request.user.restaurant
    )

    # ✅ Prevent duplicate payments
    if order.status == Order.Status.PAID:
        return Response(
            {"error": "Order already paid"},
            status=400
        )

    # ✅ Create Stripe payment intent
    intent = create_payment_intent(order)

    # ✅ Create or update Payment record
    Payment.objects.update_or_create(
        order=order,
        defaults={
            "stripe_payment_intent": intent.id,
            "amount": order.total_price(),
        }
    )

    # ✅ Dynamic URL (works in production)
    qr_url = request.build_absolute_uri(
        reverse("core:pay_order", args=[order.id])
    )

    return Response({
        "qr_url": qr_url,
        "client_secret": intent.client_secret
    })
    
    
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "core/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        settings_obj, created = Settings.objects.get_or_create(
            restaurant=self.request.user.restaurant
        )

        context["settings"] = settings_obj
        return context
    
class ManagerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/manager_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        orders_today = Order.objects.filter(
            restaurant=self.request.user.restaurant,
            created_at__date=today,
            status=Order.Status.PAID
        )

        total_revenue = orders_today.aggregate(
            total=Sum("items__final_price")
        )["total"] or 0

        context.update({
            "orders_count": orders_today.count(),
            "total_revenue": total_revenue,
        })

        return context
    
class RestaurantDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/restaurant_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        active_orders = Order.objects.filter(
            restaurant=self.request.user.restaurant,
            status=Order.Status.PENDING
        )

        tables_in_use = Table.objects.filter(
            restaurant=self.request.user.restaurant,
            is_active=True
        ).count()

        context.update({
            "active_orders_count": active_orders.count(),
            "tables_in_use": tables_in_use,
        })

        return context
    
class TableOverviewView(LoginRequiredMixin, TemplateView):
    template_name = "core/tables.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        restaurant = self.request.user.restaurant

        tables = Table.objects.filter(
            restaurant=restaurant
        ).order_by("table_number")

        active_orders = Order.objects.filter(
            restaurant=restaurant,
            table__isnull=False,
        ).exclude(
            status__in=[
                Order.Status.PAID,
                Order.Status.COMPLETED,
                Order.Status.CANCELED,
            ]
        ).select_related("table")

        context.update({
            "tables": tables,
            "active_orders": active_orders,
        })

        return context
    

