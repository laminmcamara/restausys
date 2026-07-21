# core/views.py

import uuid, csv, json
from datetime import timedelta, datetime
from django.http import HttpResponseForbidden

from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from .forms import StaffCreateForm
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import (
    TemplateView, ListView, DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    
    
)

from django.db.models import Sum, Count, Prefetch, Exists, OuterRef, Subquery, DecimalField  

from django.db.models.functions import TruncDate, TruncHour, Coalesce

from decimal import Decimal
from django.conf import settings
import random

from openpyxl import Workbook

# DRF
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.permissions import AllowAny
from .permissions import IsOwnerOrManager
from django.core.serializers.json import DjangoJSONEncoder

from rest_framework.decorators import api_view, permission_classes
from django.urls import reverse
from rest_framework.viewsets import ModelViewSet
from rest_framework import filters
from .serializers import ModifierOptionSerializer

from django.core.exceptions import PermissionDenied
from .stripe_utils import create_payment_intent
from django.views.generic import UpdateView

# TENANT BASE
from core.tenant import TenantModelViewSet
from .forms import ProductForm
from functools import wraps

# CORE IMPORTS
from .models import (Company, 
    Order, OrderItem, Category, Product,
    Table, TableSession, Payment, KitchenTicket, Settings, ModifierGroup, ModifierOption, Restaurant, ProductVariant, CustomUser, Menu, CashierShift

)
from .serializers import (
    OrderSerializer, OrderItemSerializer,
    CategorySerializer, ProductSerializer,
    TableSerializer, PaymentSerializer
)
from .permissions import IsStaffOfRestaurant
from django.contrib.auth import get_user_model
from .models import Subscription
from django.utils.timezone import now
from asgiref.sync import async_to_sync
from django.db.models.functions import ExtractHour
from django.db import transaction
import stripe

from django.contrib.auth import login
from .forms import RestaurantRegistrationForm

User = get_user_model()


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def broadcast_order_update(order):
    """
    Sends updated order to:
    - POS
    - Kitchen display
    - Restaurant dashboard
    - Table display
    - Customer display
    """

    channel_layer = get_channel_layer()

    serialized = OrderSerializer(order).data

    data = {
        "type": "order_status_update",
        "order": serialized
    }

    message = {
        "type": "order_status_update",
        "data": data
    }

    # ✅ POS
    async_to_sync(channel_layer.group_send)(
        f"pos_{order.restaurant_id}",
        message
    )

    # ✅ Kitchen
    async_to_sync(channel_layer.group_send)(
        f"kitchen_{order.restaurant_id}",
        message
    )

    # ✅ Restaurant Dashboard
    async_to_sync(channel_layer.group_send)(
        f"restaurant_{order.restaurant_id}",
        message
    )

    # ✅ Table Screen
    if order.table_id:
        async_to_sync(channel_layer.group_send)(
            f"table_{order.table_id}",
            message
        )

    # ✅ Customer Display
    async_to_sync(channel_layer.group_send)(
        f"customer_{order.restaurant_id}",
        message
    )
    
class IndexView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        if (
            user.is_authenticated
            and hasattr(user, "restaurant")
            and user.restaurant
        ):
            restaurant = user.restaurant

            context["featured_products"] = (
                Product.objects
                .filter(
                    category__menu__restaurant=restaurant,
                    is_available=True
                )
                .select_related("category", "category__menu")
                .only(
                    "id",
                    "name",
                    "price",
                    "category__id",
                    "category__name"
                )
                .order_by("name")[:3]
            )
        else:
            context["featured_products"] = Product.objects.none()

        return context
    
# ======================================================================
# POS DASHBOARD (ROLE-DRIVEN + PROTECTED)
# ======================================================================

class DashboardRouterView(LoginRequiredMixin, View):
    """
    Redirects authenticated users to the correct dashboard
    based on their role.
    """

    def get(self, request, *args, **kwargs):
        user = request.user

        # Safety: ensure user belongs to a restaurant
        if not hasattr(user, "restaurant") or not user.restaurant:
            return redirect("core:login")

        # ✅ FIXED DUPLICATE ROLE BUG
        if user.role == CustomUser.Roles.MANAGER:
            return redirect("core:manager_dashboard")

        if user.role == CustomUser.Roles.RESTAURANT:
            return redirect("core:restaurant_dashboard")

        if user.role == CustomUser.Roles.CASHIER:
            return redirect("core:pos_dashboard")

        return redirect("core:login")
    
    
class PosDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/pos/dashboard.html"

    # ✅ SHIFT PROTECTION
    def dispatch(self, request, *args, **kwargs):

        user = request.user

        # Only cashiers require active shift
        if user.is_cashier:
            active_shift = CashierShift.objects.filter(
                user=user,
                restaurant=user.restaurant,
                is_active=True
            ).exists()

            if not active_shift:
                messages.error(
                    request,
                    "You must open a cashier shift before accessing POS."
                )
                return redirect("core:start_shift")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        restaurant = user.restaurant

        # ✅ ACTIVE SHIFT IN CONTEXT
        active_shift = CashierShift.objects.filter(
            user=user,
            restaurant=restaurant,
            is_active=True
        ).first()

        context["active_shift"] = active_shift

        # ✅ BASIC INFO
        context["profile_incomplete"] = not restaurant.profile_complete
        context["currency"] = restaurant.currency
        context["current_year"] = timezone.now().year

        # ✅ ACTIVE CATEGORIES
        context["categories"] = Category.objects.filter(
            menu__restaurant=restaurant,
            is_active=True
        ).order_by("name")

        # ✅ SALES DATA
        payments = Payment.objects.filter(
            order__restaurant=restaurant,
            status=Payment.Status.PAID
        )

        total_sales = payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

        context.update({
            "total_sales": total_sales,
            "payment_count": payments.count(),
            "recent_payments": payments.order_by("-created_at")[:5],
        })

        # ✅ ROLE-DRIVEN SECTIONS (SMART SHIFT BUTTON)
        sections = []

        if user.is_cashier:

            if active_shift:
                shift_item = {
                    "name": "Close Shift",
                    "url": "core:close_shift",
                    "icon": "bi-stop-circle",
                    "color": "bg-red-600 hover:bg-red-500",
                }
            else:
                shift_item = {
                    "name": "Open Shift",
                    "url": "core:start_shift",
                    "icon": "bi-play-circle",
                    "color": "bg-green-600 hover:bg-green-500",
                }

            sections.append({
                "title": "Cashier",
                "items": [shift_item],
            })

        if user.is_manager or user.is_superuser:
            sections.append({
                "title": "Management",
                "items": [
                    {
                        "name": "Manager Dashboard",
                        "url": "core:manager_dashboard",
                        "icon": "bi-briefcase",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Restaurant Dashboard",
                        "url": "core:restaurant_dashboard",
                        "icon": "bi-building",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Settings",
                        "url": "core:settings",
                        "icon": "bi-gear",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Daily Reports",
                        "url": "core:daily_reports",
                        "icon": "bi-calendar",
                        "color": "bg-indigo-600 hover:bg-indigo-700",
                    },
                    {
                        "name": "Analytics",
                        "url": "core:analytics",
                        "icon": "bi-graph-up",
                        "color": "bg-emerald-600 hover:bg-emerald-700",
                    },
                ],
            })

        context["dashboard_sections"] = sections

        return context
    
    
class PosDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/pos/dashboard.html"

    # ✅ SHIFT PROTECTION
    def dispatch(self, request, *args, **kwargs):

        user = request.user

        # Only cashiers require active shift
        if user.is_cashier:
            active_shift = CashierShift.objects.filter(
                user=user,
                restaurant=user.restaurant,
                is_active=True
            ).exists()

            if not active_shift:
                messages.error(
                    request,
                    "You must open a cashier shift before accessing POS."
                )
                return redirect("core:start_shift")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        restaurant = user.restaurant

        # ✅ ACTIVE SHIFT IN CONTEXT
        active_shift = CashierShift.objects.filter(
            user=user,
            restaurant=restaurant,
            is_active=True
        ).first()

        context["active_shift"] = active_shift

        # ✅ BASIC INFO
        context["profile_incomplete"] = not restaurant.profile_complete
        context["currency"] = restaurant.currency
        context["current_year"] = timezone.now().year

        # ✅ ACTIVE CATEGORIES
        context["categories"] = Category.objects.filter(
            menu__restaurant=restaurant,
            is_active=True
        ).order_by("name")

        # ✅ SALES DATA
        payments = Payment.objects.filter(
            order__restaurant=restaurant,
            status=Payment.Status.PAID
        )

        total_sales = payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

        context.update({
            "total_sales": total_sales,
            "payment_count": payments.count(),
            "recent_payments": payments.order_by("-created_at")[:5],
        })

        # ✅ ROLE-DRIVEN SECTIONS (SMART SHIFT BUTTON)
        sections = []

        if user.is_cashier:

            if active_shift:
                shift_item = {
                    "name": "Close Shift",
                    "url": "core:close_shift",
                    "icon": "bi-stop-circle",
                    "color": "bg-red-600 hover:bg-red-500",
                }
            else:
                shift_item = {
                    "name": "Open Shift",
                    "url": "core:start_shift",
                    "icon": "bi-play-circle",
                    "color": "bg-green-600 hover:bg-green-500",
                }

            sections.append({
                "title": "Cashier",
                "items": [shift_item],
            })

        if user.is_manager or user.is_superuser:
            sections.append({
                "title": "Management",
                "items": [
                    {
                        "name": "Manager Dashboard",
                        "url": "core:manager_dashboard",
                        "icon": "bi-briefcase",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Restaurant Dashboard",
                        "url": "core:restaurant_dashboard",
                        "icon": "bi-building",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Settings",
                        "url": "core:settings",
                        "icon": "bi-gear",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Daily Reports",
                        "url": "core:daily_reports",
                        "icon": "bi-calendar",
                        "color": "bg-indigo-600 hover:bg-indigo-700",
                    },
                    {
                        "name": "Analytics",
                        "url": "core:analytics",
                        "icon": "bi-graph-up",
                        "color": "bg-emerald-600 hover:bg-emerald-700",
                    },
                ],
            })

        context["dashboard_sections"] = sections

        return context
    
# ======================================================================
# CUSTOMER DISPLAY (SECURED)
# ======================================================================


class CustomerDisplayView(TemplateView):
    template_name = "core/pos/customer_display.html"

    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.get("token")
        self.table_id = kwargs.get("table_id")

        self.table = get_object_or_404(
            Table,
            id=self.table_id,
            access_token=self.token
        )

        self.restaurant = self.table.restaurant

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["restaurant"] = self.restaurant
        context["table"] = self.table
        context["table_id"] = self.table.id
        return context
    
    
def customer_display_refresh(request, token, table_id):
    restaurant = get_object_or_404(
        Restaurant,
        display_token=token
    )
    
    table = get_object_or_404(
        Table,
        id=table_id,
        restaurant=restaurant
    )
    
    
    ready = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.READY
    )[:10]

    pending = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.IN_PROGRESS
    )[:10]

    return JsonResponse({
        "ready_orders": [o.short_id() for o in ready],
        "pending_orders": [o.short_id() for o in pending]
    })
    
    

@login_required
def customer_display_shortcut(request):
    restaurant = Restaurant.objects.first()

    if not restaurant:
        return HttpResponse("No restaurant configured.", status=400)

    first_table = restaurant.tables.first()

    if not first_table:
        return HttpResponse("No tables configured.", status=400)

    return redirect(
    "core:customer_display",
    token=first_table.access_token,
    table_id=first_table.id,
)


# =============================================================================
# API: UPDATE ORDER STATUS (STRICT & SAFE)
# =============================================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def update_order_status(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=request.user.restaurant
    )

    action = request.data.get("action")

    try:
        if action == "placed":
            order.mark_as_placed()

        elif action == "start":
            order.send_to_kitchen()

        elif action == "ready":
            order.mark_ready()

        elif action == "served":
            order.mark_served()

        elif action == "complete":
            order.complete_order()

        else:
            return Response(
                {"error": "Invalid action"},
                status=400
            )

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=400
        )

    broadcast_order_update(order)

    return Response({
        "success": True,
        "status": order.status
    })
def manager_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if (request.user.role or "").lower() != "manager" and not request.user.is_superuser:
            return HttpResponseForbidden("Managers only.")

        return view_func(request, *args, **kwargs)

    return wrapper

# ======================================================================
# DAILY REPORTS (SECURED)
# ======================================================================
def _get_today_paid_orders_and_total(user):
    today = timezone.now().date()

    orders = Order.objects.filter(
        restaurant=user.restaurant,
        created_at__date=today,
        payment_status=Order.PaymentStatus.PAID,
    )

    total_revenue = orders.aggregate(
        total=Sum("items__final_price")
    )["total"] or 0

    return today, orders, total_revenue


class DailyReportsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Order
    template_name = "dashboard/daily_reports.html"
    context_object_name = "orders"

    def test_func(self):
        return (
        (self.request.user.role or "").lower() == "manager"
        or self.request.user.is_superuser
        )

    def get_queryset(self):
        today = timezone.now().date()
        return Order.objects.filter(
            restaurant=self.request.user.restaurant,
            created_at__date=today,
            status="PAID"
        )



@manager_required
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

@manager_required
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
            payment_status=Order.PaymentStatus.PAID, 
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


