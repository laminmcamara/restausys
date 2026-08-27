# core/views.py

import uuid, csv, json
from datetime import timedelta, datetime
from django.http import HttpResponseForbidden

from django.contrib.auth.views import LoginView, LogoutView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import qrcode

from io import BytesIO
from .utils import get_accessible_restaurants
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
from django.utils.dateparse import parse_date
from django.views import View
from .forms import StaffCreateForm
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import (
    TemplateView, ListView, DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    

)
from core.mixins import (
    RestaurantScopedMixin,
    SubscriptionRequiredMixin,
)
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.db.models import Sum, Count, Avg, Prefetch, Exists, OuterRef, Subquery, DecimalField
from django.db.models.functions import TruncDate, TruncHour, Coalesce
from core.utils import has_active_subscription
from .webhook_utils import trigger_outbound_webhook  # Import the utility

from decimal import Decimal
from django.conf import settings
import random

from openpyxl import Workbook

# DRF
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .permissions import IsOwnerOrManager
from django.core.serializers.json import DjangoJSONEncoder

from rest_framework.decorators import api_view, permission_classes, action
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
from rest_framework import viewsets, permissions
from .models import Printer, PrintJob
from .serializers import PrinterSerializer, PrintJobSerializer
from core.services.printer_service import create_kitchen_print_job
# CORE IMPORTS
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (Company, 
    Order, OrderItem, Category, Product,
    Table, TableSession, Payment, KitchenTicket, Settings, ModifierGroup, ModifierOption, Restaurant, ProductVariant, CustomUser, Menu, InventoryItem, CashierShift, Subscription, Customer, Plan, WebhookConfiguration

)
from .serializers import (
    OrderSerializer, OrderItemSerializer,
    CategorySerializer, ProductSerializer,
    TableSerializer, PaymentSerializer, CustomUserSerializer, MenuSerializer, ModifierOptionSerializer,  ModifierGroupSerializer, SubscriptionSerializer, MenuSerializer, SettingsSerializer, StaffUserSerializer,
    StaffCreateSerializer,
    StaffUpdateSerializer,
    CustomerSerializer,
    InventoryItemSerializer,
    DiscountSerializer,
    ChangePasswordSerializer,
    WebhookConfigurationSerializer,
 
)

import secrets
from .permissions import IsStaffOfRestaurant, HasActiveSubscription
from django.contrib.auth import get_user_model
from .models import Subscription
from django.utils.timezone import now
from asgiref.sync import async_to_sync
from django.db.models.functions import ExtractHour
from django.db import transaction
import stripe
from django.core.files.base import ContentFile

from django.contrib.auth import login
from .forms import RestaurantRegistrationForm

User = get_user_model()


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .decorators import subscription_required
from django.views.decorators.csrf import csrf_protect

ACTION_STATUS_MAP = {
    "placed": Order.Status.PLACED,
    "start": Order.Status.IN_PROGRESS,
    "ready": Order.Status.READY,
    "served": Order.Status.SERVED,
    "complete": Order.Status.COMPLETED,
}

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

    # ✅ Safety check (important for tests / migrations)
    if not channel_layer:
        return

    try:
        serialized = OrderSerializer(order).data

        payload = {
            "event": "ORDER_STATUS_UPDATED",
            "order": serialized,
        }

        message = {
            "type": "order_status_update",  # must match consumer method
            "data": payload,
        }

        restaurant_id = order.restaurant_id

        groups = [
            f"pos_{restaurant_id}",
            f"kitchen_{restaurant_id}",
            f"restaurant_{restaurant_id}",
            f"customer_{restaurant_id}",
        ]

        # ✅ Add table group if exists
        if order.table_id:
            groups.append(f"table_{order.table_id}")

        for group in groups:
            async_to_sync(channel_layer.group_send)(group, message)

    except ImproperlyConfigured:
        # Channels not configured (safe fallback)
        pass

    except Exception as e:
        # Optional: log error instead of crashing request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"WebSocket broadcast failed: {str(e)}")
        
        
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

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = CustomUserSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"detail": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        update_session_auth_hash(request, user)

        return Response({"detail": "Password changed successfully"})
    
    
@api_view(["GET"])
@permission_classes([AllowAny])
def api_home(request):
    return Response({
        "message": "Restaurant Management API",
        "status": "ok",
        "version": "v1",
        "endpoints": {
            "auth": {
                "token": "/api/token/",
                "refresh": "/api/token/refresh/",
                "me": "/api/me/",
            },
            "api": "/api/v1/",
            "public_menus": "/api/v1/public/<restaurant_id>/menus/",
            "subscription": "/api/subscription/",
        }
    })
    
