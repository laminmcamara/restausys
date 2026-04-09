# core/views.py

import uuid, csv, json
from datetime import timedelta, datetime
from django.contrib.auth.views import LoginView, LogoutView
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

from django.views.generic import (
    TemplateView, ListView, DetailView
)
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

from openpyxl import Workbook

# DRF
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.serializers.json import DjangoJSONEncoder

from rest_framework.decorators import api_view, permission_classes
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from .stripe_utils import create_payment_intent
from django.views.generic import UpdateView

# TENANT BASE
from core.tenant import TenantModelViewSet
from .forms import ProductForm
from functools import wraps

# CORE IMPORTS
from .models import (
    Order, OrderItem, Category, Product,
    Table, Payment, KitchenTicket, Settings, ModifierGroup, ModifierOption, Restaurant

)
from .serializers import (
    OrderSerializer, OrderItemSerializer,
    CategorySerializer, ProductSerializer,
    TableSerializer, PaymentSerializer
)
from .permissions import IsStaffOfRestaurant
from django.contrib.auth import get_user_model

User = get_user_model()




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
# POS DASHBOARD (ROLE-DRIVEN + PROTECTED)
# ======================================================================

class PosDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/pos/dashboard.html"

    # ==========================================================
    # ✅ BACKEND ROLE PROTECTION
    # ==========================================================
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # Superuser always allowed
        if user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        # Only Cashier or Manager allowed
        if not (user.is_cashier or user.is_manager):
            raise PermissionDenied("You are not authorized to access POS.")

        return super().dispatch(request, *args, **kwargs)

    # ==========================================================
    # ✅ CONTEXT DATA
    # ==========================================================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        restaurant = user.restaurant

        # ======================================================
        # ✅ SALES DATA
        # ======================================================
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

        # ======================================================
        # ✅ POS DATA (FOR JS)
        # ======================================================
        categories = list(
            Category.objects.filter(menu__restaurant=restaurant)
            .values("id", "name", "parent_id")
        )

        products = list(
            Product.objects.filter(
                category__menu__restaurant=restaurant,
                is_available=True
            ).values(
                "id",
                "name",
                "base_price",
                "category_id",
                "image",
            )
        )

        modifier_groups = list(
            ModifierGroup.objects.filter(
                products__category__menu__restaurant=restaurant
            )
            .distinct()
            .values("id", "name", "selection_type")
        )

        modifier_options = list(
            ModifierOption.objects.filter(
                group__products__category__menu__restaurant=restaurant
            )
            .distinct()
            .values(
                "id",
                "group_id",
                "name",
                "price_adjustment",
            )
        )

        pos_data = {
            "categories": categories,
            "products": products,
            "modifier_groups": modifier_groups,
            "modifier_options": modifier_options,
        }

        context["pos_data_json"] = json.dumps(pos_data, cls=DjangoJSONEncoder)

        # ======================================================
        # ✅ ROLE-DRIVEN DASHBOARD SECTIONS
        # ======================================================

        sections = []

        # ---- CASHIER SECTION ----
        if user.is_cashier:
            sections.append({
                "title": "Cashier",
                "items": [
                    {
                        "name": "Start Shift",
                        "url": "core:start_shift",
                        "icon": "bi-play-circle",
                        "color": "bg-green-600 hover:bg-green-500",
                    },
                    {
                        "name": "End Shift",
                        "url": "core:end_shift",
                        "icon": "bi-stop-circle",
                        "color": "bg-red-600 hover:bg-red-500",
                    },
                ],
            })

        # ---- MANAGEMENT SECTION ----
        if user.is_manager or user.is_superuser:
            sections.append({
                "title": "Management",
                "items": [
                    {
                        "name": "Manager",
                        "url": "core:manager_dashboard",
                        "icon": "bi-briefcase",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                        "name": "Restaurant",
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
                        "name": "Admin",
                        "url": "admin:index",
                        "icon": "bi-shield-lock",
                        "color": "bg-blue-900/40 hover:bg-orange-500",
                    },
                    {
                    "name": "Daily Reports",
                    "url": "core:daily_reports",
                    "icon": "bi-calendar",
                    "color": "bg-indigo-600 hover:bg-indigo-700"
                    },
                    {
                    "name": "Analytics",
                    "url": "core:analytics",
                    "icon": "bi-graph-up",
                    "color": "bg-emerald-600 hover:bg-emerald-700"
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
        status=Order.Status.PAID
    )

    total_revenue = orders.aggregate(
        total=Sum("items__final_price")
    )["total"] or 0

    return today, orders, total_revenue


class DailyReportsListView(LoginRequiredMixin, ListView):
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

class AnalyticsAPIView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):

        if (request.user.role or "").lower() != "manager" and not request.user.is_superuser:            
            raise PermissionDenied("manager only.")

    def get(self, request):
        today = timezone.now().date()

        orders = Order.objects.filter(
            restaurant=request.user.restaurant,
            created_at__date=today,
            status=Order.Status.PAID
        )

        total_orders = orders.count()

        total_revenue = orders.aggregate(
            total=Sum("items__final_price")
        )["total"] or 0

        avg_order = total_revenue / total_orders if total_orders else 0

        # ✅ Status counts
        status_counts = {
            "ready": Order.objects.filter(
                restaurant=request.user.restaurant,
                created_at__date=today,
                status=Order.Status.READY
            ).count()
        }

        # ✅ Revenue by hour
        hourly = orders.annotate(
            hour=ExtractHour("created_at")
        ).values("hour").annotate(
            total=Sum("items__final_price")
        ).order_by("hour")

        hourly_revenue = [
            {"hour": x["hour"], "total": float(x["total"] or 0)}
            for x in hourly
        ]

        # ✅ Best selling items
        best_items_qs = orders.values(
            "items__menu_item__name"
        ).annotate(
            qty=Count("items")
        ).order_by("-qty")[:5]

        best_items = [
            {
                "name": x["items__menu_item__name"],
                "qty": x["qty"]
            }
            for x in best_items_qs
        ]

        return JsonResponse({
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "avg_order": float(avg_order),
            "status_counts": status_counts,
            "hourly_revenue": hourly_revenue,
            "best_items": best_items,
        })


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/analytics.html"

    def dispatch(self, request, *args, **kwargs):

        if (request.user.role or "").lower() != "manager" and not request.user.is_superuser:
            raise PermissionDenied("Manager only.")

        return super().dispatch(request, *args, **kwargs)
    
# ======================================================================
# ORDER TEMPLATE VIEWS (SECURED)
# ======================================================================

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

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/order_detail.html"

    def get_queryset(self):
        return Order.objects.filter(
            restaurant=self.request.user.restaurant
        )
        
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
        ).order_by("name")
        
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
        return Order.objects.filter(
            restaurant=self.request.user.restaurant
        )
        
        
# ✅ Public Table Menu View
def public_table_menu(request, token):
    table = get_object_or_404(Table, access_token=token)

    products = Product.objects.filter(
        category__restaurant=table.restaurant,
        is_available=True
    )

    return render(request, "customer/menu.html", {
        "table": table,
        "restaurant": table.restaurant,
        "products": products,
    })


# ✅ Order Status Page View  <-- ADD IT HERE
def table_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(request, "core/table_order_status.html", {
        "order": order
    })
    
    
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
        restaurant = self.request.user.restaurant

        return Product.objects.filter(
            category__menu__restaurant=restaurant,
            is_available=True
        ).select_related(
            "category"
        ).prefetch_related(
            "modifier_groups__options"
        )

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(
            order__restaurant=self.request.user.restaurant
        )

@login_required
def create_takeout_order(request):
    if request.method == "POST":
        data = json.loads(request.body)
        restaurant = request.user.restaurant

        order = Order.objects.create(
            restaurant=restaurant,
            order_type=Order.OrderType.TAKEOUT,
            status=Order.Status.PLACED,
            staff=request.user
        )

        for product_id, item in data.items():
            product = get_object_or_404(
                Product,
                id=product_id,
                category__menu__restaurant=restaurant,
                is_available=True
            )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item["qty"],
                final_price=product.base_price * item["qty"]
            )

        order.calculate_totals()

        return JsonResponse({
            "success": True,
            "order_id": order.id,
            "order_number": order.order_number
        })

    return JsonResponse({"success": False})