# ==========================================================
# ANALYTICS API VIEW
# ==========================================================
class AnalyticsAPIView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        if (request.user.role or "").lower() != "manager" and not request.user.is_superuser:
            raise PermissionDenied("Manager only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        restaurant = request.user.restaurant
        
        now = timezone.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timezone.timedelta(days=1)

        # ✅ Only PAID orders for revenue metrics
        paid_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__gte=start,
            created_at__lt=end,
            payment_status=Order.PaymentStatus.PAID
        )

        total_orders = paid_orders.count()

        # ✅ Use stored total_amount (enterprise-safe)
        total_revenue = paid_orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        avg_order = (
            total_revenue / total_orders
            if total_orders else 0
        )

        # ✅ Operational status counts (all orders today)
        status_counts = {
            "draft": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.DRAFT
            ).count(),
            "placed": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.PLACED
            ).count(),
            "in_progress": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.IN_PROGRESS
            ).count(),
            "ready": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.READY
            ).count(),
            "served": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.SERVED
            ).count(),
            "completed": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.COMPLETED
            ).count(),
            "canceled": Order.objects.filter(
                restaurant=restaurant,
                created_at__gte=start,
                created_at__lt=end,
                status=Order.Status.CANCELED
            ).count(),
        }

        # ✅ Revenue by hour (only paid orders)
        hourly_qs = paid_orders.annotate(
            hour=ExtractHour("created_at")
        ).values("hour").annotate(
            total=Sum("total_amount")
        ).order_by("hour")

        hourly_revenue = [
            {
                "hour": entry["hour"],
                "total": float(entry["total"] or 0)
            }
            for entry in hourly_qs
        ]

        # ✅ Best selling items (faster + scalable version)
        best_items_qs = OrderItem.objects.filter(
            order__restaurant=restaurant,
            order__created_at__gte=start,
            order__created_at__lt=end,
            order__payment_status=Order.PaymentStatus.PAID
        ).values(
            "menu_item__name"
        ).annotate(
            qty=Sum("quantity")
        ).order_by("-qty")[:5]

        best_items = [
            {
                "name": item["menu_item__name"],
                "qty": item["qty"] or 0
            }
                for item in best_items_qs
        ]

        return JsonResponse({
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "avg_order": float(avg_order),
            "status_counts": status_counts,
            "hourly_revenue": hourly_revenue,
            "best_items": best_items,
        })

# ==========================================================
# ANALYTICS DASHBOARD PAGE VIEW
# ==========================================================
class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/analytics.html"

    def dispatch(self, request, *args, **kwargs):
        if (request.user.role or "").lower() != "manager" and not request.user.is_superuser:
            raise PermissionDenied("Manager only.")
        return super().dispatch(request, *args, **kwargs)
# ======================================================================
# ORDER TEMPLATE VIEWS (SECURED)
# ======================================================================

@require_POST
@login_required
def create_order_api(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items", [])
    order_id = data.get("order_id")

    if not items or not order_id:
        return JsonResponse({"error": "Missing data"}, status=400)

    restaurant = request.user.restaurant

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant,
        status=Order.Status.DRAFT
    )

    with transaction.atomic():

        order.items.all().delete()  # Optional: reset items

        total = 0

        for item in items:
            variant_id = item.get("variantId")
            qty = int(item.get("qty", 1))

            if not variant_id or qty <= 0:
                continue

            variant = ProductVariant.objects.select_related("product").get(
                id=variant_id,
                product__category__menu__restaurant=restaurant
            )

            unit_price = variant.price
            line_total = unit_price * qty

            OrderItem.objects.create(
                order=order,
                product=variant.product,
                variant=variant,
                quantity=qty,
                final_price=unit_price
            )

            total += line_total

        order.total = total
        order.status = Order.Status.PLACED
        order.save(update_fields=["total", "status"])

    return JsonResponse({
        "order_id": str(order.id)
    })
    
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "core/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.filter(
            restaurant=self.request.user.restaurant
        ).order_by("-created_at")

        # Filters
        q = self.request.GET.get("q")
        status = self.request.GET.get("status")
        payment = self.request.GET.get("payment")

        if q:
            queryset = queryset.filter(id__icontains=q)

        if status:
            queryset = queryset.filter(status=status)

        if payment:
            queryset = queryset.filter(payment_method=payment)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        today_orders = Order.objects.filter(
        restaurant=self.request.user.restaurant,
        created_at__date=today
    )

        context["today_sales"] = (
        today_orders.filter(status="PAID")
        .aggregate(total=Sum("payments__amount"))["total"]
        or Decimal("0.00")
    )

        context["today_orders_count"] = today_orders.count()

        context["paid_orders_count"] = Order.objects.filter(
        restaurant=self.request.user.restaurant,
        status="PAID"
    ).count()

        return context
    

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            return render(
            self.request,
            "core/partials/orders_container.html",
            context
            )
        return super().render_to_response(context, **response_kwargs)

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "core/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return (
            Order.objects
            .filter(restaurant=self.request.user.restaurant)
            .select_related("table", "session")
            .prefetch_related(
                "items__product",
                "items__variant",
                "items__modifiers",
            )
        )

@login_required
def dashboard_create_order(request, session_id):
    session = get_object_or_404(
        TableSession,
        id=session_id,
        table__restaurant=request.user.restaurant,
        is_active=True
    )

    # ✅ Use your existing factory logic
    order = Order._create_for_session(
        session=session,
        section=session.section,
        created_by=request.user
    )

    return redirect("core:order_detail", pk=order.pk)

class PosOrderScreenTakeoutView(LoginRequiredMixin, TemplateView):
    template_name = "core/direct_takeaway_order.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        restaurant = self.request.user.restaurant

        # Categories
        categories = Category.objects.filter(
            menu__restaurant=restaurant
        ).order_by("name")

        products = Product.objects.filter(
            category__menu__restaurant=restaurant,
            is_available=True
         ).select_related(
            "category"
        ).prefetch_related(
            "modifier_groups__options"
        ).order_by("name").distinct()
        
        # ✅ Active Takeout Orders (not canceled or completed)
        active_orders = Order.objects.filter(
            restaurant=restaurant,
            order_type=Order.OrderType.TAKEOUT,
        ).exclude(
            status__in=[
                Order.Status.CANCELED,
                Order.Status.COMPLETED,
            ]
        ).order_by("-created_at")

        # ✅ Add to context
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
        return (
            Order.objects
            .filter(restaurant=self.request.user.restaurant)
            .select_related("table", "session")
            .prefetch_related("items__product")
        )
        
# ✅ Public Table Menu View
def public_table_menu(request, token):
    table = get_object_or_404(
        Table.objects.select_related("restaurant"),
        access_token=token
    )

    # ✅ Store table in session
    request.session["table_id"] = str(table.id)

    products = (
        Product.objects
        .filter(
            category__menu__restaurant=table.restaurant,
            is_available=True
        )
        .select_related("category")
        .distinct()
    )

    return render(request, "customer/menu.html", {
        "table": table,
        "restaurant": table.restaurant,
        "products": products,
    })


# ✅ Order Status Page View  <-- ADD IT HERE
def table_order_status(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("table", "restaurant"),
        id=order_id
    )

    # ✅ Must have table
    if not order.table:
        return redirect("home")

    # ✅ Verify order belongs to current session table
    if request.session.get("table_id") != str(order.table.id):
        return redirect("home")  # or raise PermissionDenied

    return render(request, "core/table_order_status.html", {
        "order": order
    })
    
