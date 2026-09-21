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
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from decimal import Decimal
from django.conf import settings
import random
from .print_utils import build_kitchen_ticket_text, build_receipt_text
from openpyxl import Workbook
# DRF
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .permissions import IsOwnerOrManager
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_200_OK

from rest_framework.decorators import api_view, permission_classes, action, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework_simplejwt.authentication import JWTAuthentication
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

from .models import (
    Category,
    Company,
    CustomUser,
    Customer,
    Discount,
    InventoryItem,
    KitchenTicket,
    Menu,
    ModifierGroup,
    ModifierOption,
    Order,
    OrderItem,
    Payment,
    PaymentMethod,
    Plan,
    Product,
    Session as RegisterSession,
    ProductIngredient,
    ProductVariant,
    Restaurant,
    Settings,
    Subscription,
    Table,
    TableSession,
    WebhookConfiguration,
)

from .serializers import (
    CategorySerializer,
    ChangePasswordSerializer,
    CustomUserSerializer,
    CustomerSerializer,
    DiscountSerializer,
    InventoryItemSerializer,
    MenuSerializer,
    ModifierGroupSerializer,
    ModifierOptionSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PaymentMethodSerializer,
    PaymentSerializer,
    ProductSerializer,
    PublicCategorySerializer,
    PublicOrderCreateSerializer,
    PublicTableSerializer,
    SessionSerializer,
    SettingsSerializer,
    StaffCreateSerializer,
    StaffUpdateSerializer,
    SubscriptionSerializer,
    TableSerializer,
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
from django.db.models import Q

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




class PublicTableMenuAPIView(APIView):
    permission_classes = []

    def get_table(self, token):
        return get_object_or_404(
            Table.objects.select_related(
                "restaurant",
            ),
            access_token=token,
        )

    def get(self, request, token):
        table = self.get_table(token)

        if table.current_status in [
            Table.Status.NEEDS_CLEANING,
            Table.Status.MERGED,
        ]:
            return Response(
                {
                    "detail": (
                        "This table is currently unavailable."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        menu = (
            Menu.objects
            .filter(
                restaurant_id=table.restaurant_id,
                is_active=True,
            )
            .prefetch_related(
                "categories__products",
            )
            .first()
        )

        categories = (
            menu.categories.all()
            if menu
            else Category.objects.none()
        )

        return Response(
            {
                "table": PublicTableSerializer(
                    table
                ).data,
                "categories": PublicCategorySerializer(
                    categories,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )
        
class PublicTableOrderAPIView(APIView):
    permission_classes = []

    MAX_ITEMS = 50
    MAX_QUANTITY_PER_ITEM = 50

    def get_table(self, token):
        return get_object_or_404(
            Table.objects.select_related(
                "restaurant",
            ),
            access_token=token,
        )

    @transaction.atomic
    def post(self, request, token):
        table = self.get_table(token)

        if table.current_status in [
            Table.Status.NEEDS_CLEANING,
            Table.Status.MERGED,
        ]:
            return Response(
                {
                    "detail": (
                        "This table is currently unavailable."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = PublicOrderCreateSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        validated_data = serializer.validated_data
        items_data = validated_data["items"]

        if len(items_data) > self.MAX_ITEMS:
            return Response(
                {
                    "detail": (
                        "Too many different items "
                        "in one order."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        products_by_id = {}

        for item_data in items_data:
            product = item_data["product"]

            if product.id in products_by_id:
                return Response(
                    {
                        "detail": (
                            "Duplicate products must be "
                            "combined into one item."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products_by_id[product.id] = product

        product_ids = list(
            products_by_id.keys()
        )

        valid_products = (
            Product.objects
            .filter(
                id__in=product_ids,
                is_available=True,
                category__menu__restaurant_id=(
                    table.restaurant_id
                ),
            )
            .select_related(
                "category",
                "category__menu",
            )
        )

        valid_products_by_id = {
            product.id: product
            for product in valid_products
        }

        if len(valid_products_by_id) != len(
            product_ids
        ):
            return Response(
                {
                    "detail": (
                        "One or more selected products "
                        "are unavailable."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_type = validated_data.get(
            "order_type",
            Order.OrderType.DINE_IN,
        )

        order = Order.objects.create(
            restaurant=table.restaurant,
            table=table,
            order_type=order_type,
            status=Order.Status.PLACED,
            payment_status=Order.PaymentStatus.UNPAID,
            notes=validated_data.get(
                "notes",
                "",
            ),
        )

        for item_data in items_data:
            product = valid_products_by_id[
                item_data["product"].id
            ]

            quantity = item_data["quantity"]

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                final_price=product.base_price,
                notes="",
            )

        if hasattr(order, "calculate_totals"):
            order.calculate_totals()
            order.refresh_from_db()

        table.status = Table.Status.OCCUPIED
        table.is_occupied = True

        table.save(
            update_fields=[
                "status",
                "is_occupied",
            ]
        )

        return Response(
            {
                "order": {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "status": order.status,
                    "payment_status": (
                        order.payment_status
                    ),
                    "total": str(order.total),
                },
                "table": PublicTableSerializer(
                    table
                ).data,
            },
            status=status.HTTP_201_CREATED,
        ) 

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
                    product_id = (
                    item_data.get("product_id")
                    or item_data.get("product")
                    )

                    if not product_id:
                        raise ValidationError(
                    {
                        "product": (
                        "Product is required."
                        )
                    }
                )

                    try:
                        quantity = int(
                        item_data.get(
                        "quantity",
                        1,
                        )
                        )
                    except (
                    TypeError,
                    ValueError,
                    ):
                        raise ValidationError(
                        {
                            "quantity": (
                            "Quantity must be an integer."
                            )
                        }
                    )

                    if quantity < 1 or quantity > 50:
                        raise ValidationError(
                        {
                        "quantity": (
                        "Quantity must be between "
                        "1 and 50."
                        )
                        }
                    )

                    modifier_ids = (
                    item_data.get(
                    "modifier_option_ids"
                    )
                    or item_data.get(
                    "modifiers"
                    )
                    or []
                    )

                    product = get_object_or_404(
                    Product,
                    pk=product_id,
                    is_available=True,
                    category__menu__restaurant_id=(
                    order.restaurant_id
                    ),
                    )

                    order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    final_price=product.base_price,
                    status="QUEUED",
                    notes=item_data.get(
                    "notes",
                    "",
                    ),
                    )

                    if modifier_ids:
                        order_item.modifiers.set(
                        modifier_ids
                    )

                # 5. Finalize Order Totals
                order.calculate_totals()
                order.refresh_from_db()

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
class TableViewSet(viewsets.ModelViewSet):
    serializer_class = TableSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def _get_restaurant(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return None

        restaurant = getattr(
            user,
            "restaurant",
            None,
        )

        if restaurant is None:
            profile = getattr(
                user,
                "userprofile",
                None,
            )

            if profile is not None:
                restaurant = getattr(
                    profile,
                    "restaurant",
                    None,
                )

        return restaurant

    def get_queryset(self):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Table.objects.none()

        return (
            Table.objects
            .filter(
                restaurant_id=restaurant.id,
            )
            .order_by(
                "table_number",
                "id",
            )
        )

    def _get_table_status(self, table):
        return str(
            getattr(
                table,
                "status",
                "AVAILABLE",
            )
        ).upper()

    def _set_table_occupied(self, table):
        if table is None:
            return

        changed_fields = []

        if hasattr(table, "status"):
            occupied_value = getattr(
                Table.Status,
                "OCCUPIED",
                "OCCUPIED",
            )

            if table.status != occupied_value:
                table.status = occupied_value
                changed_fields.append(
                    "status"
                )

        if hasattr(table, "is_occupied"):
            if table.is_occupied is not True:
                table.is_occupied = True
                changed_fields.append(
                    "is_occupied"
                )

        if changed_fields:
            table.save(
                update_fields=changed_fields,
            )

    def _set_table_vacant(self, table):
        if table is None:
            return

        changed_fields = []

        if hasattr(table, "status"):
            available_value = getattr(
                Table.Status,
                "AVAILABLE",
                "AVAILABLE",
            )

            if table.status != available_value:
                table.status = available_value
                changed_fields.append(
                    "status"
                )

        if hasattr(table, "is_occupied"):
            if table.is_occupied is not False:
                table.is_occupied = False
                changed_fields.append(
                    "is_occupied"
                )

        if changed_fields:
            table.save(
                update_fields=changed_fields,
            )

    def _close_table_session(
        self,
        table_session,
    ):
        if table_session is None:
            return

        changed_fields = []

        if hasattr(
            table_session,
            "is_active",
        ):
            if table_session.is_active is not False:
                table_session.is_active = False
                changed_fields.append(
                    "is_active"
                )

        if hasattr(
            table_session,
            "closed_at",
        ):
            if table_session.closed_at is None:
                table_session.closed_at = timezone.now()
                changed_fields.append(
                    "closed_at"
                )

        if changed_fields:
            table_session.save(
                update_fields=changed_fields,
            )

    def _release_table_sessions(self, table):
        if table is None:
            return

        sessions = (
            TableSession.objects
            .select_for_update()
            .filter(
                table_id=table.id,
                restaurant_id=table.restaurant_id,
                is_active=True,
            )
        )

        for table_session in sessions:
            self._close_table_session(
                table_session
            )

    def _has_active_table_session(self, table):
        if table is None:
            return False

        return (
            TableSession.objects
            .filter(
                table_id=table.id,
                restaurant_id=table.restaurant_id,
                is_active=True,
            )
            .exists()
        )

    def _normalize_table_number(
        self,
        value,
    ):
        return str(
            value or ""
        ).strip()

    def _table_number_exists(
        self,
        restaurant,
        table_number,
        exclude_pk=None,
    ):
        queryset = Table.objects.filter(
            restaurant_id=restaurant.id,
            table_number__iexact=table_number,
        )

        if exclude_pk is not None:
            queryset = queryset.exclude(
                pk=exclude_pk,
            )

        return queryset.exists()

    def perform_create(self, serializer):
        restaurant = self._get_restaurant()

        if restaurant is None:
            raise PermissionDenied(
                "User is not assigned to a restaurant."
            )

        requested_table_number = (
            self._normalize_table_number(
                serializer.validated_data.get(
                    "table_number",
                    "",
                )
            )
        )

        if not requested_table_number:
            raise ValidationError(
                {
                    "table_number": (
                        "Table number is required."
                    )
                }
            )

        if self._table_number_exists(
            restaurant=restaurant,
            table_number=requested_table_number,
        ):
            raise ValidationError(
                {
                    "table_number": (
                        "This table already exists "
                        "in your restaurant."
                    )
                }
            )

        save_kwargs = {
            "restaurant": restaurant,
            "table_number": requested_table_number,
        }

        if hasattr(
            Table,
            "Status",
        ):
            save_kwargs["status"] = (
                Table.Status.AVAILABLE
            )

        if hasattr(
            Table,
            "is_occupied",
        ):
            save_kwargs["is_occupied"] = False

        serializer.save(
            **save_kwargs
        )

    def perform_update(self, serializer):
        restaurant = self._get_restaurant()

        if restaurant is None:
            raise PermissionDenied(
                "User is not assigned to a restaurant."
            )

        table = self.get_object()

        validated_data = (
            serializer.validated_data
        )

        new_table_number = (
            self._normalize_table_number(
                validated_data.get(
                    "table_number",
                    table.table_number,
                )
            )
        )

        if not new_table_number:
            raise ValidationError(
                {
                    "table_number": (
                        "Table number is required."
                    )
                }
            )

        if self._table_number_exists(
            restaurant=restaurant,
            table_number=new_table_number,
            exclude_pk=table.pk,
        ):
            raise ValidationError(
                {
                    "table_number": (
                        "This table already exists "
                        "in your restaurant."
                    )
                }
            )

        serializer.validated_data.pop(
            "restaurant",
            None,
        )

        serializer.validated_data.pop(
            "status",
            None,
        )

        serializer.validated_data.pop(
            "is_occupied",
            None,
        )

        serializer.save(
            table_number=new_table_number,
        )

    def perform_destroy(self, instance):
        restaurant = self._get_restaurant()

        if restaurant is None:
            raise PermissionDenied(
                "User is not assigned to a restaurant."
            )

        table = (
            Table.objects
            .select_for_update()
            .filter(
                pk=instance.pk,
                restaurant_id=restaurant.id,
            )
            .first()
        )

        if table is None:
            raise ValidationError(
                {
                    "detail": (
                        "Table does not belong "
                        "to your restaurant."
                    )
                }
            )

        table_status = (
            self._get_table_status(table)
        )

        is_occupied = (
            getattr(
                table,
                "is_occupied",
                False,
            )
            or table_status
            in {
                "OCCUPIED",
                "IN_USE",
            }
        )

        if is_occupied:
            raise ValidationError(
                {
                    "detail": (
                        "Occupied tables cannot "
                        "be deleted."
                    )
                }
            )

        if self._has_active_table_session(
            table
        ):
            raise ValidationError(
                {
                    "detail": (
                        "Tables with active "
                        "sessions cannot be deleted."
                    )
                }
            )

        table.delete()

    @action(
        detail=True,
        methods=["post"],
        url_path="generate_qr",
        url_name="generate-qr",
    )
    @transaction.atomic
    def generate_qr(
        self,
        request,
        pk=None,
    ):
        table = self.get_object()

        if not hasattr(
            table,
            "generate_qr_code",
        ):
            return Response(
                {
                    "detail": (
                        "QR code generation is "
                        "not available on the "
                        "Table model."
                    )
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        table.generate_qr_code()
        table.refresh_from_db()

        return Response(
            self.get_serializer(
                table
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="release",
        url_name="release",
    )
    @transaction.atomic
    def release(
        self,
        request,
        pk=None,
    ):
        table = (
            Table.objects
            .select_for_update()
            .filter(
                pk=pk,
                restaurant_id=(
                    self._get_restaurant().id
                    if self._get_restaurant()
                    else None
                ),
            )
            .first()
        )

        if table is None:
            return Response(
                {
                    "detail": "Table not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if self._has_active_table_session(
            table
        ):
            return Response(
                {
                    "detail": (
                        "The table still has an "
                        "active table session."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        self._set_table_vacant(table)

        return Response(
            self.get_serializer(
                table
            ).data,
            status=status.HTTP_200_OK,
        )
        
        
        
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def _get_restaurant(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return None

        restaurant = getattr(
            user,
            "restaurant",
            None,
        )

        if restaurant is None:
            profile = getattr(
                user,
                "userprofile",
                None,
            )

            if profile is not None:
                restaurant = getattr(
                    profile,
                    "restaurant",
                    None,
                )

        return restaurant

    def get_queryset(self):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Order.objects.none()

        return (
            Order.objects
            .filter(
                restaurant_id=restaurant.id,
            )
            .select_related(
                "restaurant",
                "customer",
                "table",
                "section",
                "session",
                "payment_method",
                "created_by",
            )
            .prefetch_related(
                "items",
                "items__product",
                "items__variant",
                "items__modifiers",
                "payments",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

    def _get_register_session(self, restaurant):
        """
        The register model is core.Session.
        Order.session remains TableSession.
        """

        return (
            RegisterSession.objects
            .filter(
                restaurant_id=restaurant.id,
                status="OPEN",
            )
            .order_by(
                "-start_time",
                "-id",
            )
            .first()
        )

    def _get_active_table_session(
        self,
        table,
        restaurant,
    ):
        table_session = (
            TableSession.objects
            .select_for_update()
            .filter(
                table_id=table.id,
                restaurant_id=restaurant.id,
                is_active=True,
            )
            .order_by("-id")
            .first()
        )

        if table_session is not None:
            return table_session

        return TableSession.objects.create(
            table=table,
            restaurant=restaurant,
            is_active=True,
        )

    def _get_takeout_table(self, restaurant):
        table = (
            Table.objects
            .select_for_update()
            .filter(
                restaurant_id=restaurant.id,
                table_number="TO",
            )
            .first()
        )

        if table is not None:
            return table

        return Table.objects.create(
            restaurant=restaurant,
            table_number="TO",
            capacity=0,
            status=Table.Status.AVAILABLE,
            is_occupied=False,
        )

    def _set_table_occupied(self, table):
        if table is None:
            return

        changed_fields = []

        if hasattr(table, "status"):
            occupied_value = getattr(
                Table.Status,
                "OCCUPIED",
                "OCCUPIED",
            )

            if table.status != occupied_value:
                table.status = occupied_value
                changed_fields.append(
                    "status"
                )

        if hasattr(table, "is_occupied"):
            if table.is_occupied is not True:
                table.is_occupied = True
                changed_fields.append(
                    "is_occupied"
                )

        if changed_fields:
            table.save(
                update_fields=changed_fields,
            )

    def _set_table_vacant(self, table):
        if table is None:
            return

        changed_fields = []

        if hasattr(table, "status"):
            available_value = getattr(
                Table.Status,
                "AVAILABLE",
                "AVAILABLE",
            )

            if table.status != available_value:
                table.status = available_value
                changed_fields.append(
                    "status"
                )

        if hasattr(table, "is_occupied"):
            if table.is_occupied is not False:
                table.is_occupied = False
                changed_fields.append(
                    "is_occupied"
                )

        if changed_fields:
            table.save(
                update_fields=changed_fields,
            )

    def _close_table_session(
        self,
        table_session,
    ):
        if table_session is None:
            return

        changed_fields = []

        if hasattr(
            table_session,
            "is_active",
        ):
            if table_session.is_active is not False:
                table_session.is_active = False
                changed_fields.append(
                    "is_active"
                )

        if hasattr(
            table_session,
            "closed_at",
        ):
            if table_session.closed_at is None:
                table_session.closed_at = timezone.now()
                changed_fields.append(
                    "closed_at"
                )

        if changed_fields:
            table_session.save(
                update_fields=changed_fields,
            )

    def _has_other_open_orders(self, order):
        if order is None:
            return False

        if order.table_id is None:
            return False

        open_statuses = [
            Order.Status.DRAFT,
            Order.Status.PLACED,
            Order.Status.IN_PROGRESS,
            Order.Status.READY,
            Order.Status.SERVED,
        ]

        unpaid_statuses = [
            Order.PaymentStatus.UNPAID,
            Order.PaymentStatus.PARTIALLY_PAID,
        ]

        return (
            Order.objects
            .filter(
                table_id=order.table_id,
                restaurant_id=order.restaurant_id,
                status__in=open_statuses,
                payment_status__in=unpaid_statuses,
            )
            .exclude(
                pk=order.pk,
            )
            .exists()
        )

    def _release_order_table(self, order):
        """
        Release the physical table only when no
        other unpaid open orders remain.
        """

        if order is None:
            return

        if order.table_id is None:
            return

        if self._has_other_open_orders(order):
            return

        table = (
            Table.objects
            .select_for_update()
            .filter(
                pk=order.table_id,
                restaurant_id=order.restaurant_id,
            )
            .first()
        )

        if table is not None:
            self._set_table_vacant(table)

        if order.session_id is None:
            return

        table_session = (
            TableSession.objects
            .select_for_update()
            .filter(
                pk=order.session_id,
                table_id=order.table_id,
                restaurant_id=order.restaurant_id,
                is_active=True,
            )
            .first()
        )

        if table_session is not None:
            self._close_table_session(
                table_session
            )

    def _order_type_is_takeout(
        self,
        order_type,
    ):
        normalized = str(
            order_type or ""
        ).strip().upper()

        return normalized in {
            "TAKEOUT",
            "TAKE_OUT",
            "TAKE-AWAY",
            "TAKE_AWAY",
        }

    def _get_order_type(self, serializer):
        return serializer.validated_data.get(
            "order_type",
            Order.OrderType.DINE_IN,
        )

    def _get_table_for_create(
        self,
        request,
        restaurant,
        order_type,
    ):
        if self._order_type_is_takeout(
            order_type
        ):
            return self._get_takeout_table(
                restaurant
            )

        table_id = (
            request.data.get("table")
            or request.data.get("table_id")
        )

        if not table_id:
            raise ValidationError(
                {
                    "table": (
                        "Table ID is required "
                        "for dine-in orders."
                    )
                }
            )

        table = get_object_or_404(
            Table.objects.select_for_update(),
            pk=table_id,
            restaurant_id=restaurant.id,
        )

        table_status = str(
            getattr(
                table,
                "status",
                "AVAILABLE",
            )
        ).strip().upper()

        if table_status == "VACANT":
            table_status = "AVAILABLE"

        if table_status == "IN_USE":
            table_status = "OCCUPIED"

        blocked_statuses = {
            "NEEDS_CLEANING",
            "MERGED",
            "INACTIVE",
        }

        if table_status in blocked_statuses:
            raise ValidationError(
                {
                    "table": (
                        "This table cannot accept "
                        "new orders."
                    )
                }
            )

        return table

    def _clean_order_data(
        self,
        serializer,
    ):
        validated_data = dict(
            serializer.validated_data
        )

        view_managed_fields = [
            "restaurant",
            "created_by",
            "session",
            "table",
            "status",
            "payment_status",
            "payment_method",
            "total",
        ]

        for field_name in view_managed_fields:
            validated_data.pop(
                field_name,
                None,
            )

        return validated_data

    @transaction.atomic
    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "User is not associated "
                        "with a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        order_type = self._get_order_type(
            serializer
        )

        table = self._get_table_for_create(
            request=request,
            restaurant=restaurant,
            order_type=order_type,
        )

        register_session = (
            self._get_register_session(
                restaurant
            )
        )

        if register_session is None:
            return Response(
                {
                    "detail": (
                        "Open the register before "
                        "creating an order."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        table_session = (
            self._get_active_table_session(
                table=table,
                restaurant=restaurant,
            )
        )

        validated_data = (
            self._clean_order_data(
                serializer
            )
        )

        order = Order.objects.create(
            restaurant=restaurant,
            created_by=request.user,
            session=table_session,
            table=table,
            order_type=order_type,
            status=Order.Status.DRAFT,
            payment_status=(
                Order.PaymentStatus.UNPAID
            ),
            **validated_data,
        )

        if hasattr(
            order,
            "calculate_totals",
        ):
            order.calculate_totals()
            order.refresh_from_db()

        if not self._order_type_is_takeout(
            order_type
        ):
            self._set_table_occupied(
                table
            )

        output_serializer = self.get_serializer(
            order
        )

        headers = self.get_success_headers(
            output_serializer.data
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="create_takeout",
        url_name="create-takeout",
    )
    @transaction.atomic
    def create_takeout(self, request):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "User is not associated "
                        "with a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        register_session = (
            self._get_register_session(
                restaurant
            )
        )

        if register_session is None:
            return Response(
                {
                    "detail": (
                        "Open the register before "
                        "creating an order."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        items = request.data.get(
            "items",
            [],
        )

        if not isinstance(items, list):
            return Response(
                {
                    "items": (
                        "Items must be a list."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not items:
            return Response(
                {
                    "items": (
                        "At least one item is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        takeout_table = (
            self._get_takeout_table(
                restaurant
            )
        )

        table_session = (
            self._get_active_table_session(
                table=takeout_table,
                restaurant=restaurant,
            )
        )

        notes = str(
            request.data.get(
                "notes",
                "",
            )
        ).strip()

        order = Order.objects.create(
            restaurant=restaurant,
            created_by=request.user,
            session=table_session,
            table=takeout_table,
            order_type=Order.OrderType.TAKEOUT,
            status=Order.Status.DRAFT,
            payment_status=(
                Order.PaymentStatus.UNPAID
            ),
            notes=notes,
        )

        for item_data in items:
            if not isinstance(
                item_data,
                dict,
            ):
                raise ValidationError(
                    {
                        "items": (
                            "Each item must be "
                            "an object."
                        )
                    }
                )

            product_id = item_data.get(
                "product"
            )

            quantity = item_data.get(
                "quantity"
            )

            if not product_id:
                raise ValidationError(
                    {
                        "product": (
                            "Product is required."
                        )
                    }
                )

            try:
                quantity = int(quantity)
            except (
                TypeError,
                ValueError,
            ):
                raise ValidationError(
                    {
                        "quantity": (
                            "Quantity must be "
                            "an integer."
                        )
                    }
                )

            if quantity < 1 or quantity > 50:
                raise ValidationError(
                    {
                        "quantity": (
                            "Quantity must be "
                            "between 1 and 50."
                        )
                    }
                )

            product = get_object_or_404(
                Product,
                pk=product_id,
                is_available=True,
                category__menu__restaurant_id=(
                    restaurant.id
                ),
            )

            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                final_price=product.base_price,
                notes="",
            )

            modifier_ids = item_data.get(
                "modifiers",
                [],
            )

            if modifier_ids:
                modifier_objects = (
                    ModifierOption.objects
                    .filter(
                        id__in=modifier_ids,
                    )
                )

                order_item.modifiers.set(
                    modifier_objects
                )

        if hasattr(
            order,
            "calculate_totals",
        ):
            order.calculate_totals()
            order.refresh_from_db()

        return Response(
            self.get_serializer(
                order
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="open_or_create",
        url_name="open-or-create",
    )
    @transaction.atomic
    def open_or_create(self, request):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "User is not associated "
                        "with a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        table_id = (
            request.data.get("table")
            or request.data.get("table_id")
        )

        if not table_id:
            return Response(
                {
                    "detail": (
                        "Table ID is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        table = get_object_or_404(
            Table.objects.select_for_update(),
            pk=table_id,
            restaurant_id=restaurant.id,
        )

        table_status = str(
            getattr(
                table,
                "status",
                "AVAILABLE",
            )
        ).strip().upper()

        if table_status == "VACANT":
            table_status = "AVAILABLE"

        if table_status == "IN_USE":
            table_status = "OCCUPIED"

        blocked_statuses = {
            "NEEDS_CLEANING",
            "MERGED",
            "INACTIVE",
        }

        if table_status in blocked_statuses:
            return Response(
                {
                    "detail": (
                        "This table cannot accept "
                        "new orders."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        register_session = (
            self._get_register_session(
                restaurant
            )
        )

        if register_session is None:
            return Response(
                {
                    "detail": (
                        "Open the register before "
                        "creating an order."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        table_session = (
            self._get_active_table_session(
                table=table,
                restaurant=restaurant,
            )
        )

        open_order_statuses = [
            Order.Status.DRAFT,
            Order.Status.PLACED,
            Order.Status.IN_PROGRESS,
            Order.Status.READY,
            Order.Status.SERVED,
        ]

        unpaid_statuses = [
            Order.PaymentStatus.UNPAID,
            Order.PaymentStatus.PARTIALLY_PAID,
        ]

        existing_order = (
            Order.objects
            .select_for_update()
            .filter(
                table_id=table.id,
                restaurant_id=restaurant.id,
                session_id=table_session.id,
                status__in=open_order_statuses,
                payment_status__in=unpaid_statuses,
            )
            .prefetch_related(
                "items",
                "items__product",
                "items__modifiers",
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

        if existing_order is not None:
            self._set_table_occupied(
                table
            )

            return Response(
                self.get_serializer(
                    existing_order
                ).data,
                status=status.HTTP_200_OK,
            )

        order = Order.objects.create(
            restaurant=restaurant,
            table=table,
            session=table_session,
            order_type=Order.OrderType.DINE_IN,
            status=Order.Status.DRAFT,
            payment_status=(
                Order.PaymentStatus.UNPAID
            ),
            created_by=request.user,
        )

        self._set_table_occupied(
            table
        )

        return Response(
            self.get_serializer(
                order
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="send_to_kitchen",
        url_name="send-to-kitchen",
    )
    @transaction.atomic
    def send_to_kitchen(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.payment_status == (
            Order.PaymentStatus.PAID
        ):
            return Response(
                {
                    "detail": (
                        "Paid orders cannot be "
                        "sent back to the kitchen."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.payment_status == (
            Order.PaymentStatus.REFUNDED
        ):
            return Response(
                {
                    "detail": (
                        "Refunded orders cannot be "
                        "sent to the kitchen."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not order.items.exists():
            return Response(
                {
                    "detail": (
                        "Cannot send an empty order "
                        "to the kitchen."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_statuses = [
            Order.Status.DRAFT,
            Order.Status.PLACED,
        ]

        if order.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Order cannot be sent to "
                        "the kitchen from status "
                        f"{order.status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.PLACED

        order.save(
            update_fields=[
                "status",
            ]
        )

        return Response(
            self.get_serializer(
                order
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start_preparing",
        url_name="start-preparing",
    )
    @transaction.atomic
    def start_preparing(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status != (
            Order.Status.PLACED
        ):
            return Response(
                {
                    "detail": (
                        "Only placed orders can "
                        "start preparation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = (
            Order.Status.IN_PROGRESS
        )

        order.save(
            update_fields=[
                "status",
            ]
        )

        return Response(
            self.get_serializer(
                order
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark_ready",
        url_name="mark-ready",
    )
    @transaction.atomic
    def mark_ready(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status != (
            Order.Status.IN_PROGRESS
        ):
            return Response(
                {
                    "detail": (
                        "Only cooking orders can "
                        "be marked ready."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.READY

        order.save(
            update_fields=[
                "status",
            ]
        )

        return Response(
            self.get_serializer(
                order
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark_served",
        url_name="mark-served",
    )
    @transaction.atomic
    def mark_served(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status != (
            Order.Status.READY
        ):
            return Response(
                {
                    "detail": (
                        "Only ready orders can "
                        "be marked served."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.SERVED

        order.save(
            update_fields=[
                "status",
            ]
        )

        return Response(
            self.get_serializer(
                order
            ).data,
            status=status.HTTP_200_OK,
        )

    def _normalize_payment_method(
        self,
        value,
    ):
        normalized = str(
            value or "cash"
        ).strip().lower()

        normalized = normalized.replace(
            "_",
            " ",
        ).replace(
            "-",
            " ",
        )

        normalized = " ".join(
            normalized.split()
        )

        if "cash" in normalized:
            return "cash"

        if (
            "card" in normalized
            or "credit" in normalized
            or "debit" in normalized
            or "visa" in normalized
            or "master" in normalized
        ):
            return "card"

        if (
            "mobile" in normalized
            or "momo" in normalized
            or "mtn" in normalized
            or "airtel" in normalized
            or "orange" in normalized
        ):
            return "mobile"

        return normalized

    def _get_restaurant_payment_method(
        self,
        restaurant,
        requested_method,
    ):
        payment_method_fields = {
            field.name
            for field in PaymentMethod._meta.get_fields()
        }

        method = None

        try:
            method = (
                PaymentMethod.objects
                .filter(
                    pk=requested_method,
                    restaurant_id=restaurant.id,
                )
                .first()
            )
        except (
            TypeError,
            ValueError,
        ):
            method = None

        if method is not None:
            is_active = getattr(
                method,
                "active",
                getattr(
                    method,
                    "is_active",
                    True,
                ),
            )

            if not is_active:
                raise ValidationError(
                    {
                        "payment_method": (
                            "This payment method "
                            "is inactive."
                        )
                    }
                )

            return method

        method_name = (
            self._normalize_payment_method(
                requested_method
            )
        )

        method_query = (
            PaymentMethod.objects
            .filter(
                restaurant_id=restaurant.id,
            )
        )

        if "active" in payment_method_fields:
            method_query = method_query.filter(
                active=True,
            )
        elif "is_active" in payment_method_fields:
            method_query = method_query.filter(
                is_active=True,
            )

        if "slug" in payment_method_fields:
            method_query = method_query.filter(
                Q(
                    name__iexact=method_name
                )
                | Q(
                    slug__iexact=method_name
                )
            )
        else:
            method_query = method_query.filter(
                name__iexact=method_name,
            )

        method = (
            method_query
            .order_by("id")
            .first()
        )

        if method is None:
            raise ValidationError(
                {
                    "payment_method": (
                        f"Payment method "
                        f"'{method_name}' does not "
                        "exist for this restaurant."
                    )
                }
            )

        return method

    @transaction.atomic
    def _mark_order_paid(
        self,
        order,
        restaurant,
        requested_method,
    ):
        locked_order = (
            Order.objects
            .select_for_update()
            .select_related(
                "restaurant",
                "payment_method",
                "table",
                "session",
            )
            .get(
                pk=order.pk,
                restaurant_id=restaurant.id,
            )
        )

        if locked_order.payment_status == (
            Order.PaymentStatus.PAID
        ):
            self._release_order_table(
                locked_order
            )

            return (
                locked_order,
                None,
                False,
            )

        if locked_order.payment_status == (
            Order.PaymentStatus.REFUNDED
        ):
            raise ValidationError(
                {
                    "payment_status": (
                        "A refunded order cannot "
                        "be paid."
                    )
                }
            )

        if hasattr(
            locked_order,
            "calculate_totals",
        ):
            locked_order.calculate_totals()
            locked_order.refresh_from_db()

        amount_to_pay = (
            locked_order.total
            or Decimal("0.00")
        )

        if amount_to_pay <= Decimal(
            "0.00"
        ):
            raise ValidationError(
                {
                    "amount": (
                        "Cannot mark an order with "
                        "a zero total as paid."
                    )
                }
            )

        method_obj = (
            self._get_restaurant_payment_method(
                restaurant=restaurant,
                requested_method=requested_method,
            )
        )

        payment, created = (
            Payment.objects
            .select_for_update()
            .update_or_create(
                order=locked_order,
                defaults={
                    "amount": amount_to_pay,
                    "method": method_obj,
                    "status": "PAID",
                },
            )
        )

        locked_order.payment_method = (
            method_obj
        )

        locked_order.payment_status = (
            Order.PaymentStatus.PAID
        )

        locked_order.save(
            update_fields=[
                "payment_method",
                "payment_status",
            ]
        )

        self._release_order_table(
            locked_order
        )

        return (
            locked_order,
            payment,
            created,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark_paid",
        url_name="mark-paid",
    )
    @transaction.atomic
    def mark_paid(
        self,
        request,
        pk=None,
    ):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "User is not associated "
                        "with a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        requested_method = (
            request.data.get(
                "payment_method"
            )
            or request.data.get("method")
            or "cash"
        )

        try:
            (
                locked_order,
                payment,
                created,
            ) = self._mark_order_paid(
                order=order,
                restaurant=restaurant,
                requested_method=requested_method,
            )
        except ValidationError as error:
            return Response(
                error.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment is None:
            return Response(
                {
                    "detail": (
                        "Order is already paid."
                    ),
                    "order_id": str(
                        locked_order.id
                    ),
                    "payment_status": (
                        locked_order.payment_status
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "Payment confirmed and "
                    "table released."
                ),
                "payment": {
                    "id": str(payment.id),
                    "amount": str(
                        payment.amount
                    ),
                    "status": payment.status,
                    "method": getattr(
                        payment.method,
                        "name",
                        None,
                    ),
                    "created": created,
                },
                "order": self.get_serializer(
                    locked_order
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
        url_name="complete",
    )
    @transaction.atomic
    def complete(
        self,
        request,
        pk=None,
    ):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "User is not associated "
                        "with a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.payment_status != (
            Order.PaymentStatus.PAID
        ):
            return Response(
                {
                    "detail": (
                        "Order must be paid before "
                        "completion."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status == (
            Order.Status.COMPLETED
        ):
            self._release_order_table(
                order
            )

            return Response(
                {
                    "detail": (
                        "Order is already completed."
                    ),
                    "order": self.get_serializer(
                        order
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        if hasattr(
            order,
            "deduct_inventory",
        ):
            order.deduct_inventory()

        order.status = (
            Order.Status.COMPLETED
        )

        order.save(
            update_fields=[
                "status",
            ]
        )

        self._release_order_table(
            order
        )

        return Response(
            {
                "message": (
                    "Order completed and "
                    "table released."
                ),
                "order": self.get_serializer(
                    order
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="refund",
        url_name="refund",
    )
    @transaction.atomic
    def refund(
        self,
        request,
        pk=None,
    ):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "User is not associated "
                        "with a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = (
            self.get_queryset()
            .select_for_update()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.payment_status != (
            Order.PaymentStatus.PAID
        ):
            return Response(
                {
                    "detail": (
                        "Only paid orders can "
                        "be refunded."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.payment_status = (
            Order.PaymentStatus.REFUNDED
        )

        order.status = (
            Order.Status.CANCELED
        )

        order.save(
            update_fields=[
                "payment_status",
                "status",
            ]
        )

        self._release_order_table(
            order
        )

        Payment.objects.filter(
            order=order,
        ).update(
            status="REFUNDED",
        )

        return Response(
            {
                "message": (
                    "Order refunded and "
                    "table released."
                ),
                "order": self.get_serializer(
                    order
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="print-receipt",
        url_name="print-receipt",
        renderer_classes=[
            StaticHTMLRenderer,
        ],
    )
    def print_receipt(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        items = order.items.all()

        total_payment = (
            order.payments.aggregate(
                total=Sum("amount"),
            )["total"]
            or Decimal("0.00")
        )

        html_content = render_to_string(
            "receipts/order_receipt.html",
            {
                "order": order,
                "items": items,
                "restaurant": order.restaurant,
                "total_payment": total_payment,
            },
        )

        return Response(
            html_content,
            content_type="text/html",
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="print-kitchen",
        url_name="print-kitchen",
        renderer_classes=[
            StaticHTMLRenderer,
        ],
    )
    def print_kitchen(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .filter(
                pk=pk,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        items = order.items.all()

        html_content = render_to_string(
            "receipts/kitchen_ticket.html",
            {
                "order": order,
                "items": items,
            },
        )

        return Response(
            html_content,
            content_type="text/html",
        )
        
            
class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def _get_restaurant(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return None

        restaurant = getattr(
            user,
            "restaurant",
            None,
        )

        if restaurant is None:
            profile = getattr(
                user,
                "userprofile",
                None,
            )

            if profile is not None:
                restaurant = getattr(
                    profile,
                    "restaurant",
                    None,
                )

        return restaurant

    def get_queryset(self):
        restaurant = self._get_restaurant()

        if restaurant is None:
            return OrderItem.objects.none()

        return (
            OrderItem.objects
            .filter(
                order__restaurant_id=restaurant.id,
            )
            .select_related(
                "order",
                "order__restaurant",
                "product",
                "variant",
            )
            .prefetch_related(
                "modifiers",
            )
            .order_by(
                "-id",
            )
        )

    def perform_create(self, serializer):
        restaurant = self._get_restaurant()

        if restaurant is None:
            raise PermissionDenied(
                "User is not assigned to a restaurant."
            )

        order_id = self.request.data.get(
            "order"
        )

        if not order_id:
            raise ValidationError(
                {
                    "order": (
                        "Order ID is required."
                    )
                }
            )

        order = get_object_or_404(
            Order,
            id=order_id,
            restaurant_id=restaurant.id,
        )

        if order.payment_status == Order.PaymentStatus.PAID:
            raise ValidationError(
                {
                    "order": (
                        "Paid orders cannot receive "
                        "new items."
                    )
                }
            )

        if order.status in [
            Order.Status.COMPLETED,
            Order.Status.CANCELED,
        ]:
            raise ValidationError(
                {
                    "order": (
                        "Completed or canceled orders "
                        "cannot receive items."
                    )
                }
            )

        item = serializer.save(
            order=order,
        )

        order.calculate_totals()

        return item

    def perform_update(self, serializer):
        item = OrderItemSerializer.create()

        item.order.calculate_totals()

    def perform_destroy(self, instance):
        order = instance.order

        instance.delete()

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


class ProductViewSet(viewsets.ModelViewSet): # Changed from ReadOnlyModelViewSet to allow updates
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        user = self.request.user
        
        # Base queryset with optimized lookups
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

    @action(detail=True, methods=['get'], url_path='recipe')
    def get_recipe(self, request, pk=None):
        """Fetch the ingredients linked to this product"""
        product = self.get_object()
        ingredients = ProductIngredient.objects.filter(product=product).select_related('inventory_item')
        
        data = [{
            "inventory_item": ing.inventory_item.id,
            "inventory_item_name": ing.inventory_item.name,
            "quantity_required": ing.quantity_required,
            "unit": ing.inventory_item.unit
        } for ing in ingredients]
        
        return Response(data)

    @action(detail=True, methods=['post'], url_path='update_recipe')
    def update_recipe(self, request, pk=None):
        """Update or create the recipe for this product"""
        product = self.get_object()
        ingredients_data = request.data.get('ingredients', [])

        try:
            with transaction.atomic():
                # 1. Clear existing recipe for this product
                ProductIngredient.objects.filter(product=product).delete()

                # 2. Re-create ingredients from the provided list
                for item in ingredients_data:
                    inv_item_id = item.get('inventory_item')
                    qty = item.get('quantity_required')
                    
                    if inv_item_id and qty:
                        ProductIngredient.objects.create(
                            product=product,
                            inventory_item_id=inv_item_id,
                            quantity_required=qty
                        )

            return Response({"message": "Recipe updated successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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



class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return methods belonging to the logged-in user's restaurant
        if not self.request.user.restaurant:
            return PaymentMethod.objects.none()
            
        return PaymentMethod.objects.filter(
            restaurant=self.request.user.restaurant, 
            active=True
        )



@method_decorator(never_cache, name="dispatch")
class PaymentSummaryAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_restaurant(self, request):
        """
        Return the restaurant assigned to the authenticated user.
        """

        user = request.user

        if not user or not user.is_authenticated:
            return None

        return getattr(user, "restaurant", None)

    def get_today_bounds(self):
        """
        Return today's local date and timezone-aware boundaries.

        Make sure settings.py contains:

            TIME_ZONE = "Asia/Hong_Kong"
            USE_TZ = True
        """

        now_local = timezone.localtime(
            timezone.now()
        )

        start_of_today = now_local.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end_of_today = (
            start_of_today
            + timezone.timedelta(days=1)
        )

        return (
            now_local.date(),
            start_of_today,
            end_of_today,
        )

    def money(self, value):
        """
        Convert Decimal or None into a JSON-safe float.
        """

        return float(
            value or Decimal("0.00")
        )

    def get_method_display_name(self, payment_method):
        if not payment_method:
            return None

        if hasattr(
            payment_method,
            "get_name_display",
        ):
            return payment_method.get_name_display()

        return payment_method.name

    def get_order_payload(self, order):
        """
        Convert one Order into the frontend transaction shape.
        """

        payment_method = order.payment_method
        created_at = order.created_at

        local_created_at = None

        if created_at:
            local_created_at = timezone.localtime(
                created_at
            )

        if payment_method:
            method_code = payment_method.name
            method_display_name = (
                self.get_method_display_name(
                    payment_method
                )
            )
        else:
            method_code = None
            method_display_name = None

        if order.order_number is not None:
            order_reference = (
                f"ORD-{order.order_number}"
            )
        else:
            order_reference = (
                f"ORD-{str(order.id)[:6].upper()}"
            )

        return {
            # Order.id is a UUID in your model.
            "id": str(order.id),

            # Human-readable order reference.
            "order_number": order_reference,

            "method": method_code,
            "method_name": method_display_name,

            "amount": self.money(order.total),

            # Uses Order.payment_status as the source of truth.
            "status": order.payment_status,

            "created_at": (
                created_at.isoformat()
                if created_at
                else None
            ),

            "date": (
                local_created_at.strftime(
                    "%Y-%m-%d %H:%M"
                )
                if local_created_at
                else None
            ),
        }

    def get(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {
                    "detail": "Authentication required."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        restaurant = self.get_restaurant(request)

        if restaurant is None:
            return Response(
                {
                    "detail": (
                        "Authenticated user is not assigned "
                        "to a restaurant."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        (
            today,
            start_of_today,
            end_of_today,
        ) = self.get_today_bounds()

        # ==========================================================
        # TENANT BOUNDARY
        # ==========================================================
        #
        # Every statistic and every recent order is derived from
        # this queryset. Never use Order.objects.all() below.
        #
        orders = (
            Order.objects
            .filter(
                restaurant_id=restaurant.id,
            )
            .select_related(
                "restaurant",
                "payment_method",
            )
        )

        # ==========================================================
        # DATE FILTERS
        # ==========================================================

        today_orders = orders.filter(
            created_at__gte=start_of_today,
            created_at__lt=end_of_today,
        )

        # ==========================================================
        # STATUS FILTERS
        # ==========================================================

        paid_statuses = {
            Order.PaymentStatus.PAID,
            "PAID",
            "paid",
            "Paid",
        }

        unpaid_statuses = {
            Order.PaymentStatus.UNPAID,
            "UNPAID",
            "unpaid",
            "Unpaid",
        }

        partially_paid_statuses = {
            Order.PaymentStatus.PARTIALLY_PAID,
            "PARTIALLY_PAID",
            "partially_paid",
            "Partially Paid",
        }

        excluded_order_statuses = {
            Order.Status.CANCELED,
            Order.Status.COMPLETED,
            "CANCELED",
            "COMPLETED",
            "canceled",
            "completed",
        }

        paid_orders = orders.filter(
            payment_status__in=paid_statuses,
        )

        paid_today_orders = today_orders.filter(
            payment_status__in=paid_statuses,
        )

        # Pending means unpaid or partially paid and not canceled
        # or completed.
        unpaid_pending_orders = (
            orders
            .filter(
                Q(
                    payment_status__in=unpaid_statuses
                )
                | Q(
                    payment_status__in=partially_paid_statuses
                )
            )
            .exclude(
                status__in=excluded_order_statuses,
            )
        )

        # ==========================================================
        # TOTALS
        # ==========================================================

        total_today = (
            today_orders.aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        total_paid = (
            paid_orders.aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        total_paid_today = (
            paid_today_orders.aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        unpaid_pending = (
            unpaid_pending_orders.aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        gross_sales_volume = (
            orders.aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        # ==========================================================
        # PAID TOTALS BY PAYMENT METHOD
        # ==========================================================

        cash = (
            paid_orders
            .filter(
                Q(
                    payment_method__name__iexact="cash"
                )
                | Q(
                    payment_method__slug__iexact="cash"
                )
            )
            .aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        card = (
            paid_orders
            .filter(
                Q(
                    payment_method__name__iexact="card"
                )
                | Q(
                    payment_method__slug__iexact="card"
                )
                | Q(
                    payment_method__name__iexact="credit card"
                )
                | Q(
                    payment_method__slug__iexact="credit-card"
                )
            )
            .aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        mobile = (
            paid_orders
            .filter(
                Q(
                    payment_method__name__iexact="mobile"
                )
                | Q(
                    payment_method__slug__iexact="mobile"
                )
                | Q(
                    payment_method__name__iexact="mobile_pay"
                )
                | Q(
                    payment_method__slug__iexact="mobile-pay"
                )
                | Q(
                    payment_method__name__iexact="mobile payment"
                )
                | Q(
                    payment_method__slug__iexact="mobile-payment"
                )
                | Q(
                    payment_method__name__iexact="momo"
                )
                | Q(
                    payment_method__slug__iexact="momo"
                )
            )
            .aggregate(
                total=Sum("total"),
            )["total"]
            or Decimal("0.00")
        )

        # ==========================================================
        # RECENT ORDERS
        # ==========================================================
        #
        # This includes unpaid orders, so the frontend heading
        # should say "Recent Orders", not "Recent Transactions".
        #
        recent_orders = (
            orders
            .order_by("-created_at")[:10]
        )

        payments = [
            self.get_order_payload(order)
            for order in recent_orders
        ]

        # ==========================================================
        # SERVER DIAGNOSTICS
        # ==========================================================
        #
        # Keep temporarily while testing. Remove later.
        #
        print(
            "PAYMENT SUMMARY TOTALS:",
            {
                "user_id": user.id,
                "username": user.username,
                "restaurant_id": restaurant.id,
                "restaurant_name": restaurant.name,
                "today": str(today),
                "start_of_today": str(
                    start_of_today
                ),
                "end_of_today": str(
                    end_of_today
                ),
                "all_orders": orders.count(),
                "today_orders": today_orders.count(),
                "paid_orders": paid_orders.count(),
                "paid_today_orders": (
                    paid_today_orders.count()
                ),
                "unpaid_pending_orders": (
                    unpaid_pending_orders.count()
                ),
                "total_today": str(total_today),
                "total_paid": str(total_paid),
                "total_paid_today": str(
                    total_paid_today
                ),
                "unpaid_pending": str(
                    unpaid_pending
                ),
                "cash": str(cash),
                "card": str(card),
                "mobile": str(mobile),
            },
            flush=True,
        )

        response_data = {
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.name,
            },
            "stats": {
                "total_today": self.money(
                    total_today
                ),
                "total_paid": self.money(
                    total_paid
                ),
                "total_paid_today": self.money(
                    total_paid_today
                ),
                "pending": self.money(
                    unpaid_pending
                ),
                "unpaid_pending": self.money(
                    unpaid_pending
                ),
                "active_table_balances": self.money(
                    unpaid_pending
                ),
                "total_count": orders.count(),
                "total_amount": self.money(
                    gross_sales_volume
                ),
                "gross_sales_volume": self.money(
                    gross_sales_volume
                ),
                "confirmed_in_bank_drawer": self.money(
                    total_paid_today
                ),
                "cash": self.money(cash),
                "credit_card": self.money(card),
                "card": self.money(card),
                "mobile": self.money(mobile),
                "mobile_pay": self.money(mobile),
            },
            "payments": payments,
        }

        response = Response(
            response_data,
            status=status.HTTP_200_OK,
        )

        response["Cache-Control"] = (
            "no-store, no-cache, "
            "must-revalidate, max-age=0"
        )
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        return response
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


def order_status_api(request, token, order_id):
    # ✅ Validate QR session
    if not validate_qr_session(request, token):
        return Response({"error": "Session expired"}, status=HTTP_403_FORBIDDEN)

    table_id = request.session.get("table_id")
    restaurant_id = request.session.get("restaurant_id")

    if not table_id or not restaurant_id:
        return Response({"error": "Unauthorized"}, status=HTTP_403_FORBIDDEN)

    order = get_object_or_404(
        Order,
        id=order_id,
        table_id=table_id,
        restaurant_id=restaurant_id
    )

    return Response({"status": order.status}, status=HTTP_200_OK)

    
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


@api_view(['GET', 'POST'])
def subscription_status(request):
    restaurant = request.user.restaurant_profile # Adjust based on your User model
    subscription = restaurant.subscription

    if request.method == 'GET':
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    if request.method == 'POST':
        # User is reporting a payment
        method = request.data.get('offline_payment_method')
        ref = request.data.get('offline_payment_reference')
        
        subscription.offline_payment_method = method
        subscription.offline_payment_reference = ref
        subscription.offline_payment_notes = f"User reported payment via {method} at {timezone.now()}"
        # We DON'T change status to ACTIVE yet. Admin does that.
        subscription.save()
        
        return Response({"status": "submitted", "message": "Verification pending."})

    
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
        session=register_session,
        table=table,
        **validated_data,
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
    
    

class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    
    def get_queryset(self):
        # Ensure user is authenticated before filtering
        if not self.request.user.is_authenticated:
            return RegisterSession.objects.none()
        return RegisterSession.objects.filter(restaurant=self.request.user.restaurant)

    def perform_create(self, serializer):
        # PREVENT DUPLICATE SESSIONS: 
        # Check if there is already an active session for this restaurant
        active_session = RegisterSession.objects.filter(
            restaurant=self.request.user.restaurant, 
            status='OPEN'
        ).exists()
        
        if active_session:
            raise serializer.ValidationError({"detail": "A session is already open for this restaurant."})
        
        serializer.save(
            restaurant=self.request.user.restaurant,
            opened_by=self.request.user,
            status='OPEN'
        )

    @action(detail=False, methods=['get'])
    def active(self, request):
        # Finds the most recent open session for this restaurant
        session = self.get_queryset().filter(status='OPEN').order_by('-start_time').first()
        if not session:
            return Response(None, status=200) # Return null instead of 404 to help frontend logic
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        session = self.get_object()
        end_amount = request.data.get('end_amount')
        
        if not end_amount:
            return Response({"error": "Closing amount is required"}, status=400)
            
        session.status = 'CLOSED'
        session.end_amount = end_amount
        session.end_time = timezone.now()
        session.save()
        
        return Response({"status": "Session closed successfully"})
    
    
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Logic for your existing PaymentsPage"""
        today = timezone.now().date()
        payments = (
            Payment.objects
            .filter(created_at__date=today)
            .select_related("method", "order")
        )

        stats = {
            "total_today": sum(p.amount for p in payments),
            "total_paid": sum(p.amount for p in payments if p.status == 'PAID'),
            "pending": sum(p.amount for p in payments if p.status == 'PENDING'),
            "total_count": payments.count(),  # Use payments.count() instead of queryset.count()
            "total_amount": sum(p.amount for p in payments),
            "gross_sales_volume": sum(p.order.total for p in payments),
            "confirmed_in_bank_drawer": sum(p.amount for p in payments if p.status == 'CONFIRMED'), 
            "cash": sum(p.amount for p in payments if p.method and p.method.name == 'cash'),
            "credit_card": sum(p.amount for p in payments if p.method and p.method.name == 'card'),
            "mobile": sum(
                            p.amount for p in payments
                            if p.method and "mobile" in p.method.name.lower()),      
        }

        payment_list = [
            {
                "id": str(p.id),
                "order_number": p.order.short_id() if hasattr(p.order, 'short_id') and callable(p.order.short_id) else str(p.order.id)[:4],
                "method_name": p.method.name if p.method else None,
                "amount": float(p.amount),
                "status": p.status,
                "date": p.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for p in payments
        ]

        return Response({"stats": stats, "payments": payment_list})

    def create(self, request, *args, **kwargs):
        """Handle new payment from POS"""
        order_id = request.data.get('order')
        amount = request.data.get('amount')
        method_name = request.data.get('method') or "Cash"

        from core.models import Payment, PaymentMethod

        try:
            with transaction.atomic():
                order = Order.objects.get(id=order_id)
                restaurant = order.restaurant

                # Resolve or create PaymentMethod
                method_obj, _ = PaymentMethod.objects.get_or_create(
                    restaurant=restaurant,
                    name__iexact=method_name,
                    defaults={"name": method_name.capitalize(), "active": True},
                )

                # 1. Create the Payment Record
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    method=method_obj,  # Use FK, not method_name
                    status='PAID',
                )

                # 2. Update the Order Status 
                order.status = 'PAID'
                order.payment_method = method_obj  # Update order payment method
                order.save()

                return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