def pay_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Mark order as paid
    order.status = "PAID"
    order.save(update_fields=["status"])

    messages.success(request, "Order paid successfully.")

    return redirect("table_order_status", order_id=order.id)

# ======================================================================
# POS API ENDPOINTS
# ======================================================================

class PosDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = request.user.restaurant

        categories = Category.objects.filter(
            menu__restaurant=restaurant
        )

        products = Product.objects.filter(
            category__menu__restaurant=restaurant,
            is_available=True
        )

        tables = Table.objects.filter(
            restaurant=restaurant
        )

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
            status=Order.Status.PLACED
        )

        return Response(OrderSerializer(order).data)

@login_required
def order_receipt(request, pk):

    if not hasattr(request.user, "restaurant"):
        raise PermissionDenied("No restaurant assigned.")

    order = get_object_or_404(
        Order,
        pk=pk,
        restaurant=request.user.restaurant
    )

    return render(request, "orders/order_receipt.html", {
        "order": order
    })
    
def order_status_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return JsonResponse({
        "status": order.status
    })
    
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

    if order.status == Order.Status.PAID:
        return Response(
            {"error": "Order already paid"},
            status=400
        )

    intent = create_payment_intent(order)

    Payment.objects.update_or_create(
        order=order,
        defaults={
            "stripe_payment_intent": intent.id,
            "amount": order.total_price(),
        }
    )

    qr_url = request.build_absolute_uri(
        reverse("core:pay_order", args=[order.id])
    )

    return Response({
        "qr_url": qr_url,
        "client_secret": intent.client_secret
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
        if request.user.role != "manager":
            return redirect("core:pos_dashboard")

        return super().dispatch(request, *args, **kwargs)
    
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

        active_orders = Order.objects.filter(
            restaurant=self.request.user.restaurant,
            status=Order.Status.PLACED
        )

        tables_in_use = Table.objects.filter(
            restaurant=self.request.user.restaurant,
            status__in=[
                Table.Status.OCCUPIED,
                Table.Status.RESERVED,
            ]
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
                Order.Status.COMPLETED,
                Order.Status.CANCELED,
            ],
            payment_status=Order.PaymentStatus.PAID
        ).select_related("table")

        context.update({
            "tables": tables,
            "active_orders": active_orders,
        })

        return context
    



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

        if user.role == "manager":
            return reverse_lazy("core:manager_dashboard")

        if user.role == "staff":
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
    return redirect("core:table-overview")


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


@login_required
def kitchen_queue_count(request):
    restaurant = request.user.restaurant
    count = Order.objects.filter(
        restaurant=restaurant,
        status=Order.Status.IN_PROGRESS
    ).count()

    return HttpResponse(
        f'<span class="absolute top-2 right-2 bg-yellow-500 text-black text-xs px-2 py-0.5 rounded-full">{count}</span>'
    )
    
def start_shift(request):
    return HttpResponse("Shift started")

def end_shift(request):
    return HttpResponse("Shift ended")


@login_required
def create_staff(request):
    if not request.user.can_manage_staff:
        raise PermissionDenied("You are not allowed to create staff.")
    
    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            form.save(restaurant=request.user.restaurant)
            return redirect("staff_list")
    else:
        form = StaffCreateForm()

    return render(request, "core/create_staff.html", {"form": form})

@login_required
def staff_list(request):
    if not request.user.can_manage_staff:
        raise PermissionDenied()

    staff = User.objects.filter(restaurant=request.user.restaurant)

    return render(request, "core/staff_list.html", {
        "staff": staff
    })


@login_required
def manage_products(request):
    if request.user.role != "MANAGER":
        return redirect("core:dashboard")

    products = Product.objects.filter(restaurant=request.user.restaurant)

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.restaurant = request.user.restaurant
            product.save()
            return redirect("core:manage_products")
    else:
        form = ProductForm()

    context = {
        "products": products,
        "form": form,
    }
    return render(request, "core/dashboard/manage_products.html", context)

def public_table_menu(request, token):
    table = get_object_or_404(Table, access_token=token)

    products = Product.objects.filter(
        category__restaurant=table.restaurant,
        is_available=True
    ).select_related("category")

    return render(request, "customer/menu.html", {
        "table": table,
        "restaurant": table.restaurant,
        "products": products,
    })
    
@login_required
def print_all_qr_codes(request):
    restaurant = request.user.restaurant
    tables = restaurant.tables.all().order_by("table_number")

    return render(request, "core/print_all_qr.html", {
        "tables": tables,
        "restaurant": restaurant
    })