# ======================================================================
# ======================== API VIEWSETS ================================
# ======================================================================
class TableViewSet(TenantModelViewSet):
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated, IsStaffOfRestaurant]

    def get_queryset(self):
        restaurant = self.request.user.restaurant

        active_session_subquery = TableSession.objects.filter(
            table=OuterRef("pk"),
            restaurant=restaurant,
            is_active=True
        )

        return (
            Table.objects
            .filter(restaurant=restaurant)
            .annotate(
                has_active_session=Exists(active_session_subquery),
                active_session_id=Subquery(
                    active_session_subquery.values("id")[:1]
                )
            )
            .order_by("table_number")
        )
        
        
class TableCreateView(LoginRequiredMixin, CreateView):
    model = Table
    fields = ["table_number", "capacity"]
    template_name = "core/table_form.html"
    success_url = reverse_lazy("core:tables")

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.restaurant:
            return redirect("core:dashboard")  # or raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
    
class TableUpdateView(LoginRequiredMixin, UpdateView):
    model = Table
    fields = ["table_number", "capacity"]
    template_name = "core/table_form.html"
    success_url = reverse_lazy("core:tables")

    def get_queryset(self):
        return Table.objects.filter(
            restaurant=self.request.user.restaurant
        )

class TableDeleteView(LoginRequiredMixin, DeleteView):
    model = Table
    template_name = "core/table_confirm_delete.html"
    success_url = reverse_lazy("core:tables")

    def get_queryset(self):
        return Table.objects.filter(
            restaurant=self.request.user.restaurant
        )
        
        


class OrderViewSet(TenantModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsStaffOfRestaurant]

    def perform_create(self, serializer):
        order = serializer.save(
            restaurant=self.request.user.restaurant,
            staff=self.request.user
        )

        broadcast_order_update(order)

class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(
            order__restaurant=self.request.user.restaurant
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        ).select_related("menu", "parent").prefetch_related("products")


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
    
    def get_queryset(self):
        return Product.objects.filter(
            category__menu__restaurant=self.request.user.restaurant,
            is_available=True
        ).select_related("category").prefetch_related("modifier_groups__options")
        
        
class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "core/admin/product_form.html"
    success_url = reverse_lazy("core:manage_products")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # ✅ Pass restaurant into form
        kwargs["restaurant"] = self.request.user.restaurant

        return kwargs

class ManagerProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        return Product.objects.filter(
            category__menu__restaurant=self.request.user.restaurant
        )

    def get_object(self):
        return get_object_or_404(
            Product,
            pk=self.kwargs["pk"],
            category__menu__restaurant=self.request.user.restaurant
        )

    def perform_create(self, serializer):
        category = serializer.validated_data["category"]

        # Extra safety check
        if category.menu.restaurant != self.request.user.restaurant:
            raise PermissionDenied("Invalid category for this restaurant.")

        serializer.save()
        


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

        orders = Order.objects.filter(
            restaurant=restaurant,
            status__in=["pending", "preparing"]
        ).order_by("-created_at")

        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)


@login_required
def order_receipt(request, pk):

    if not hasattr(request.user, "restaurant"):
        raise PermissionDenied("No restaurant assigned.")

    order = get_object_or_404(
        Order,
        pk=pk,
        restaurant=request.user.restaurant
    )

    if order.status == "pending":
        order.status = "completed"
        order.save(update_fields=["status"])

        # ✅ Broadcast to Kitchen Display
        channel_layer = get_channel_layer()

        serialized = OrderSerializer(order).data

        async_to_sync(channel_layer.group_send)(
            f"kitchen_{order.restaurant_id}",
            {
                "type": "order_status_update",
                "data": {
                    "type": "new_order",
                    "order": serialized
                }
            }
        )

    return render(request, "orders/order_receipt.html", {
        "order": order
    })
    
def order_status_api(request, order_id):

    table_id = request.session.get("table_id")

    if not table_id:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    order = get_object_or_404(
        Order,
        id=order_id,
        table__id=table_id
    )

    return JsonResponse({
        "status": order.status
    })


@require_POST
def call_waiter_api(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    WaiterCall.objects.create(
        restaurant=table.restaurant,
        table=table
    )

    return JsonResponse({"success": True})

def active_waiter_calls(request):
    calls = WaiterCall.objects.filter(
        restaurant=request.user.restaurant,
        resolved=False
    ).order_by("-created_at")

    return render(request, "dashboard/waiter_calls.html", {"calls": calls})

# ======================================================================
# ======================== PAYMENTS API ================================
# ======================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_qr_payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=request.user.restaurant
    )

    if order.payment_status == Order.PaymentStatus.PAID:
        return Response(
            {"error": "Order already paid"},
            status=400
        )

    intent = create_stripe_payment_intent(order)

    payment, _ = Payment.objects.update_or_create(
        order=order,
        defaults={
            "stripe_payment_intent": intent.id,
            "amount": order.total,
            "status": "PENDING",
        }
    )

    qr_url = request.build_absolute_uri(
        reverse("core:pay_order", args=[order.restaurant.slug, order.id]
        )
    )

    return Response({
        "qr_url": qr_url,
        "client_secret": intent.client_secret
    })
    
def pay_order(request, restaurant_slug, order_id):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)

    # ✅ If already paid, show success page
    if order.payment_status == Order.PaymentStatus.PAID:
        return render(request, "core/payment_success.html", {
            "order": order,
            "restaurant": restaurant
        })

    if request.method == "POST":
        with transaction.atomic():
            order.payment_status = Order.PaymentStatus.PAID
            order.save(update_fields=["payment_status"])
            order.mark_as_placed()

        return redirect(
            "core:payment_success",
            restaurant_slug=restaurant.slug,
            order_id=order.id
        )

    # ✅ Normal GET
    return render(request, "core/pay_order.html", {
        "order": order,
        "restaurant": restaurant,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    })
    
def payment_success(request, restaurant_slug, order_id):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant
    )

    if order.payment_status != Order.PaymentStatus.PAID:
        return redirect("core:pay_order", restaurant_slug=restaurant.slug, order_id=order.id)

    return render(request, "core/payment_success.html", {
        "order": order,
        "restaurant": restaurant
    })
    

@login_required
@transaction.atomic
def refund_order(request, order_id):

    user = request.user

    if not user.is_cashier and not user.is_manager:
        messages.error(request, "You do not have permission to process refunds.")
        return redirect("core:dashboard")

    order = get_object_or_404(Order, id=order_id)

    if order.payment_status != Order.PaymentStatus.PAID:
        messages.error(request, "Order is not paid.")
        return redirect("core:order_detail", order_id=order.id)

    if hasattr(order, "refund_record"):
        messages.error(request, "This order has already been refunded.")
        return redirect("core:order_detail", order_id=order.id)

    # ✅ Require active shift
    active_shift = CashierShift.objects.filter(
        user=user,
        restaurant=user.restaurant,
        is_active=True
    ).first()

    if not active_shift:
        messages.error(request, "No active shift found.")
        return redirect("core:start_shift")

    # ✅ Get all paid payments for this order
    payments = order.payments.filter(status=Payment.Status.PAID)

    if not payments.exists():
        messages.error(request, "No valid payments found.")
        return redirect("core:order_detail", order_id=order.id)

    total_paid = payments.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    # ✅ Create refund record
    refund = Refund.objects.create(
        order=order,
        shift=active_shift,
        amount=total_paid,
        processed_by=user,
    )

    # ✅ Mark payments as refunded
    payments.update(status=Payment.Status.REFUNDED)

    # ✅ Update order status
    order.payment_status = Order.PaymentStatus.REFUNDED
    order.status = Order.Status.CANCELLED
    order.save()

    messages.success(request, "Refund processed successfully.")
    return redirect("core:order_detail", order_id=order.id)