# ======================================================================
# POS DASHBOARD (ROLE-DRIVEN + PROTECTED)
# ======================================================================

    
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

    if action not in ACTION_STATUS_MAP:
        return Response({"error": "Invalid action"}, status=400)

    try:
        new_status = ACTION_STATUS_MAP[action]
        order.transition_to(new_status, actor=request.user)

    except (ValidationError, PermissionDenied, ValueError) as e:
        return Response({"error": str(e)}, status=400)

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
@subscription_required
def create_order_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items")
    order_id = data.get("order_id")

    if not isinstance(items, list) or not order_id:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    restaurant = request.user.restaurant

    MAX_QTY_PER_ITEM = 100  # Prevent abuse

    with transaction.atomic():

        # ✅ Lock the order row to prevent race conditions
        try:
            order = Order.objects.select_for_update().get(
                id=order_id,
                restaurant=restaurant
            )
        except Order.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        # ✅ Explicit status validation (double-submit protection)
        if order.status != Order.Status.DRAFT:
            return JsonResponse(
                {"error": "Order already processed"},
                status=400
            )

        if not items:
            return JsonResponse(
                {"error": "Order cannot be empty"},
                status=400
            )

        # ✅ Reset items safely
        order.items.all().delete()

        total = 0
        created_items = 0

        for item in items:
            variant_id = item.get("variantId")
            qty = item.get("qty")

            if not variant_id:
                continue

            try:
                qty = int(qty)
            except (TypeError, ValueError):
                continue

            if qty <= 0 or qty > MAX_QTY_PER_ITEM:
                continue

            try:
                variant = ProductVariant.objects.select_related("product").get(
                    id=variant_id,
                    product__category__menu__restaurant=restaurant
                )
            except ProductVariant.DoesNotExist:
                continue

            unit_price = variant.price
            line_total = unit_price * qty

            OrderItem.objects.create(
                order=order,
                product=variant.product,
                variant=variant,
                quantity=qty,
                final_price=unit_price  # ✅ server authoritative price
            )

            total += line_total
            created_items += 1

        if created_items == 0:
            return JsonResponse(
                {"error": "No valid items provided"},
                status=400
            )

        order.total = total
        order.save(update_fields=["total"])

        # ✅ Transition state after items & total are valid
        order.transition_to(Order.Status.PLACED, actor=request.user)

    return JsonResponse({
        "order_id": str(order.id),
        "total": str(total),
        "status": order.status,
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
        statuses = self.request.GET.getlist("status")
        payment = self.request.GET.get("payment")

        if q:
            queryset = queryset.filter(id__icontains=q)

        if statuses:
            queryset = queryset.filter(status__in=statuses)

        if payment:
            queryset = queryset.filter(payment_method=payment)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        today_orders = Order.objects.filter(
            restaurant=self.request.user.restaurant,
            created_at__date=today
        )

        context["today_sales"] = (
            today_orders
            .filter(status="PAID")
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Categories belonging to restaurants the user is assigned to
        context["categories"] = Category.objects.filter(
            restaurant=self.request.user.restaurant 
        )

        # Available products from those restaurants
        context["products"] = (
            Product.objects
            .filter(
                category__menu__restaurant=self.request.user.restaurant,
                is_available=True
            )
            .select_related("category")
        )

        return context
    
@login_required
@require_POST
@transaction.atomic
def add_order_item(request, order_id, product_id):
    order = get_object_or_404(Order, id=order_id)
    product = get_object_or_404(Product, id=product_id)

    item, created = OrderItem.objects.get_or_create(
        order=order,
        product=product,
        defaults={
            "quantity": 1
        }
    )

    if not created:
        item.quantity += 1
        item.save()   # ✅ triggers your custom save()

    return redirect("core:order_detail", pk=order.id)

@require_POST
@login_required
@subscription_required
def create_draft_order_api(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    restaurant = request.user.restaurant
    session_id = data.get("session_id")
    order_type = data.get("order_type", Order.Type.TAKEAWAY)
    notes = data.get("notes", "")

    with transaction.atomic():

        session = None
        section = None

        if session_id:
            session = get_object_or_404(
                TableSession.objects.select_for_update(),
                id=session_id,
                table__restaurant=restaurant,
                is_active=True
            )
            section = session.section
            order_type = Order.Type.DINE_IN

        active_shift = Shift.objects.filter(
            restaurant=restaurant,
            ended_at__isnull=True
        ).first()

        order = Order.objects.create(
            restaurant=restaurant,
            created_by=request.user,
            status=Order.Status.DRAFT,
            type=order_type,
            table=session.table if session else None,
            session=session,
            section=section,
            shift=active_shift,
            notes=notes,
            total=0
        )

    return JsonResponse({
        "order_id": str(order.id),
        "status": order.status,
        "type": order.type,
    })

class PosOrderScreenTakeoutView(LoginRequiredMixin, TemplateView):
    template_name = "core/direct_takeaway_order.html"
    
    
class OrderSuccessView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "core/order_success.html"
    context_object_name = "order"
    pk_url_kwarg = "order_id"

    def get_queryset(self):
        return (
            Order.objects
            .filter(
                restaurant=self.request.user.restaurant,
                status__in=[
                    Order.Status.PLACED,
                    Order.Status.PAID,
                    Order.Status.COMPLETED,
                ]
            )
            .select_related("table", "session")
            .prefetch_related("items__product")
        )
        
# ✅ Public Table Menu View
def public_table_menu(request, token):
    table = get_object_or_404(
        Table.objects.select_related("restaurant"),
        access_token=token
    )

    if not table.is_active:
        return render(request, "customer/qr_expired.html")

    now = timezone.now()

    # ✅ Bind table securely to session
    request.session["table_id"] = str(table.id)
    request.session["table_token"] = token
    request.session["qr_expires_at"] = (
        now + timedelta(hours=3)
    ).isoformat()

    # ✅ Idempotency token
    nonce = uuid.uuid4().hex
    request.session["qr_nonce"] = nonce
    request.session.modified = True

    products = (
        Product.objects
        .filter(
            category__menu__restaurant=table.restaurant,
            is_available=True
        )
        .select_related("category")
        .prefetch_related("modifier_groups__options")
        .distinct()
    )

    return render(request, "customer/menu.html", {
        "table": table,
        "restaurant": table.restaurant,
        "products": products,
        "qr_nonce": nonce,
    })
    
    
# ✅ Order Status Page View  <-- ADD IT HERE
def table_order_status(request, token, order_id):

    if not validate_qr_session(request, token):
        return render(request, "customer/session_expired.html")

    table = get_object_or_404(
        Table.objects.select_related("restaurant"),
        access_token=token,
        is_active=True
    )

    order = get_object_or_404(
        Order.objects.select_related("table", "restaurant"),
        id=order_id,
        table=table,  # ✅ Must belong to this table
        restaurant=table.restaurant,
        status__in=[
            Order.Status.PLACED,
            Order.Status.PAID,
            Order.Status.COMPLETED,
        ]
    )

    # ✅ Extra safety: session match
    if request.session.get("table_id") != str(table.id):
        return redirect("home")

    return render(request, "core/table_order_status.html", {
        "order": order
    })
    
    
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@require_POST
@csrf_protect  # ✅ keep CSRF enabled
def table_cart_api(request, token):

    if not validate_qr_session(request, token):
        return JsonResponse({"error": "QR session expired."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    product_id = data.get("item_id")
    quantity = data.get("quantity")

    if not product_id:
        return JsonResponse({"error": "Missing product."}, status=400)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid quantity."}, status=400)

    if quantity <= 0:
        return JsonResponse({"error": "Quantity must be positive."}, status=400)

    MAX_QTY_PER_ITEM = 50
    if quantity > MAX_QTY_PER_ITEM:
        return JsonResponse({"error": "Quantity too large."}, status=400)

    # ✅ Get table from token
    table = get_object_or_404(
        Table.objects.select_related("restaurant"),
        access_token=token,
        is_active=True
    )

    # ✅ Validate product belongs to restaurant
    product = get_object_or_404(
        Product,
        id=product_id,
        category__menu__restaurant=table.restaurant,
        is_available=True
    )

    cart = request.session.get("cart", {})

    product_id = str(product.id)

    new_qty = cart.get(product_id, 0) + quantity

    if new_qty > MAX_QTY_PER_ITEM:
        return JsonResponse({"error": "Too many items in cart."}, status=400)

    cart[product_id] = new_qty

    request.session["cart"] = cart
    request.session.modified = True

    return JsonResponse({
        "cart_count": sum(cart.values())
    })


def table_checkout(request, token):

    if not validate_qr_session(request, token):
        return render(request, "customer/session_expired.html")

    table = get_object_or_404(
        Table.objects.select_related("restaurant"),
        access_token=token,
        is_active=True
    )

    cart = request.session.get("cart", {})

    if not cart:
        return redirect("public_table_menu", token=token)

    cart_items = []
    total = 0

    MAX_QTY_PER_ITEM = 50

    for product_id, quantity in cart.items():

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue

        if quantity <= 0 or quantity > MAX_QTY_PER_ITEM:
            continue

        try:
            product = Product.objects.get(
                id=product_id,
                category__menu__restaurant=table.restaurant,
                is_available=True
            )
        except Product.DoesNotExist:
            continue

        item_total = product.price * quantity
        total += item_total

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "total": item_total
        })

    if not cart_items:
        return redirect("public_table_menu", token=token)

    return render(request, "core/table_checkout.html", {
        "table": table,
        "cart_items": cart_items,
        "total": total
    })
    
    
class PlaceOrderAPIView(APIView):
    """
    API View to handle order placement from the POS.
    It manages Table Sessions, Order Items, and Modifiers in a single transaction.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        table_id = data.get("table_id")
        items = data.get("items", [])

        if not items:
            return Response(
                {"error": "Cannot place an empty order."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # We wrap only the database logic in the transaction
            with transaction.atomic():
                # 1. Verify Table and Restaurant ownership
                table = Table.objects.select_for_update().get(
                    id=table_id, 
                    restaurant=request.user.restaurant
                )

                # 2. Get or Create an Active Session
                session = TableSession.objects.filter(
                    table=table, 
                    is_active=True,
                    restaurant=request.user.restaurant
                ).first()

                if not session:
                    session = TableSession.objects.create(
                        table=table,
                        restaurant=request.user.restaurant,
                        is_active=True,
                        opened_by=request.user
                    )
                    table.status = "OCCUPIED"
                    table.save(update_fields=['status'])

                # 3. Create the Order
                order = Order.objects.create(
                    restaurant=request.user.restaurant,
                    table=table,
                    session=session,
                    status="PLACED",
                    created_by=request.user,
                    payment_status="PENDING"
                )

                # 4. Process Order Items
                for item_data in items:
                    product_id = item_data.get('product_id')
                    quantity = int(item_data.get('quantity', 1))
                    modifier_ids = item_data.get('modifier_option_ids', [])
                    
                    order_item = OrderItem.objects.create(
                        order=order,
                        product_id=product_id,
                        quantity=quantity,
                        status="QUEUED"
                    )

                    if modifier_ids:
                        order_item.modifiers.set(modifier_ids)

                    order_item.recalculate_price()

                # 5. Finalize Order Totals
                order.calculate_totals()

            # ===========================================================
            # WEBHOOK TRIGGER (Outside the transaction block)
            # ===========================================================
            # Prepare the payload for the external developer
            webhook_payload = {
                "order_id": str(order.id),
                "order_number": order.order_number if hasattr(order, 'order_number') else order.id,
                "total_amount": float(order.total),
                "table_name": table.name,
                "status": order.status,
                "items_count": len(items)
            }

            trigger_outbound_webhook(
                restaurant=request.user.restaurant,
                event_type="order.placed",
                payload=webhook_payload
            )
            # ===========================================================

            return Response({
                "message": "Order placed successfully",
                "order_id": order.id,
                "order_number": order.order_number if hasattr(order, 'order_number') else order.id,
                "session_id": session.id
            }, status=status.HTTP_201_CREATED)

        except Table.DoesNotExist:
            return Response({"error": "Table not found."}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return Response({"error": "One or more products not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Order Placement Error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
# ======================================================================
# ======================== API VIEWSETS ================================
# ======================================================================
class TableViewSet(TenantModelViewSet):
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated, IsStaffOfRestaurant]

    def get_queryset(self):
        user = self.request.user

        # 1. Handle Superuser (Admin) Logic
        if user.is_superuser:
            restaurant_id = self.request.query_params.get("restaurant")
            tables = Table.objects.all()
        
        # If no specific restaurant is requested, you might want to return 
        # nothing or only the superuser's own restaurant to prevent clutter
            if restaurant_id:
                tables = tables.filter(restaurant_id=restaurant_id)
        
        # Add annotations
            active_session_qs = TableSession.objects.filter(table=OuterRef("pk"), is_active=True)
            return tables.annotate(
                has_active_session=Exists(active_session_qs),
                active_session_id=Subquery(active_session_qs.values("id")[:1])
            ).order_by("restaurant_id", "table_number")

    # 2. Handle Standard Restaurant Staff/Managers
    # Use the restaurant associated with the user profile
        restaurant = getattr(user, "restaurant", None)

        if not restaurant:
        # If the user isn't assigned to a restaurant, they see NOTHING
            return Table.objects.none()

    # Strict filtering by the user's assigned restaurant
        active_session_qs = TableSession.objects.filter(
            table=OuterRef("pk"),
            restaurant=restaurant,
            is_active=True
        )

        return (
            Table.objects
            .filter(restaurant=restaurant) # This is the isolation barrier
            .annotate(
                has_active_session=Exists(active_session_qs),
                active_session_id=Subquery(active_session_qs.values("id")[:1])
            )
            .order_by("table_number")
        )


    @action(detail=True, methods=["post"])
    def generate_qr(self, request, pk=None):
        table = self.get_object()

        qr_url = f"http://127.0.0.1:3000/menu/{table.id}"

        qr = qrcode.make(qr_url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        file_name = f"table_{table.id}_qr.png"

        table.qr_code.save(
            file_name,
            ContentFile(buffer.getvalue()),
            save=True
        )

        return Response({"message": "QR generated successfully"})
    
    
# TODO: Remove when staff dashboard fully API-driven      
class TableCreateView(LoginRequiredMixin, CreateView):
    model = Table
    fields = ["table_number", "capacity"]
    template_name = "core/table_form.html"
    success_url = reverse_lazy("core:tables")

    def dispatch(self, request, *args, **kwargs):
        # Cache restaurant once
        self.restaurant = Restaurant.objects.filter(
            users=request.user
        ).first()

        if not self.restaurant:
            return redirect("core:dashboard")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.restaurant = self.restaurant
        return super().form_valid(form)
    
    
# TODO: Remove when staff dashboard fully API-driven      
class TableUpdateView(LoginRequiredMixin, UpdateView):
    model = Table
    fields = ["table_number", "capacity"]
    template_name = "core/table_form.html"
    success_url = reverse_lazy("core:tables")

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "restaurant"):
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Table.objects.filter(
            restaurant=self.request.user.restaurant
        )
        
        
class TableDeleteView(LoginRequiredMixin, DeleteView):
    model = Table
    template_name = "core/table_confirm_delete.html"
    success_url = reverse_lazy("core:tables")

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "restaurant"):
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Table.objects.filter(
            restaurant=self.request.user.restaurant
        )



class OrderViewSet(TenantModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsStaffOfRestaurant]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["table", "status"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    # -------------------------------------------------
    # ✅ QUERYSET (TENANT SAFE)
    # -------------------------------------------------

    def get_queryset(self):
        restaurants = get_accessible_restaurants(self.request.user)
        user = self.request.user

        qs = Order.objects.select_related(
            "restaurant",
            "table",
            "session",
            "created_by",
        ).prefetch_related(
            "items",
            "items__product",
            "items__modifiers",
        ).order_by("-created_at")

        if user.is_superuser:
            return qs

        restaurant = getattr(user, "restaurant", None)

        if restaurant is None:
            return Order.objects.none()

        return qs.filter(restaurant=restaurant)

    # -------------------------------------------------
    # ✅ CREATE ORDER
    # -------------------------------------------------

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_superuser:
            table = serializer.validated_data.get("table")
            restaurant = serializer.validated_data.get("restaurant", None)

            if restaurant is None and table is not None:
                restaurant = table.restaurant

            if restaurant is None:
                raise PermissionDenied("Restaurant or table required for superuser.")
        else:
            restaurant = getattr(user, "restaurant", None)

            if not restaurant:
                raise PermissionDenied("No restaurant assigned.")

        order = serializer.save(
            restaurant=restaurant,
            created_by=user
        )

        broadcast_order_update(order)
        
        
    # -------------------------------------------------
    # ✅ OPEN OR CREATE DRAFT ORDER
    # -------------------------------------------------

    @action(detail=False, methods=["post"])
    def open_or_create(self, request):
        table_id = request.data.get("table_id") or request.data.get("table")

        if not table_id:
            return Response(
                {"error": "table_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        if user.is_superuser:
            # For superuser, derive the restaurant from the selected table.
            table = get_object_or_404(
                Table.objects.select_related("restaurant"),
                id=table_id,
            )
            restaurant = table.restaurant
        else:
            restaurant = getattr(user, "restaurant", None)

            if not restaurant:
                return Response(
                    {"error": "No restaurant assigned."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Tenant safety: non-superusers can only open orders for their own restaurant tables.
            table = get_object_or_404(
                Table,
                id=table_id,
                restaurant=restaurant
            )

        # Check existing draft order for this table
        order = Order.objects.filter(
            table=table,
            restaurant=restaurant,
            status=Order.Status.DRAFT
        ).first()

        if order:
            serializer = self.get_serializer(order)
            return Response(serializer.data)

        # Ensure active table session
        session, _ = TableSession.objects.get_or_create(
            table=table,
            restaurant=restaurant,
            is_active=True,
            defaults={
                "opened_by": user,
            } if any(f.name == "opened_by" for f in TableSession._meta.fields) else {}
        )

        # Create new draft order
        order = Order.objects.create(
            restaurant=restaurant,
            table=table,
            session=session,
            order_type=Order.OrderType.DINE_IN,
            status=Order.Status.DRAFT,
            created_by=user,
        )

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # -------------------------------------------------
    # ✅ SEND TO KITCHEN (DRAFT → PLACED + CREATE PRINT JOB)
    # -------------------------------------------------

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def send_to_kitchen(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.Status.DRAFT:
            return Response(
                {"error": "Only draft orders can be sent to kitchen."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Recalculate saved backend totals before sending to kitchen
        order.calculate_totals()
        order.refresh_from_db()

        # Move order from DRAFT to PLACED
        order.transition_to(Order.Status.PLACED, actor=request.user)
        order.refresh_from_db()

        # Create kitchen print job
        print_job = create_kitchen_print_job(order)

        # Broadcast update to POS/Kitchen dashboards
        broadcast_order_update(order)

        serializer = self.get_serializer(order)
        data = serializer.data

        # Optional extra info for frontend/debugging
        data["print_job_id"] = print_job.id
        data["printer"] = str(print_job.printer) if print_job.printer else None

        return Response(data)

    # -------------------------------------------------
    # ✅ KITCHEN: START PREPARING (PLACED → IN_PROGRESS)
    # -------------------------------------------------

    @action(detail=True, methods=["post"])
    def start_preparing(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.Status.PLACED:
            return Response(
                {"error": "Only placed orders can start preparation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.transition_to(Order.Status.IN_PROGRESS, actor=request.user)

        broadcast_order_update(order)

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    # -------------------------------------------------
    # ✅ KITCHEN: MARK READY (IN_PROGRESS → READY)
    # -------------------------------------------------

    @action(detail=True, methods=["post"])
    def mark_ready(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.Status.IN_PROGRESS:
            return Response(
                {"error": "Order must be in progress."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.transition_to(Order.Status.READY, actor=request.user)

        broadcast_order_update(order)

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    # -------------------------------------------------
    # ✅ PICKUP: MARK SERVED (READY → SERVED)
    # -------------------------------------------------

    @action(detail=True, methods=["post"])
    def mark_served(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.Status.READY:
            return Response(
                {"error": "Order must be ready first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.transition_to(Order.Status.SERVED, actor=request.user)

        broadcast_order_update(order)

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    # -------------------------------------------------
    # ✅ MANAGER: MARK PAID (PAYMENT ONLY)
    # -------------------------------------------------

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        order = self.get_object()

        if order.payment_status == Order.PaymentStatus.PAID:
            return Response(
                {"error": "Order already paid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.mark_as_paid(actor=request.user)

        broadcast_order_update(order)

        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    
class MarkOrderPaidView(APIView):
    """
    POST /api/v1/orders/<order_id>/mark-paid/
    Marks an order as paid and triggers an outbound webhook.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        # Assuming get_user_restaurant is a helper you have defined
        from .utils import get_user_restaurant 
        
        restaurant = get_user_restaurant(request.user)
        if not restaurant:
            return Response(
                {"detail": "No restaurant associated with your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(id=order_id, restaurant=restaurant)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payment_method = request.data.get("payment_method", "cash")

        # Validate payment method
        valid_methods = ["cash", "card", "mobile", "online"]
        if payment_method not in valid_methods:
            return Response(
                {"detail": f"Invalid payment method. Use: {', '.join(valid_methods)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use a transaction to ensure data integrity
        with transaction.atomic():
            # Create or update the payment record
            payment, created = Payment.objects.get_or_create(
                order=order,
                restaurant=restaurant,
                defaults={
                    "amount": order.total,
                    "payment_method": payment_method,
                    "status": "paid",
                },
            )

            if not created:
                payment.status = "paid"
                payment.payment_method = payment_method
                payment.save()

            # Update order status
            if hasattr(order, "status"):
                order.status = "paid"
                order.save()

            # ===========================================================
            # WEBHOOK TRIGGER (Scheduled to run after DB commit)
            # ===========================================================
            webhook_payload = {
                "order_id": str(order.id),
                "order_number": getattr(order, 'order_number', order.id),
                "amount": float(order.total),
                "payment_method": payment_method,
                "paid_at": payment.updated_at.isoformat() if hasattr(payment, 'updated_at') else None
            }

            # transaction.on_commit ensures we don't send the webhook 
            # if the database transaction rolls back.
            transaction.on_commit(lambda: trigger_outbound_webhook(
                restaurant=restaurant,
                event_type="order.paid",
                payload=webhook_payload
            ))
            # ===========================================================

        return Response(
            {
                "detail": "Order marked as paid.", 
                "order_id": order.id, 
                "payment_method": payment_method
            },
            status=status.HTTP_200_OK,
        )
        
        
class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = OrderItem.objects.select_related(
            "order",
            "order__restaurant",
            "product",
        ).prefetch_related("modifiers")

        if user.is_superuser:
            return qs

        restaurant = getattr(user, "restaurant", None)

        if restaurant is None:
            return OrderItem.objects.none()

        return qs.filter(order__restaurant=restaurant)

    def perform_create(self, serializer):
        user = self.request.user
        order_id = self.request.data.get("order")

        if not order_id:
            raise ValidationError({"order": "Order ID is required."})

        if user.is_superuser:
            order = get_object_or_404(
                Order,
                id=order_id,
            )
        else:
            restaurant = getattr(user, "restaurant", None)

            if restaurant is None:
                raise PermissionDenied("No restaurant assigned.")

            order = get_object_or_404(
                Order,
                id=order_id,
                restaurant=restaurant,
            )

        item = serializer.save(order=order)

        order.calculate_totals()

    def perform_update(self, serializer):
        item = serializer.save()

        # Recalculate order totals after changing quantity/item fields
        item.order.calculate_totals()

    def perform_destroy(self, instance):
        order = instance.order
        instance.delete()

        # Recalculate order totals after removing an item
        order.calculate_totals()
        
        
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Category.objects
            .filter(
                is_active=True,
                menu__is_active=True,
                menu__restaurant__company__active=True,
            )
            .select_related(
                "menu",
                "parent",
                "menu__restaurant",
                "menu__restaurant__company",
            )
            .prefetch_related("products")
            .order_by("display_order", "name")
        )

        if user.is_superuser:
            return qs

        return qs.filter(
            menu__restaurant__company__owner=user
        )

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Product.objects
            .filter(
                is_available=True,
                category__is_active=True,
                category__menu__is_active=True,
            )
            .select_related("category", "category__menu")
            .prefetch_related("modifier_groups__options")
            .order_by("category__display_order", "display_order", "name")
        )

        if user.is_superuser:
            return qs

        restaurant = getattr(user, "restaurant", None)

        if restaurant is None:
            return Product.objects.none()

        return qs.filter(category__menu__restaurant=restaurant)
    

class ManagerCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        ).order_by("display_order", "name")

    def perform_create(self, serializer):
        restaurant = self.request.user.restaurant

        menu = serializer.validated_data.get("menu")

        if menu:
            if menu.restaurant != restaurant:
                raise PermissionDenied(
                    "You cannot add categories to another restaurant's menu."
                )
        else:
            menu = Menu.objects.filter(
                restaurant=restaurant
            ).first()

            if not menu:
                menu = Menu.objects.create(
                    restaurant=restaurant,
                    name="Default Menu"
                )

        serializer.save(menu=menu)
    
# ==============================================================
# ================== PRODUCT DELETE ============================
# ==============================================================


    

        
class ManagerProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [
        IsAuthenticated,
        IsOwnerOrManager,
    ]

    def get_queryset(self):
        restaurant = self.request.user.restaurant
        return Product.objects.filter(
            category__menu__restaurant=restaurant
        )

    def perform_create(self, serializer):
        category = serializer.validated_data["category"]
        restaurant = self.request.user.restaurant

        # ✅ Strong tenant isolation
        if category.menu.restaurant != restaurant:
            raise PermissionDenied("Invalid category for this restaurant.")

        serializer.save()

class ManagerMenuViewSet(viewsets.ModelViewSet):
    serializer_class = MenuSerializer
    permission_classes = [
        IsAuthenticated,
        IsOwnerOrManager,
    ]

    def get_queryset(self):
        restaurant = self.request.user.restaurant

        return (
            Menu.objects
            .filter(restaurant=restaurant)
            .prefetch_related(
                "categories",
                "categories__products",
                "categories__products__modifier_groups",
                "categories__products__modifier_groups__options",
            )
        )

    def perform_create(self, serializer):
        restaurant = self.request.user.restaurant

        if serializer.validated_data.get("is_active", True):
            Menu.objects.filter(
                restaurant=restaurant,
                is_active=True
            ).update(is_active=False)

        serializer.save(restaurant=restaurant)

    def perform_update(self, serializer):
        restaurant = self.request.user.restaurant

        if serializer.instance.restaurant != restaurant:
            raise PermissionDenied("You cannot modify this menu.")

        if serializer.validated_data.get("is_active", False):
            Menu.objects.filter(
                restaurant=restaurant,
                is_active=True
            ).exclude(id=serializer.instance.id).update(is_active=False)

        serializer.save()
        
class PublicMenuViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        restaurant_id = self.kwargs.get("restaurant_id")

        return (
            Menu.objects
            .filter(
                restaurant_id=restaurant_id,
                is_active=True
            )
            .prefetch_related(
                "categories",
                "categories__products",
                "categories__products__modifier_groups",
                "categories__products__modifier_groups__options",
            )
        )
        
class PosMenuViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuSerializer
    permission_classes = [
        IsAuthenticated,
        HasActiveSubscription,
    ]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Menu.objects
            .filter(is_active=True)
            .prefetch_related(
                "categories",
                "categories__products",
            )
        )

        if user.is_superuser:
            return qs

        restaurant = getattr(user, "restaurant", None)

        if restaurant is None:
            return Menu.objects.none()

        return qs.filter(restaurant=restaurant)
    
class ManagerModifierGroupViewSet(viewsets.ModelViewSet):
    serializer_class = ModifierGroupSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        return ModifierGroup.objects.filter(
            products__category__menu__restaurant=self.request.user.restaurant
        ).distinct()

    def perform_create(self, serializer):
        products = serializer.validated_data.get("products", [])

        for product in products:
            if not product.category.menu.restaurant.users.filter(
                id=self.request.user.id
            ).exists():
                raise PermissionDenied("Invalid product.")

        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance

        if not instance.products.filter(
            category__menu__restaurant=self.request.user.restaurant
        ).exists():
            raise PermissionDenied("You cannot modify this modifier group.")

        serializer.save()
        
class ManagerModifierOptionViewSet(viewsets.ModelViewSet):
    serializer_class = ModifierOptionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        return ModifierOption.objects.filter(
            group__products__category__menu__restaurant=self.request.user.restaurant
        ).distinct()

    def perform_create(self, serializer):
        group = serializer.validated_data["group"]

        if not group.products.filter(
            category__menu__restaurant=self.request.user.restaurant
        ).exists():
            raise PermissionDenied("Invalid modifier group.")

        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance

        if not instance.group.products.filter(
            category__menu__restaurant=self.request.user.restaurant
        ).exists():
            raise PermissionDenied("You cannot modify this modifier option.")

        serializer.save()



class PaymentSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        restaurant = getattr(request.user, 'restaurant', None)
        if not restaurant:
            return Response({"error": "Restaurant not found"}, status=404)

        today = timezone.now().date()
        orders = Order.objects.filter(restaurant=restaurant)
        
        # FIXED: Changed 'total_amount' to 'total' based on your model choices
        total_today = orders.filter(created_at__date=today).aggregate(Sum('total'))['total__sum'] or 0
        total_paid = orders.filter(status='paid').aggregate(Sum('total'))['total__sum'] or 0
        pending = orders.filter(status='pending').aggregate(Sum('total'))['total__sum'] or 0

        # Get recent payments
        recent_payments = orders.order_by('-created_at')[:10]
        
        return Response({
            "stats": {
                "total_today": float(total_today),
                "total_paid": float(total_paid),
                "pending": float(pending)
            },
            "payments": [
                {
                    "id": o.id,
                    "order_number": o.order_number or f"ORD-{o.id}",
                    "amount": float(o.total), # FIXED: Changed o.total_amount to o.total
                    "status": o.status,
                    "date": o.created_at.strftime("%Y-%m-%d %H:%M")
                } for o in recent_payments
            ]
        })


# ======================================================================
# POS API ENDPOINTS
# ======================================================================

class PosDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.is_superuser:
            orders = Order.objects.filter(
                status__in=["pending", "preparing"]
            ).order_by("-created_at")
        else:
            restaurant = getattr(user, "restaurant", None)

            if restaurant is None:
                return Response([])

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

    return render(
        request,
        "orders/order_receipt.html",
        {"order": order}
    )
    
@login_required
@require_POST
@transaction.atomic
def complete_order(request, pk):

    if not hasattr(request.user, "restaurant"):
        raise PermissionDenied("No restaurant assigned.")

    order = get_object_or_404(
        Order.objects.select_for_update(),
        pk=pk,
        restaurant=request.user.restaurant
    )

    # ✅ Prevent double checkout
    if order.status == Order.Status.COMPLETED:
        return redirect("core:order-receipt", pk=order.pk)

    # ✅ Mark paid using model method
    order.mark_as_paid(actor=request.user)

    # ✅ Transition (handles inventory + session closing)
    order.transition_to(Order.Status.COMPLETED, actor=request.user)

    # ✅ Broadcast update
    channel_layer = get_channel_layer()
    serialized = OrderSerializer(order).data

    async_to_sync(channel_layer.group_send)(
        f"kitchen_{order.restaurant_id}",
        {
            "type": "order_status_update",
            "data": {
                "type": "order_updated",
                "order": serialized
            }
        }
    )

    return redirect("core:order-receipt", pk=order.pk)

@login_required
@require_POST
@transaction.atomic
def send_to_kitchen(request, pk):
    order = get_object_or_404(
        Order.objects.select_for_update(),
        pk=pk,
        restaurant=request.user.restaurant
    )

    if order.status != Order.Status.DRAFT:
        return redirect("core:pos", order_id=order.pk)

    order.calculate_totals()
    order.refresh_from_db()

    order.transition_to(Order.Status.PLACED, actor=request.user)
    order.refresh_from_db()

    create_kitchen_print_job(order)

    return redirect("core:pos", order_id=order.pk)


@login_required
@require_POST
@transaction.atomic
def complete_ticket(request, ticket_id):

    if not hasattr(request.user, "restaurant"):
        raise PermissionDenied("No restaurant assigned.")

    ticket = get_object_or_404(
        KitchenTicket.objects.select_for_update(),
        pk=ticket_id,
        restaurant=request.user.restaurant
    )

    ticket.mark_completed(actor=request.user)

    return JsonResponse({
        "detail": "Ticket completed successfully."
    })
    

@login_required
@require_POST
@transaction.atomic
def mark_as_paid(request, pk):

    if not hasattr(request.user, "restaurant"):
        raise PermissionDenied("No restaurant assigned.")

    order = get_object_or_404(
        Order.objects.select_for_update(),
        pk=pk,
        restaurant=request.user.restaurant
    )

    # ✅ If already completed, just redirect
    if order.status == Order.Status.COMPLETED:
        return redirect("core:order-receipt", pk=order.pk)

    # ✅ Mark payment via model method
    order.mark_as_paid(actor=request.user)

    # ✅ Complete via state machine (triggers inventory + session closing)
    order.transition_to(Order.Status.COMPLETED, actor=request.user)

    return redirect("core:order-receipt", pk=order.pk)


@require_GET
def order_status_api(request, token, order_id):

    # ✅ Validate QR session
    if not validate_qr_session(request, token):
        return render(request, "customer/session_expired.html")

    table_id = request.session.get("table_id")
    restaurant_id = request.session.get("restaurant_id")

    if not table_id or not restaurant_id:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    order = get_object_or_404(
        Order,
        id=order_id,
        table_id=table_id,
        restaurant_id=restaurant_id
    )

    return JsonResponse({
        "status": order.status
    })
    
    
@require_POST
@transaction.atomic
def call_waiter_api(request, token):

    # ✅ Validate QR session
    if not validate_qr_session(request, token):
        return JsonResponse({"error": "QR session expired."}, status=403)

    table = get_object_or_404(
        Table.objects.select_for_update(),
        access_token=token
    )

    # ✅ Optional anti-spam protection (recommended)
    recent_call_exists = WaiterCall.objects.filter(
        table=table,
        resolved=False
    ).exists()

    if recent_call_exists:
        return JsonResponse({
            "detail": "Waiter already called."
        }, status=200)

    # ✅ Create waiter call
    WaiterCall.objects.create(
        restaurant=table.restaurant,
        table=table
    )

    return JsonResponse({"success": True})


@require_GET
@login_required
def active_waiter_calls_api(request):

    if not hasattr(request.user, "restaurant"):
        raise PermissionDenied("No restaurant assigned.")

    calls = (
        WaiterCall.objects
        .filter(
            restaurant=request.user.restaurant,
            resolved=False
        )
        .select_related("table")
        .order_by("-created_at")
    )

    data = [
        {
            "id": call.id,
            "table_id": call.table.id,
            "table_name": call.table.name,
            "created_at": call.created_at,
        }
        for call in calls
    ]

    return JsonResponse({"calls": data})


    
# ======================================================================
# ======================== PAYMENTS API ================================
# ======================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def generate_qr_payment(request, order_id):

    order = get_object_or_404(
        Order.objects.select_for_update(),
        id=order_id,
        restaurant=request.user.restaurant
    )

    # ✅ Prevent generating payment for completed order
    if order.payment_status == Order.PaymentStatus.PAID:
        return Response(
            {"error": "Order already paid"},
            status=400
        )

    # ✅ If a pending payment already exists, reuse it
    existing_payment = Payment.objects.filter(
        order=order,
        status="PENDING"
    ).first()

    if existing_payment and existing_payment.stripe_payment_intent:
        intent_id = existing_payment.stripe_payment_intent
        intent = stripe.PaymentIntent.retrieve(intent_id)

    else:
        # ✅ Create new Stripe intent
        intent = create_stripe_payment_intent(order)

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "stripe_payment_intent": intent.id,
                "amount": order.total,
                "status": "PENDING",
            }
        )

    qr_url = request.build_absolute_uri(
        reverse(
            "core:pay_order",
            args=[order.restaurant.slug, order.id]
        )
    )

    return Response({
        "qr_url": qr_url,
        "client_secret": intent.client_secret
    })
    
    
def pay_order(request, restaurant_slug, order_id):

    restaurant = get_object_or_404(
        Restaurant,
        slug=restaurant_slug
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant
    )

    # ✅ If already paid, show success
    if order.payment_status == Order.PaymentStatus.PAID:
        return render(
            request,
            "core/payment_success.html",
            {
                "order": order,
                "restaurant": restaurant
            }
        )

    # ✅ GET: Render Stripe payment page
    return render(
        request,
        "core/pay_order.html",
        {
            "order": order,
            "restaurant": restaurant,
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        }
    )
    
from django.shortcuts import get_object_or_404, redirect, render


def payment_success(request, restaurant_slug, order_id):

    restaurant = get_object_or_404(
        Restaurant,
        slug=restaurant_slug
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant
    )

    # ✅ Only allow success page if truly paid
    if order.payment_status != Order.PaymentStatus.PAID:
        return redirect(
            "core:pay_order",
            restaurant_slug=restaurant.slug,
            order_id=order.id
        )

    return render(
        request,
        "core/payment_success.html",
        {
            "order": order,
            "restaurant": restaurant
        }
    )
    

@login_required
@transaction.atomic
def refund_order(request, order_id):

    user = request.user

    if not user.is_cashier and not user.is_manager:
        messages.error(request, "You do not have permission to process refunds.")
        return redirect("core:dashboard")

    order = get_object_or_404(
        Order.objects.select_for_update(),
        id=order_id,
        restaurant=user.restaurant
    )

    # ✅ Must be paid
    if order.payment_status != Order.PaymentStatus.PAID:
        messages.error(request, "Order is not paid.")
        return redirect("core:order_detail", order_id=order.id)

    # ✅ Prevent double refund
    if order.payment_status == Order.PaymentStatus.REFUNDED:
        messages.error(request, "Order already refunded.")
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

    # ✅ Get successful payments only
    payments = order.payments.filter(status=Payment.Status.SUCCEEDED)

    if not payments.exists():
        messages.error(request, "No valid payments found.")
        return redirect("core:order_detail", order_id=order.id)

    total_paid = payments.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    # ✅ Reverse Stripe payments
    for payment in payments:
        stripe.Refund.create(
            payment_intent=payment.stripe_payment_intent
        )

    # ✅ Restore inventory
    order.restore_inventory()

    # ✅ Mark payments as refunded
    payments.update(status=Payment.Status.REFUNDED)

    # ✅ Update order safely
    order.mark_as_refunded(actor=user)

    # ✅ Create refund record
    Refund.objects.create(
        order=order,
        shift=active_shift,
        amount=total_paid,
        processed_by=user,
    )

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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mock_activate_subscription(request):

    restaurant = request.user.restaurant
    plan_id = request.data.get("plan_id")

    try:
        plan = Plan.objects.get(id=plan_id)

        Subscription.objects.update_or_create(
            restaurant=restaurant,
            defaults={
                "plan": plan,
                "status": "trialing",
                "current_period_start": timezone.now(),
                "current_period_end": timezone.now() + timezone.timedelta(days=30),
                "cancel_at_period_end": False,
            },
        )

        return Response({"success": True})

    except Plan.DoesNotExist:
        return Response({"error": "Invalid plan"}, status=400)
    
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def settings_api(request):
    # 1. Check if user is superuser
    if request.user.is_superuser:
        # For superusers, we try to get a restaurant from query params, 
        # otherwise just take the first one in the system for management.
        restaurant_id = request.query_params.get('restaurant_id')
        if restaurant_id:
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()
        else:
            restaurant = Restaurant.objects.first()
    else:
        # Normal flow for restaurant staff
        restaurant = getattr(request.user, "restaurant", None)

    # 2. Validation
    if not restaurant:
        raise PermissionDenied("No restaurant found or associated with this account.")

    # 3. Role Check (Skip for superusers)
    if not request.user.is_superuser and hasattr(request.user, "role"):
        if request.user.role not in ["OWNER", "MANAGER"]:
            raise PermissionDenied("Only owners and managers can edit restaurant settings.")

    # 4. Logic
    settings_obj, _ = Settings.objects.get_or_create(
        restaurant=restaurant,
        defaults={
            "restaurant_display_name": restaurant.name,
        },
    )

    if request.method == "GET":
        serializer = SettingsSerializer(settings_obj)
        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = SettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_api(request):

    user = request.user
    restaurant = getattr(user, "restaurant", None)

    active_shift = None

    if restaurant:
        shift = CashierShift.objects.filter(
            user=user,
            restaurant=restaurant,
            is_active=True
        ).first()

        if shift:
            active_shift = {
                "id": shift.id,
                "started_at": shift.started_at,
            }

    return Response({
        "user": {
            "id": user.id,
            "email": user.email,
            "is_cashier": user.is_cashier,
            "is_manager": user.is_manager,
        },
        "restaurant": {
            "id": restaurant.id,
            "name": restaurant.name,
        } if restaurant else None,
        "active_shift": active_shift,
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_detail(request):

    restaurant = getattr(request.user, "restaurant", None)

    if not restaurant:
        return Response({"detail": "No restaurant assigned."}, status=400)

    subscription = get_object_or_404(
        Subscription,
        restaurant=restaurant
    )

    serializer = SubscriptionSerializer(subscription)

    return Response(serializer.data)

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):

    restaurant = request.user.restaurant
    plan_id = request.data.get("plan_id")

    if not plan_id:
        return Response({"error": "Plan ID is required"}, status=400)

    try:
        plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return Response({"error": "Invalid plan"}, status=400)

    try:
        # ✅ Prevent duplicate active or trial subscriptions
        existing_subscription = Subscription.objects.filter(
            restaurant=restaurant,
            status__in=["trialing", "active"]
        ).first()

        if existing_subscription:
            return Response(
                {"error": "You already have an active subscription."},
                status=400
            )

        # ✅ Create or reuse Stripe customer
        if restaurant.stripe_customer_id:
            customer_id = restaurant.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=restaurant.name,
                metadata={
                    "restaurant_id": str(restaurant.id)
                }
            )
            customer_id = customer["id"]

            # Save Stripe customer on restaurant
            restaurant.stripe_customer_id = customer_id
            restaurant.save(update_fields=["stripe_customer_id"])

        # ✅ Create Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],
            subscription_data={
                "trial_period_days": 30,  # ✅ 1 month free trial
                "metadata": {
                    "restaurant_id": str(restaurant.id),
                    "plan_id": str(plan.id),
                },
            },
            metadata={
                "restaurant_id": str(restaurant.id),
                "plan_id": str(plan.id),
            },
            success_url=settings.FRONTEND_URL + "/billing/success",
            cancel_url=settings.FRONTEND_URL + "/billing/cancel",
        )

        return Response({"url": checkout_session.url})

    except Exception as e:
        return Response({"error": str(e)}, status=400)
    
    
class ManagerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/manager_dashboard.html"
    login_url = "core:login"

    def dispatch(self, request, *args, **kwargs):
        # ✅ Role check (authentication already handled by LoginRequiredMixin)
        if request.user.role != CustomUser.Roles.MANAGER:
            return redirect("core:pos_dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        # ✅ Tenant-safe filtering
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

        # ✅ Resolve restaurant safely
        restaurant = Restaurant.objects.filter(
            users=self.request.user
        ).first()

        if not restaurant:
            return context  # or raise PermissionDenied

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
            status__in=[Table.Status.OCCUPIED, Table.Status.RESERVED]
        ).count()

        # ================= TODAY =================
        today_orders_qs = Order.objects.filter(
            restaurant=restaurant,
            created_at__date=today
        )

        today_orders = today_orders_qs.count()

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

        # ================= TREND CALC =================
        def calculate_trend(current, previous):
            if previous == 0:
                return None, None

            raw = round(((current - previous) / previous) * 100, 1)

            if raw > 0:
                direction = "up"
            elif raw < 0:
                direction = "down"
            else:
                direction = "neutral"

            return abs(raw), direction

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

        # ================= DAILY REVENUE (7 DAYS) =================
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

        daily_map = {i["day"]: float(i["total"] or 0) for i in daily_qs}

        daily_labels = []
        daily_revenue_data = []

        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            daily_labels.append(day.strftime("%b %d"))
            daily_revenue_data.append(daily_map.get(day, 0))

        # ================= HOURLY REVENUE =================
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

        hourly_map = {
            i["hour"].hour: float(i["total"] or 0)
            for i in hourly_qs
        }

        hourly_labels = []
        hourly_revenue_data = []

        for hour in range(24):
            hourly_labels.append(f"{hour:02d}:00")
            hourly_revenue_data.append(hourly_map.get(hour, 0))

        # ================= ACTIVE SESSIONS =================
        active_sessions = TableSession.objects.filter(
            restaurant=restaurant,
            is_active=True
        ).select_related("table", "section")

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

        # ✅ Resolve restaurant safely
        restaurant = Restaurant.objects.filter(
            users=self.request.user
        ).first()

        if not restaurant:
            return context  # or raise PermissionDenied

        # --------------------------------------------------
        # ✅ Subquery for active session (scoped to restaurant)
        # --------------------------------------------------
        active_session_subquery = TableSession.objects.filter(
            table=OuterRef("pk"),
            restaurant=restaurant,
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
        # ✅ Active Orders (dashboard use)
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
    
@require_POST
@login_required
@subscription_required
def create_draft_order_api(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    restaurant = request.user.restaurant

    order_type = data.get("order_type", Order.Type.TAKEAWAY)
    table_id = data.get("table_id")  # optional
    notes = data.get("notes", "")

    # ✅ Optional: attach active shift
    active_shift = Shift.objects.filter(
        restaurant=restaurant,
        ended_at__isnull=True
    ).first()

    with transaction.atomic():

        order = Order.objects.create(
            restaurant=restaurant,
            created_by=request.user,
            status=Order.Status.DRAFT,
            type=order_type,
            table_id=table_id if order_type == Order.Type.DINE_IN else None,
            shift=active_shift,
            notes=notes,
            total=0
        )

    return JsonResponse({
        "order_id": str(order.id),
        "status": order.status,
        "type": order.type,
    })

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
    balance = session_total - paid_total
    return render(
        request,
        "dashboard/session_detail.html",
        {
            "session": session,
            "orders": orders,
            "session_total": session_total,
            "paid_total": paid_total,
            "balance": balance,
        }
    )
    
    
@login_required
def dashboard_session_orders_refresh(request, session_id):
    restaurant = request.user.restaurant

    session = get_object_or_404(
        TableSession,
        id=session_id,
        restaurant=restaurant
    )

    orders = Order.objects.filter(
        session=session
    ).order_by("-created_at")

    html = render_to_string(
        "core/partials/session_orders_list.html",
        {
            "orders": orders,
            "session": session,
        },
        request=request
    )

    return JsonResponse({"html": html})
    
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
    
    
    


def get_request_restaurant(request):
    restaurant = getattr(request.user, "restaurant", None)

    if restaurant:
        return restaurant

    raise PermissionDenied("No restaurant is linked to this account.")


def ensure_can_manage_staff(request):
    if not getattr(request.user, "can_manage_staff", False):
        raise PermissionDenied("You do not have permission to manage staff.")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def staff_list_create_api(request):
    restaurant = get_request_restaurant(request)

    if request.method == "GET":
        staff = User.objects.filter(
            restaurant=restaurant
        ).exclude(
            role=User.Roles.CUSTOMER
        ).order_by("first_name", "last_name", "email")

        serializer = StaffUserSerializer(
            staff,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    if request.method == "POST":
        ensure_can_manage_staff(request)

        serializer = StaffCreateSerializer(
            data=request.data,
            context={"restaurant": restaurant},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_serializer = StaffUserSerializer(
            user,
            context={"request": request},
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def staff_detail_api(request, pk):
    restaurant = get_request_restaurant(request)

    try:
        staff_user = User.objects.get(
            pk=pk,
            restaurant=restaurant,
        )
    except User.DoesNotExist:
        raise NotFound("Staff user not found.")

    if staff_user.role == User.Roles.CUSTOMER:
        raise NotFound("Staff user not found.")

    if request.method == "GET":
        serializer = StaffUserSerializer(
            staff_user,
            context={"request": request},
        )
        return Response(serializer.data)

    ensure_can_manage_staff(request)

    if request.method == "PATCH":
        serializer = StaffUpdateSerializer(
            staff_user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()

        response_serializer = StaffUserSerializer(
            updated_user,
            context={"request": request},
        )
        return Response(response_serializer.data)

    if request.method == "DELETE":
        if staff_user.id == request.user.id:
            raise PermissionDenied("You cannot deactivate your own account.")

        staff_user.is_active = False
        staff_user.save()

        return Response(
            {"detail": "Staff account deactivated."},
            status=status.HTTP_200_OK,
        )

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
        return (
            ModifierOption.objects
            .filter(
                group__products__category__restaurant=self.request.user.restaurant
            )
            .distinct()
        )

    def perform_create(self, serializer):
        group = serializer.validated_data["group"]

        # ✅ Security check BEFORE saving
        if not group.products.filter(
            category__menu__restaurant=self.request.user.restaurant
        ).exists():
            raise PermissionDenied("Invalid restaurant access.")

        serializer.save()
        
        
def public_display(request, token):
    restaurant = get_object_or_404(
        Restaurant,
        display_token=token,
    )

    orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=["READY", "SERVED"]
    ).order_by("-created_at")[:30]   # newest first, limit to 30

    return render(
        request,
        "core/pos/public_display.html",
        {
            "restaurant": restaurant,
            "orders": orders,
            "now": timezone.now(),
        }
    )
    

def legacy_public_display_redirect(request, token):
    """
    Redirect old /display/<token>/ URLs
    to new /pickup/<token>/ URL.
    """
    return redirect("core:public_display", token=token)


def legacy_customer_display_redirect(request, token, table_id):
    """
    Redirect old /display/<token>/<table_id>/ URLs
    to new /table/<token>/<table_id>/ URL.
    """
    return redirect("core:customer_display", token=token, table_id=table_id)

@login_required
def dashboard_public_display(request):
    if not request.user.can_access_public_display:
        return redirect("core:dashboard")

    token = request.user.restaurant.display_token
    return redirect("core:public_display", token=token)

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = ["name", "description", "display_order"]
    template_name = "core/partials/category_form.html"

    def form_valid(self, form):
        # ✅ Resolve restaurant safely
        restaurant = Restaurant.objects.filter(
            users=self.request.user
        ).first()

        if not restaurant:
            return HttpResponseBadRequest("No restaurant found.")

        # ✅ Get menu belonging to this restaurant
        menu = Menu.objects.filter(
            restaurant=restaurant
        ).first()

        if not menu:
            return HttpResponseBadRequest("No menu found.")

        # ✅ Assign menu safely
        form.instance.menu = menu
        form.save()

        # ✅ Refresh categories (tenant-safe)
        categories = (
            Category.objects
            .filter(menu__restaurant=restaurant)
            .annotate(product_count=Count("products"))
            .order_by("display_order", "name")
        )

        response = render(
            self.request,
            "core/partials/category_table.html",
            {"categories": categories}
        )

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
    http_method_names = ["delete"]

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.products.exists():
            html = render_to_string(
                "core/admin/category_error.html",
                {
                    "message": "Cannot delete category with products."
                },
                request=request
            )
            return HttpResponse(html)

        self.object.delete()
        return HttpResponse(status=204)
    
from django.views.generic import DetailView

class CategoryDeleteModalView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = "core/partials/category_delete_modal.html"

    def get_queryset(self):
        return Category.objects.filter(
            menu__restaurant=self.request.user.restaurant
        )

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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    user = request.user
    restaurant = user.restaurant

    if not restaurant:
        return Response(
            {
                "success": False,
                "message": (
                    "Your account is not assigned to a restaurant."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    company = restaurant.company
    subscription = getattr(restaurant, "subscription", None)

    if subscription:
        subscription.expire_if_needed()

    trial_ended = False

    if subscription and subscription.current_period_end:
        trial_ended = (
            subscription.current_period_end
            <= timezone.now()
        )

    profile_incomplete = not restaurant.onboarding_completed

    return Response(
        {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
            "company": {
                "id": company.id,
                "name": company.name,
            },
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.name,
                "address_line_1": restaurant.address_line_1,
                "city": restaurant.city,
                "country": restaurant.country,
                "timezone": restaurant.timezone,
                "currency": restaurant.currency,
                "onboarding_completed": (
                    restaurant.onboarding_completed
                ),
            },
            "onboarding": {
                "completed": (
                    restaurant.onboarding_completed
                ),
                "profile_incomplete": profile_incomplete,
                "trial_ended": trial_ended,
                "show_completion_prompt": (
                    profile_incomplete and not trial_ended
                ),
            },
            "subscription": (
                {
                    "id": subscription.id,
                    "status": subscription.status,
                    "plan_name": (
                        subscription.plan.name
                        if subscription.plan
                        else None
                    ),
                    "current_period_end": (
                        subscription.current_period_end
                    ),
                    "days_remaining": subscription.days_remaining,
                    "is_active": subscription.is_active(),
                }
                if subscription
                else None
            ),
        },
        status=status.HTTP_200_OK,
    )


def subscription_expired(request):
    return render(
        request,
        "core/subscription_expired.html",
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def register_restaurant_api(request):
    form = RestaurantRegistrationForm(data=request.data)

    if not form.is_valid():
        return Response(
            {
                "success": False,
                "message": "Please correct the errors below.",
                "errors": form.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = form.cleaned_data["email"].strip().lower()
    password = form.cleaned_data["password"]
    restaurant_name = (
        form.cleaned_data["restaurant_name"].strip()
    )

    if CustomUser.objects.filter(email__iexact=email).exists():
        return Response(
            {
                "success": False,
                "message": "A user with this email already exists.",
                "errors": {
                    "email": [
                        "A user with this email already exists."
                    ]
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    starter_plan = Plan.objects.filter(
        code="starter",
        is_active=True,
    ).first()

    company = Company.objects.create(
        name=restaurant_name,
    )

    restaurant = Restaurant.objects.create(
        company=company,
        name=restaurant_name,
        address_line_1="",
        city="",
        country="",
        timezone="UTC",
        currency="USD",
        onboarding_completed=False,
    )

    user = CustomUser(
        username=email,
        email=email,
        role=CustomUser.Roles.MANAGER,
        restaurant=restaurant,
    )
    user.set_password(password)
    user.save()

    subscription = Subscription.objects.create(
        restaurant=restaurant,
        plan=starter_plan,
        status=Subscription.SubscriptionStatus.TRIALING,
    )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "success": True,
            "message": (
                f"Welcome to {restaurant.name}. "
                "Your account was created successfully."
            ),
            "onboarding": {
                "completed": restaurant.onboarding_completed,
                "required": True,
                "message": (
                    "Please complete your restaurant profile "
                    "before the trial ends."
                ),
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "company": {
                "id": company.id,
                "name": company.name,
            },
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.name,
                "company_id": company.id,
                "onboarding_completed": (
                    restaurant.onboarding_completed
                ),
            },
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "restaurant_id": restaurant.id,
            },
            "subscription": {
                "id": subscription.id,
                "status": subscription.status,
                "plan_id": subscription.plan_id,
                "plan_name": (
                    subscription.plan.name
                    if subscription.plan
                    else None
                ),
                "trial_start": subscription.trial_start,
                "trial_end": subscription.trial_end,
                "current_period_start": (
                    subscription.current_period_start
                ),
                "current_period_end": (
                    subscription.current_period_end
                ),
                "days_remaining": subscription.days_remaining,
                "is_active": subscription.is_active(),
            },
        },
        status=status.HTTP_201_CREATED,
    )
    
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_summary(request):
    from .models import Order, OrderItem, Table

    restaurants = get_accessible_restaurants(request.user)

    today = timezone.localdate()

    default_start = today - timedelta(days=6)
    start_date = parse_date(request.GET.get("start_date", "")) or default_start
    end_date = parse_date(request.GET.get("end_date", "")) or today

    month_start = today.replace(day=1)

    selected_orders = Order.objects.filter(
        restaurant__in=restaurants,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )

    selected_completed_orders = selected_orders.filter(status__iexact="completed")

    monthly_orders_queryset = Order.objects.filter(
        restaurant__in=restaurants,
        created_at__date__gte=month_start,
        created_at__date__lte=today,
    )

    monthly_completed_orders = monthly_orders_queryset.filter(status__iexact="completed")

    weekly_sales = selected_completed_orders.aggregate(
        total=Sum("total")
    )["total"] or 0

    weekly_orders = selected_orders.count()

    monthly_sales = monthly_completed_orders.aggregate(
        total=Sum("total")
    )["total"] or 0

    monthly_orders = monthly_orders_queryset.count()

    average_order_value = selected_completed_orders.aggregate(
        avg=Avg("total")
    )["avg"] or 0

    active_tables = Table.objects.filter(
        restaurant__in=restaurants,
        status__in=["occupied", "reserved"],
    ).count()

    sales_by_day_queryset = (
        selected_completed_orders
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(sales=Sum("total"))
        .order_by("day")
    )

    sales_by_day = [
        {
            "date": item["day"].strftime("%a"),
            "sales": float(item["sales"] or 0),
        }
        for item in sales_by_day_queryset
    ]

    orders_by_status_queryset = (
        selected_orders
        .values("status")
        .annotate(value=Count("id"))
        .order_by("status")
    )

    orders_by_status = [
        {
            "name": item["status"].capitalize() if item["status"] else "Unknown",
            "value": item["value"],
        }
        for item in orders_by_status_queryset
    ]

    top_items_queryset = (
        OrderItem.objects
        .filter(order__in=selected_completed_orders)
        .values("product__name")
        .annotate(
            quantity=Sum("quantity"),
            revenue=Sum("final_price"),
        )
        .order_by("-quantity")[:10]
    )

    top_items = [
        {
            "name": item["product__name"] or "Unknown Item",
            "quantity": item["quantity"] or 0,
            "revenue": float(item["revenue"] or 0),
        }
        for item in top_items_queryset
    ]
    
    recent_orders_queryset = (
        selected_orders
        .select_related("table")
        .order_by("-created_at")[:10]
    )

    recent_orders = [
        {
            "id": order.id,
            "table": str(order.table) if order.table else "Takeaway",
            "status": order.status,
            "total": float(order.total or 0),
            "created_at": timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M"),
        }
        for order in recent_orders_queryset
    ]

    return Response({
        "summary": {
            "weekly_sales": float(weekly_sales),
            "monthly_sales": float(monthly_sales),
            "weekly_orders": weekly_orders,
            "monthly_orders": monthly_orders,
            "average_order_value": float(average_order_value),
            "active_tables": active_tables,
        },
        "sales_by_day": sales_by_day,
        "orders_by_status": orders_by_status,
        "top_items": top_items,
        "staff_performance": [],
        "recent_orders": recent_orders,
    })

class PrinterViewSet(viewsets.ModelViewSet):
    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Printer.objects.all()

        printer_type = self.request.query_params.get("printer_type")
        is_active = self.request.query_params.get("is_active")

        if printer_type:
            queryset = queryset.filter(printer_type=printer_type.upper())

        if is_active is not None:
            if is_active.lower() in ["true", "1", "yes"]:
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ["false", "0", "no"]:
                queryset = queryset.filter(is_active=False)

        return queryset


class PrintJobViewSet(viewsets.ModelViewSet):
    queryset = PrintJob.objects.select_related("order", "printer").all()
    serializer_class = PrintJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = PrintJob.objects.select_related("order", "printer").all()

        status_value = self.request.query_params.get("status")
        job_type = self.request.query_params.get("job_type")
        order_id = self.request.query_params.get("order")

        if status_value:
            queryset = queryset.filter(status=status_value.upper())

        if job_type:
            queryset = queryset.filter(job_type=job_type.upper())

        if order_id:
            queryset = queryset.filter(order_id=order_id)

        return queryset

    def perform_create(self, serializer):
        job_type = serializer.validated_data.get("job_type")
        printer = serializer.validated_data.get("printer")

        if printer is None:
            printer = get_default_printer(job_type)

        serializer.save(printer=printer)
        
        
# ===================================================================
# CUSTOMER VIEWSET
# ===================================================================
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Now 'restaurant' is a valid keyword!
        restaurant = getattr(self.request.user, 'restaurant', None)

        if not restaurant:
            return Customer.objects.none()
        return Customer.objects.filter(restaurant=restaurant)

    def perform_create(self, serializer):
        # Automatically assign the customer to the manager's restaurant
        restaurant = getattr(self.request.user, 'restaurant', None)

        serializer.save(restaurant=restaurant)

# ===================================================================
# INVENTORY VIEWSET
# ===================================================================

def get_user_restaurant(user):
    return user.restaurant

class InventoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for inventory items. Includes a custom action to get
    only low-stock items.
    """

    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        restaurant = getattr(self.request.user, 'restaurant', None)

        if not restaurant:
            return InventoryItem.objects.none()
        queryset = InventoryItem.objects.filter(restaurant=restaurant)

        # Filter low stock items
        low_stock = self.request.query_params.get("low_stock")
        if low_stock == "true":
            from django.db.models import F
            queryset = queryset.filter(quantity__lte=F("low_stock_threshold"))

        return queryset

    def perform_create(self, serializer):
        restaurant = getattr(self.request.user, 'restaurant', None)

        serializer.save(restaurant=restaurant)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Return only items at or below their low stock threshold."""
        restaurant = get_user_restaurant(request.user)
        if not restaurant:
            return Response([])
        from django.db.models import F
        items = InventoryItem.objects.filter(
            restaurant=restaurant,
            quantity__lte=F("low_stock_threshold"),
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


# ===================================================================
# DISCOUNT VIEWSET
# ===================================================================
class DiscountViewSet(viewsets.ModelViewSet):
    """
    CRUD for discounts and promo codes.
    Includes toggle action to activate/deactivate quickly.
    """

    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        restaurant = getattr(self.request.user, 'restaurant', None)

        if not restaurant:
            return Discount.objects.none()
        queryset = Discount.objects.filter(restaurant=restaurant)

        # Filter active only
        active = self.request.query_params.get("active")
        if active == "true":
            queryset = queryset.filter(is_active=True)
        elif active == "false":
            queryset = queryset.filter(is_active=False)

        return queryset

    def perform_create(self, serializer):
        restaurant = getattr(self.request.user, 'restaurant', None)

        serializer.save(restaurant=restaurant)

    @action(detail=True, methods=["patch"])
    def toggle(self, request):
        """Toggle is_active status."""
        discount = self.get_object()
        discount.is_active = not discount.is_active
        discount.save()
        serializer = self.get_serializer(discount)
        return Response(serializer.data)



class WebhookConfigAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Ensure restaurant exists for the user
        restaurant = getattr(request.user, 'restaurant', None)
        if not restaurant:
            return Response({"error": "No restaurant found"}, status=403)
        
        config, _ = WebhookConfiguration.objects.get_or_create(restaurant=restaurant)
        serializer = WebhookConfigurationSerializer(config)
        return Response(serializer.data)

    def post(self, request):
        restaurant = request.user.restaurant
        config, _ = WebhookConfiguration.objects.get_or_create(restaurant=restaurant)
        
        # Update URLs and Toggle Status
        config.live_webhook_url = request.data.get('live_webhook_url', config.live_webhook_url)
        config.test_webhook_url = request.data.get('test_webhook_url', config.test_webhook_url)
        config.is_live_enabled = request.data.get('is_live_enabled', config.is_live_enabled)
        config.is_test_enabled = request.data.get('is_test_enabled', config.is_test_enabled)
        
        config.save()
        return Response({"message": "Configuration updated successfully"})



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_api_key(request):
    """
    Endpoint: /api/v1/developer/regenerate-key/
    Payload: {"type": "live_api_key"} or {"type": "test_api_key"}
    """
    key_type = request.data.get("type")
    if key_type not in ["live_api_key", "test_api_key", "live_secret", "test_secret"]:
        return Response({"error": "Invalid key type"}, status=400)

    config = WebhookConfiguration.objects.get(restaurant=request.user.restaurant)
    
    # Generate new value
    if "secret" in key_type:
        new_value = secrets.token_hex(24)
    else:
        prefix = "beepos_live_" if "live" in key_type else "beepos_test_"
        new_value = f"{prefix}{secrets.token_urlsafe(32)}"

    setattr(config, key_type, new_value)
    config.save()

    return Response({
        "message": f"{key_type.replace('_', ' ').title()} regenerated",
        "new_value": new_value
    })