def mock_create_payment_intent(request, restaurant_slug, order_id):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant
    )

    # ✅ Mock payment instead of Stripe
    with transaction.atomic():
        if order.payment_status != Order.PaymentStatus.PAID:
            order.payment_status = Order.PaymentStatus.PAID
            order.save(update_fields=["payment_status"])
            order.mark_as_placed()

    return JsonResponse({
        "success": True
    })

    
class SettingsView(LoginRequiredMixin, UpdateView):
    model = Settings
    template_name = "core/settings.html"
    success_url = reverse_lazy("core:settings")
    fields = [
        # General
        "restaurant_display_name",
        "currency_symbol",
        "timezone",

        # Tax & Charges
        "tax_percentage",
        "service_charge_percentage",
        "prices_include_tax",

        # Order Behavior
        "auto_mark_order_paid",
        "allow_split_payments",
        "allow_table_merge",

        # Receipt
        "show_logo_on_receipt",
        "receipt_footer_text",

        # Inventory
        "stock_alerts_enabled",
        "auto_deduct_inventory",

        # Notifications
        "email_notifications_enabled",
        "send_daily_sales_report",
        "low_stock_email_alerts",
        "notify_on_new_order",

        # UI
        "default_theme",
        "items_per_page",
    ]

    def get_object(self):
        """
        Ensure only restaurant users can edit settings.
        """

        restaurant = getattr(self.request.user, "restaurant", None)

        if not restaurant:
            raise PermissionDenied("SaaS admin cannot edit restaurant settings.")



        settings, created = Settings.objects.get_or_create(
            restaurant=restaurant,
            defaults={
                "restaurant_display_name": restaurant.name,
            }
        )

        return settings
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["settings_tabs"] = [
        "general",
        "tax",
        "orders",
        "receipt",
        "inventory",
        "notifications",
        "ui",
    ]

        context["order_fields"] = [
        "auto_mark_order_paid",
        "allow_split_payments",
        "allow_table_merge",
    ]

        context["inventory_fields"] = [
        "stock_alerts_enabled",
        "auto_deduct_inventory",
    ]

        context["notification_fields"] = [
        "email_notifications_enabled",
        "send_daily_sales_report",
        "low_stock_email_alerts",
        "notify_on_new_order",
    ]

        return context
    
class ManagerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/manager_dashboard.html"
    login_url = "core:login"
    
    def dispatch(self, request, *args, **kwargs):

        # ✅ First: make sure user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # ✅ Then check role
        if request.user.role != CustomUser.Roles.MANAGER:
            return redirect("core:pos_dashboard")

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        orders_today = Order.objects.filter(
            restaurant=self.request.user.restaurant,
            created_at__date=today,
            payment_status=Order.PaymentStatus.PAID,
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

        restaurant = self.request.user.restaurant
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        # ================= ACTIVE ORDERS =================
        active_orders_count = Order.objects.filter(
            restaurant=restaurant,
            status=Order.Status.PLACED
        ).count()

        # ================= TABLES IN USE =================
        tables_in_use = Table.objects.filter(
            restaurant=restaurant,
            status__in=[
                Table.Status.OCCUPIED,
                Table.Status.RESERVED,
            ]
        ).count()

        # ================= TODAY =================
        today_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date=today
        ).count()

        today_revenue = Payment.objects.filter(
            order__restaurant=restaurant,
            created_at__date=today
        ).aggregate(total=Sum("amount"))["total"] or 0

        # ================= YESTERDAY =================
        yesterday_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date=yesterday
        ).count()

        yesterday_revenue = Payment.objects.filter(
            order__restaurant=restaurant,
            created_at__date=yesterday
        ).aggregate(total=Sum("amount"))["total"] or 0

        # ================= WEEK =================
        week_start = today - timedelta(days=today.weekday())
        last_week_start = week_start - timedelta(days=7)
        last_week_end = week_start - timedelta(days=1)

        this_week_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date__gte=week_start
        ).count()

        this_week_revenue = Payment.objects.filter(
            order__restaurant=restaurant,
            created_at__date__gte=week_start
        ).aggregate(total=Sum("amount"))["total"] or 0

        last_week_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date__range=(last_week_start, last_week_end)
        ).count()

        last_week_revenue = Payment.objects.filter(
            order__restaurant=restaurant,
            created_at__date__range=(last_week_start, last_week_end)
        ).aggregate(total=Sum("amount"))["total"] or 0

        # ================= MONTH =================
        month_start = today.replace(day=1)

        monthly_revenue = Payment.objects.filter(
            order__restaurant=restaurant,
            created_at__date__gte=month_start
        ).aggregate(total=Sum("amount"))["total"] or 0

        # ================= TREND CALCULATION =================
        def calculate_trend(current, previous):
            if previous == 0:
                return None, None

            raw_percentage = round(((current - previous) / previous) * 100, 1)

            if raw_percentage > 0:
                direction = "up"
            elif raw_percentage < 0:
                direction = "down"
            else:
                direction = "neutral"

            return abs(raw_percentage), direction

        orders_trend, orders_trend_direction = calculate_trend(
            today_orders, yesterday_orders
        )

        revenue_trend, revenue_trend_direction = calculate_trend(
            today_revenue, yesterday_revenue
        )

        weekly_trend, trend_direction = calculate_trend(
            this_week_orders, last_week_orders
        )

        weekly_revenue_trend, weekly_revenue_trend_direction = calculate_trend(
            this_week_revenue, last_week_revenue
        )

        # ================= DAILY REVENUE (LAST 7 DAYS) =================
        seven_days_ago = today - timedelta(days=6)

        daily_qs = (
            Payment.objects
            .filter(
                order__restaurant=restaurant,
                created_at__date__gte=seven_days_ago
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )

        daily_data_map = {
            item["day"]: float(item["total"] or 0)
            for item in daily_qs
        }

        daily_labels = []
        daily_revenue_data = []

        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            daily_labels.append(day.strftime("%b %d"))
            daily_revenue_data.append(daily_data_map.get(day, 0))

        # ================= HOURLY REVENUE (TODAY) =================
        hourly_qs = (
            Payment.objects
            .filter(
                order__restaurant=restaurant,
                created_at__date=today
            )
            .annotate(hour=TruncHour("created_at"))
            .values("hour")
            .annotate(total=Sum("amount"))
            .order_by("hour")
        )

        hourly_data_map = {
            item["hour"].hour: float(item["total"] or 0)
            for item in hourly_qs
        }

        hourly_labels = []
        hourly_revenue_data = []

        for hour in range(24):
            hourly_labels.append(f"{hour:02d}:00")
            hourly_revenue_data.append(hourly_data_map.get(hour, 0))

        # ================= ACTIVE SESSIONS =================
        active_sessions = (
            TableSession.objects
            .filter(
                restaurant=restaurant,
                is_active=True
            )
            .select_related("table", "section")
        )

        # ================= PAYMENTS =================
        payment_qs = Payment.objects.filter(
            order__restaurant=restaurant
        )

        payment_count = payment_qs.count()

        recent_payments = (
            payment_qs
            .select_related("order")
            .order_by("-created_at")[:10]
        )

        total_sales = payment_qs.aggregate(
            total=Sum("amount")
        )["total"] or 0

        # ================= CONTEXT =================
        context.update({
            "active_orders_count": active_orders_count,
            "tables_in_use": tables_in_use,

            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "today_label": today,
            "yesterday_label": yesterday,

            "orders_trend": orders_trend,
            "orders_trend_direction": orders_trend_direction,
            "revenue_trend": revenue_trend,
            "revenue_trend_direction": revenue_trend_direction,

            "this_week_orders": this_week_orders,
            "weekly_trend": weekly_trend,
            "trend_direction": trend_direction,
            "week_start": week_start,

            "this_week_revenue": this_week_revenue,
            "weekly_revenue_trend": weekly_revenue_trend,
            "weekly_revenue_trend_direction": weekly_revenue_trend_direction,

            "monthly_revenue": monthly_revenue,
            "month_start": month_start,

            "currency": restaurant.currency,

            "daily_labels": json.dumps(daily_labels),
            "daily_revenue_data": json.dumps(daily_revenue_data),
            "hourly_labels": json.dumps(hourly_labels),
            "hourly_revenue_data": json.dumps(hourly_revenue_data),

            "active_sessions": active_sessions,
            "recent_payments": recent_payments,
            "payment_count": payment_count,
            "total_sales": total_sales,
        })

        return context
    


class TableOverviewView(LoginRequiredMixin, TemplateView):
    template_name = "core/tables.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        restaurant = self.request.user.restaurant

        # --------------------------------------------------
        # ✅ Subquery for active session
        # --------------------------------------------------
        active_session_subquery = TableSession.objects.filter(
            table=OuterRef("pk"),
            is_active=True
        )

        # --------------------------------------------------
        # ✅ Tables with session annotations
        # --------------------------------------------------
        tables = (
            Table.objects
            .filter(restaurant=restaurant)
            .annotate(
                has_active_session=Exists(active_session_subquery),
                active_session_id=Subquery(
                    active_session_subquery.values("id")[:1]
                )
            )
            .order_by("table_number")
        )

        # --------------------------------------------------
        # ✅ Active Orders (for dashboard use)
        # --------------------------------------------------
        active_orders = (
            Order.objects
            .filter(
                restaurant=restaurant,
                table__isnull=False,
                status__in=[
                    Order.Status.PLACED,
                    Order.Status.IN_PROGRESS,
                    Order.Status.READY,
                ]
            )
            .select_related("table")
        )

        # --------------------------------------------------
        # ✅ Context
        # --------------------------------------------------
        context.update({
            "tables": tables,
            "active_orders": active_orders,
        })

        return context
    
@login_required
def dashboard_table_open(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
        restaurant=request.user.restaurant
    )

    # Prevent duplicate active table session
    existing_session = TableSession.objects.filter(
        table=table,
        session_type=TableSession.SessionType.TABLE,
        is_active=True
    ).first()

    if existing_session:
        request.session["session_id"] = existing_session.id
        return redirect(
            "core:dashboard_session_detail",
            session_id=existing_session.id
        )

    with transaction.atomic():
        session = TableSession.objects.create(
            restaurant=request.user.restaurant,
            table=table,
            session_type=TableSession.SessionType.TABLE,
            is_active=True
        )

    request.session["session_id"] = session.id

    return redirect(
        "core:dashboard_session_detail",
        session_id=session.id
    )
    
    
@login_required
def create_takeaway_order(request):

    with transaction.atomic():

        session = TableSession.objects.create(
            restaurant=request.user.restaurant,
            session_type=TableSession.SessionType.TAKEAWAY,
            is_active=True
        )

        order = Order.objects.create(
            restaurant=request.user.restaurant,
            session=session,
            created_by=request.user,
            status=Order.Status.DRAFT
        )

    # Store session
    request.session["session_id"] = session.id

    return redirect("core:order_detail", pk=order.pk)

@login_required
def dashboard_session_detail(request, session_id):
    restaurant = request.user.restaurant

    session = get_object_or_404(
        TableSession,
        id=session_id,
        restaurant=restaurant
    )

    orders = Order.objects.filter(
        session=session
    ).order_by("-created_at")

    # ✅ Calculate total revenue for session
    session_total = orders.aggregate(
        total=Coalesce(
            Sum("total"),
            0,
            output_field=DecimalField()
        )
    )["total"]

    # ✅ Calculate total paid amount
    paid_total = orders.filter(
        payment_status=Order.PaymentStatus.PAID
    ).aggregate(
        total=Coalesce(
            Sum("total"),
            0,
            output_field=DecimalField()
        )
    )["total"]

    return render(
        request,
        "dashboard/session_detail.html",
        {
            "session": session,
            "orders": orders,
            "session_total": session_total,
            "paid_total": paid_total,
        }
    )
    
@login_required
def dashboard_table_close(request, session_id):
    session = get_object_or_404(
        TableSession,
        id=session_id,
        restaurant=request.user.restaurant
    )

    if not session.is_fully_paid:
        messages.error(request, "Session is not fully paid.")
        return redirect("core:dashboard_home")

    # ✅ Freeze financial values here
    session.final_subtotal = session.total_amount
    session.final_tax = session.total_tax
    session.final_total = session.total_amount
    session.is_active = False
    session.closed_at = timezone.now()
    session.save()

    # ✅ Redirect directly to receipt PDF
    return redirect(
    reverse("core:session_receipt_print", args=[session.id])
)
    
@login_required
def session_receipt_pdf(request, session_id):
    session = get_object_or_404(
        TableSession,
        id=session_id,
        restaurant=request.user.restaurant
    )

    auto_print = request.GET.get("print") == "true"

    html_string = render_to_string(
        "core/pos/session_receipt_pdf.html",
        {
            "session": session,
            "auto_print": auto_print,
        }
    )

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")

    if auto_print:
        response["Content-Disposition"] = (
            f'inline; filename="session_{session.id}.pdf"'
        )
    else:
        response["Content-Disposition"] = (
            f'attachment; filename="session_{session.id}.pdf"'
        )

    return response

# ======================================================================
# AUTHENTICATION
# ======================================================================


class CustomLoginView(LoginView):
    template_name = "core/registration/login.html"

    def form_valid(self, form):
        messages.success(self.request, "Login successful.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user

        if user.is_superuser:
            return reverse_lazy("admin:index")

        if user.role == CustomUser.Roles.MANAGER:
            return reverse_lazy("core:manager_dashboard")

        if user.role == CustomUser.Roles.CASHIER:
            return reverse_lazy("core:pos_dashboard")

        return reverse_lazy("core:home")
    
def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("core:login")


class PrintQRView(LoginRequiredMixin, DetailView):
    model = Table
    template_name = "core/print_qr.html"
    context_object_name = "table"
    
def regenerate_qr(request, pk):
    table = get_object_or_404(Table, pk=pk)

    # Call your QR generation logic here
    table.generate_qr_code()   # adjust if your method name differs
    table.save()

    messages.success(request, "QR code regenerated successfully.")
    return redirect("core:table_overview")


@login_required
def orders_badge_count(request):
    restaurant = request.user.restaurant
    count = Order.objects.filter(
        restaurant=restaurant
    ).exclude(
        status__in=[Order.Status.COMPLETED, Order.Status.CANCELED]
    ).count()

    return HttpResponse(
        f'<span class="absolute top-2 right-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">{count}</span>'
    )


# =============================================================================
# ✅ KITCHEN DISPLAY (ORDER-BASED)
# =============================================================================

@login_required
def kitchen_display(request):
    restaurant = request.user.restaurant

    if not restaurant:
        return render(request, "core/kitchen/kds.html", {
            "tickets": []
        })

    tickets = (
        KitchenTicket.objects
        .filter(
            order__restaurant=restaurant,
            order__status__in=[
                Order.Status.PLACED,
                Order.Status.IN_PROGRESS,
                Order.Status.READY,
            ]
        )
        .select_related("order", "order__table", "order__created_by")
        .prefetch_related("order__items__product", "order__items__modifiers")
        .order_by("order__created_at")
    )

    return render(request, "core/kitchen/kds.html", {
        "tickets": tickets
    })
    
@login_required
def kitchen_queue_count(request):
    restaurant = request.user.restaurant

    if not restaurant:
        return HttpResponse("")

    count = Order.objects.filter(
        restaurant=restaurant,
        status__in=[
            Order.Status.PLACED,
            Order.Status.IN_PROGRESS,
        ]
    ).count()

    return HttpResponse(
        f'''
        <span class="absolute top-2 right-2 bg-yellow-500 text-black text-xs px-2 py-0.5 rounded-full">
            {count}
        </span>
        '''
    )
    


@login_required
def start_shift(request):

    user = request.user

    # ✅ Only cashiers can start shift
    if not user.is_cashier:
        messages.error(request, "Only cashiers can start a shift.")
        return redirect("core:dashboard")

    # ✅ Prevent duplicate active shift
    existing_shift = CashierShift.objects.filter(
        user=user,
        restaurant=user.restaurant,
        is_active=True
    ).first()

    if existing_shift:
        messages.warning(request, "You already have an active shift.")
        return redirect("core:pos_dashboard")

    if request.method == "POST":
        try:
            starting_cash = Decimal(
                request.POST.get("starting_cash", "0")
            )
        except:
            messages.error(request, "Invalid starting cash amount.")
            return redirect("core:start_shift")

        shift = CashierShift.objects.create(
            user=user,
            restaurant=user.restaurant,
            starting_cash=starting_cash,
            start_time=timezone.now(),
            is_active=True,
        )

        messages.success(request, "Shift started successfully.")
        return redirect("core:pos_dashboard")

    return render(request, "core/cashier_shift/start_shift.html")


@login_required
def end_shift(request):

    user = request.user

    if not user.is_cashier:
        messages.error(request, "Only cashiers can close shifts.")
        return redirect("core:dashboard")

    shift = CashierShift.objects.filter(
        user=user,
        restaurant=user.restaurant,
        is_active=True
    ).first()

    if not shift:
        messages.error(request, "No active shift found.")
        return redirect("core:pos_dashboard")

    if request.method == "POST":

        try:
            closing_cash = Decimal(
                request.POST.get("closing_cash", "0")
            )
        except:
            messages.error(request, "Invalid closing cash amount.")
            return redirect("core:close_shift")

        # ✅ Payments linked to this shift only
        payments = shift.payments.filter(
            status=Payment.Status.PAID
        )

        # ✅ Refunds linked to this shift
        refunds = shift.refunds.all()

        total_sales = payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        total_refunds = refunds.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        net_sales = total_sales - total_refunds

        total_cash_sales = payments.filter(
            method="cash"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        total_card_sales = total_sales - total_cash_sales

        # ✅ Expected physical cash in drawer
        expected_cash = (
            shift.starting_cash
            + total_cash_sales
            - total_refunds
        )

        cash_difference = closing_cash - expected_cash

        # ✅ Update shift
        shift.total_sales = total_sales
        shift.total_cash_sales = total_cash_sales
        shift.total_card_sales = total_card_sales
        shift.total_refunds = total_refunds
        shift.net_sales = net_sales
        shift.closing_cash = closing_cash
        shift.cash_difference = cash_difference
        shift.end_time = timezone.now()
        shift.is_active = False
        shift.save()

        messages.success(request, "Shift closed successfully.")
        return redirect("core:shift_z_report_print", shift.id)

    return render(
        request,
        "core/cashier_shift/end_shift.html",
        {"shift": shift}
    )




@login_required
def shift_z_report_print(request, shift_id):

    shift = get_object_or_404(
        CashierShift,
        id=shift_id,
        restaurant=request.user.restaurant
    )

    return render(
        request,
        "core/cashier_shift/z_report_print.html",
        {"shift": shift}
    )
    
    
    


@login_required
def create_staff(request):
    if not request.user.can_manage_staff:
        raise PermissionDenied("You are not allowed to create staff.")
    
    if request.method == "POST":
        form = StaffCreateForm(request.POST, current_user=request.user)
        if form.is_valid():
            form.save(restaurant=request.user.restaurant)
            return redirect("staff_list")
    else:
        form = StaffCreateForm(current_user=request.user)

    return render(request, "core/create_staff.html", {"form": form})

@login_required
def staff_list(request):
    if not request.user.can_manage_staff:
        raise PermissionDenied()

    staff = User.objects.filter(
        restaurant=request.user.restaurant,
        is_superuser=False,
        is_platform_owner=False
    )
    return render(request, "core/staff_list.html", {
        "staff": staff
    })


@login_required
def manage_products(request):
    user = request.user

    if user.role != user.Roles.MANAGER and not user.is_platform_owner:
        return redirect("core:dashboard")

    restaurant = user.restaurant

    form = ProductForm()
    form.fields["category"].queryset = Category.objects.filter(
        menu__restaurant=restaurant
    )

    return render(
        request,
        "core/admin/products.html",
        {"form": form}
    )
    
@login_required
def print_qr(request, pk):
    table = get_object_or_404(
        Table,
        pk=pk,
        restaurant=request.user.restaurant
    )

    print("PRINT VIEW TABLE ID:", table.id)
    print("PRINT VIEW QR FIELD:", table.qr_code)
    print("PRINT VIEW QR NAME:", table.qr_code.name)
    print("PRINT VIEW QR BOOL:", bool(table.qr_code))

    qr_absolute_url = None
    if table.qr_code:
        qr_absolute_url = request.build_absolute_uri(table.qr_code.url)

    return render(request, "core/print_qr.html", {
        "table": table,
        "qr_absolute_url": qr_absolute_url,
    })
    
    
def print_receipt(request, restaurant_slug, order_id):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant
    )

    if order.payment_status != Order.PaymentStatus.PAID:
        return HttpResponse(status=403)

    # ✅ Force recalculation before printing
    order.calculate_totals()

    return render(request, "core/receipt.html", {
        "order": order,
        "restaurant": restaurant
    })
    

@login_required
def pos_view(request, order_id):

    order = get_object_or_404(
        Order.objects.select_related("restaurant"),
        id=order_id,
        restaurant=request.user.restaurant
    )

    categories = Category.objects.filter(
        menu__restaurant=order.restaurant,
        is_active=True
    )

    variants = ProductVariant.objects.filter(
        product__category__menu__restaurant=order.restaurant,
        product__category__is_active=True
    ).select_related("product")

    category_id = request.GET.get("category")

    if category_id and category_id != "all":
        variants = variants.filter(
            product__category_id=category_id
        )

    return render(request, "core/pos.html", {
        "order": order,
        "variants": variants,
        "categories": categories,
    })
    
@require_POST
@login_required
def add_to_order(request, order_id, variant_id):

    restaurant = request.user.restaurant

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant
    )

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        product__category__menu__restaurant=restaurant
    )

    item, created = OrderItem.objects.get_or_create(
        order=order,
        variant=variant,
        defaults={
            "product": variant.product,
            "quantity": 1,
            "final_price": variant.price
        }
    )

    if not created:
        item.quantity += 1
        item.final_price = variant.price * item.quantity
        item.save()

    return redirect("core:pos", order_id=order.id)

@require_POST
@login_required
@transaction.atomic
def update_quantity(request, order_id, item_id):

    # ✅ Correct restaurant filter
    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=request.user.restaurant
    )

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order=order
    )

    action = request.POST.get("action")

    if action == "increase":
        item.quantity += 1
        item.final_price = item.variant.price * item.quantity
        item.save()

    elif action == "decrease":
        if item.quantity > 1:
            item.quantity -= 1
            item.final_price = item.variant.price * item.quantity
            item.save()
        else:
            item.delete()

    # ✅ Recalculate order totals (important)
    order.refresh_from_db()
    order.calculate_totals()  # if you have this method
    order.save()

    # ✅ Broadcast real-time update
    broadcast_order_update(order)

    return render(request, "core/partials/_order_summary.html", {
        "order": order
    })

@require_POST
@login_required
def remove_item(request, order_id, item_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=request.user.restaurant
    )

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order=order
    )

    item.delete()

    return render(request, "core/partials/_order_summary.html", {
        "order": order
    })
                                                                                                    
    
class ModifierOptionViewSet(ModelViewSet):
    serializer_class = ModifierOptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not hasattr(user, "restaurant") or user.restaurant is None:
            return ModifierOption.objects.none()

        return ModifierOption.objects.filter(
            group__products__category__menu__restaurant=user.restaurant
        ).distinct()
        
    def perform_create(self, serializer):
        option = serializer.save()

        # Security check: prevent cross-restaurant linking
        if not option.group.products.filter(
            category__menu__restaurant=self.request.user.restaurant
        ).exists():
            option.delete()  # rollback
            raise PermissionDenied("Invalid restaurant access.")
        
def public_display(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, display_token=token, is_active=True)
    return render(
        request,
        "core/pos/public_display.html",
        {"restaurant": restaurant}
    )


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = ["name", "description", "display_order"]
    template_name = "core/partials/category_form.html"

    def form_valid(self, form):
        menu = Menu.objects.filter(
            restaurant=self.request.user.restaurant
        ).first()

        if not menu:
            return HttpResponseBadRequest("No menu found.")

        form.instance.menu = menu
        form.save()

        # ✅ Return updated table instead of redirect
        categories = (
            Category.objects
            .filter(menu__restaurant=self.request.user.restaurant)
            .annotate(product_count=Count("products"))
            .order_by("display_order", "name")
        )

        response = render(
            self.request,
            "core/partials/category_table.html",
            {"categories": categories}
        )

        # ✅ Tell HTMX to replace the table
        response["HX-Target"] = "#category-table"
        response["HX-Swap"] = "innerHTML"

        return response

    def form_invalid(self, form):
        return render(
            self.request,
            "core/partials/category_form.html",
            {"form": form}
        )
    
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "dashboard/categories.html"
    context_object_name = "categories"

    def get_queryset(self):
        return (
            Category.objects
            .filter(menu__restaurant=self.request.user.restaurant)
            .annotate(product_count=Count("products"))
            .order_by("display_order", "name")
        )
    
class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    fields = ["name", "description", "display_order", "is_active"]
    template_name = "core/partials/category_form.html"
    success_url = reverse_lazy("core:category_list")

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        )
        
class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = "core/dashboard/category_confirm_delete.html"
    success_url = reverse_lazy("core:category_list")

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.product_set.exists():
            return HttpResponseBadRequest(
                "Cannot delete category with products."
            )

        return super().delete(request, *args, **kwargs)
    
        
class UpdateCategoryOrderView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

        with transaction.atomic():
            for item in data:
                Category.objects.filter(
                    id=item.get("id"),
                    menu__restaurant=request.user.restaurant
                ).update(display_order=item.get("position", 0))

        return JsonResponse({"status": "ok"})
        


@transaction.atomic
def register_restaurant(request):
    if request.method == "POST":
        form = RestaurantRegistrationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            restaurant_name = form.cleaned_data["restaurant_name"]

            # ✅ 1. Create Company
            company = Company.objects.create(
                name=restaurant_name
            )

            # ✅ 2. Create Restaurant
            restaurant = Restaurant.objects.create(
                company=company,
                name=restaurant_name,
                address_line_1="Not Provided",
                city="Not Provided",
                country="Not Provided",
                timezone="UTC",
                currency="USD",
            )

            # ✅ 3. Create User
            user = CustomUser(
                username=email,
                email=email,
                role=CustomUser.Roles.MANAGER,
                restaurant=restaurant,
            )
            user.set_password(password)
            user.save()

            # ✅ 4. Create Trial Subscription
            Subscription.objects.create(
                restaurant=restaurant,
                plan_name="Trial",
                end_date=now().date() + timedelta(days=14)
            )

            login(request, user)

            return redirect("core:dashboard")

    else:
        form = RestaurantRegistrationForm()

    return render(request, "core/register.html", {"form": form})

def subscription_expired(request):
    return render(request, "core/subscription_expired.html")