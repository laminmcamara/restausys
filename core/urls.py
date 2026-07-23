from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import *
from .views import (
    ProductListView,
    ProductUpdateView,
    ProductDeleteView,
)
app_name = "core"

# ============================================================
# DRF ROUTER
# ============================================================

router = DefaultRouter()
router.register(r"tables", TableViewSet, basename="table")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"manager/products", ManagerProductViewSet, basename="manager-products")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"order-items", OrderItemViewSet, basename="orderitem")
router.register(r"payments", PaymentViewSet, basename="payment")

# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

    # ========================================================
    # MAIN
    # ========================================================
    path("", IndexView.as_view(), name="home"),

    # ========================================================
    # AUTH
    # ========================================================
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="core:login"), name="logout"),

    path("password-reset/",
         auth_views.PasswordResetView.as_view(
             template_name="core/registration/password_reset.html"),
         name="password_reset"),

    path("password-reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="core/registration/password_reset_done.html"),
         name="password_reset_done"),

    path("reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="core/registration/password_reset_confirm.html"),
         name="password_reset_confirm"),

    path("reset/done/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="core/registration/password_reset_complete.html"),
         name="password_reset_complete"),

    # JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ========================================================
    # DASHBOARDS
    # ========================================================
    path("dashboard/", DashboardRouterView.as_view(), name="dashboard"),
    path("manager-dashboard/", ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("restaurant-dashboard/", RestaurantDashboardView.as_view(), name="restaurant_dashboard"),
    path("register/", register_restaurant, name="register"),
    path("subscription-expired/", subscription_expired, name="subscription_expired"),

    # ========================================================
    # POS
    # ========================================================
    path("pos/", PosDashboardView.as_view(), name="pos_dashboard"),
    path("pos/<uuid:order_id>/", pos_view, name="pos"),

    path("pos/<uuid:order_id>/add/<uuid:variant_id>/",
         add_to_order, name="add_to_order"),

    path("pos/<uuid:order_id>/update/<int:item_id>/",
         update_quantity, name="update_quantity"),

    path("pos/<uuid:order_id>/remove/<int:item_id>/",
         remove_item, name="remove_item"),

    path("api/v1/pos-data/", PosDataView.as_view(), name="pos_data"),

    # ========================================================
    # TABLES & SESSIONS
    # ========================================================
    path("pos/tables/", TableOverviewView.as_view(), name="table_overview"),

    path("dashboard/tables/<int:table_id>/open/",
         dashboard_table_open, name="dashboard_table_open"),

    path("dashboard/sessions/<int:session_id>/",
         dashboard_session_detail, name="dashboard_session_detail"),

    path("dashboard/sessions/<int:session_id>/orders/create/",
         dashboard_create_order, name="dashboard_create_order"),

    path("dashboard/sessions/<int:session_id>/close/",
         dashboard_table_close, name="dashboard_table_close"),

    path("sessions/<int:pk>/receipt/",
         session_receipt_pdf, name="session_receipt_pdf"),

    path("tables/<int:pk>/print/",
         PrintQRView.as_view(), name="print_qr"),

    path("tables/<int:pk>/regenerate/",
         regenerate_qr, name="regenerate_qr"),

    path("table/<uuid:token>/",
         public_table_menu, name="public_table_menu"),


    path(
        "table/<uuid:token>/place-order/",
        place_table_order,
        name="place-table-order"
    ),
    
    
    path(
        "table/<uuid:token>/checkout/",
        table_checkout,
        name="table-checkout"
    ),

    
    # ========================================================
    # ORDERS
    # ========================================================
    path("orders/", OrderListView.as_view(), name="orders"),
    
    path("orders/<uuid:pk>/complete/",
        complete_order,
        name="complete_order"),
    
    path(
        "orders/<uuid:pk>/send-to-kitchen/",
        send_to_kitchen,
        name="send_to_kitchen",
    ),
    
    path("orders/<uuid:pk>/",
         OrderDetailView.as_view(), name="order_detail"),

    # ✅ FIXED UUID HERE
    path("orders/<uuid:order_id>/add/<uuid:product_id>/",
         add_order_item, name="add-order-item"),

    path("orders/<uuid:pk>/receipt/",
         order_receipt, name="order-receipt"),

    path("orders/takeaway/new/",
         create_takeaway_order, name="create_takeaway_order"),

    path(
        "table/<uuid:token>/order/<uuid:order_id>/",
        table_order_status,
        name="table-order-status"
    ),

    path(
        "api/table/<uuid:token>/order/<uuid:order_id>/status/",
        order_status_api,
        name="order_status_api"
    ),
    path("order-success/<int:order_id>/",
         OrderSuccessView.as_view(), name="order_success"),

    # ========================================================
    # PAYMENTS
    # ========================================================
    path("dashboard/orders/<uuid:order_id>/pay/",
         pay_order, name="dashboard_order_pay"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/",
         pay_order, name="pay_order"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/success/",
         payment_success, name="payment_success"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/receipt/",
         print_receipt, name="print_receipt"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/create-payment-intent/",
         create_payment_intent, name="create_payment_intent"),

    # ========================================================
    # CATEGORY MANAGEMENT
    # ========================================================
    path("dashboard/categories/",
         CategoryListView.as_view(), name="category_list"),

    path("dashboard/categories/add/",
         CategoryCreateView.as_view(), name="category_add"),

    path("dashboard/categories/<uuid:pk>/edit/",
         CategoryUpdateView.as_view(), name="category_edit"),

    path("dashboard/categories/<uuid:pk>/delete/",
         CategoryDeleteView.as_view(), name="category_delete"),

    path("dashboard/categories/reorder/",
         UpdateCategoryOrderView.as_view(), name="update_category_order"),

    # ========================================================
    # PRODUCT MANAGEMENT
    # ========================================================
    path("dashboard/products/",
     ProductListView.as_view(), name="manage_products"),

     path("dashboard/products/",
     manage_products, name="manage_products"),

    path("dashboard/products/add/",
         ProductCreateView.as_view(), name="product_add"),
    
   path(
        "dashboard/products/",
        ProductListView.as_view(),
        name="product_list"
    ),
    path(
        "dashboard/products/<int:pk>/edit/",
        ProductUpdateView.as_view(),
        name="edit_product"
    ),
    path(
        "dashboard/products/<int:pk>/delete/",
        ProductDeleteView.as_view(),
        name="delete_product"
    ),

    # ========================================================
    # STAFF & SHIFTS
    # ========================================================
    path("staff/", staff_list, name="staff_list"),
    path("staff/create/", create_staff, name="create_staff"),

    path("shift/start/", start_shift, name="start_shift"),
    path("shift/end/", end_shift, name="close_shift"),

    path("shift/<int:shift_id>/z-report/",
         shift_z_report_print, name="shift_z_report_print"),

    # ========================================================
    # DISPLAYS
    # ========================================================
    path("kitchen/", kitchen_display, name="kitchen_display"),

    path("display/<uuid:token>/<int:table_id>/",
         CustomerDisplayView.as_view(), name="customer_display"),

    path("display/<uuid:token>/<int:table_id>/refresh/",
         customer_display_refresh, name="customer_display_refresh"),

    path("display/<uuid:token>/",
         public_display, name="public_display"),

    path("customer/",
         customer_display_shortcut, name="customer_display_shortcut"),

    # ========================================================
    # BADGES
    # ========================================================
    path("badges/orders/",
         orders_badge_count, name="orders_badge_count"),

    path("badges/kitchen/",
         kitchen_queue_count, name="kitchen_queue_count"),

    # ========================================================
    # SETTINGS
    # ========================================================
    path("settings/",
         SettingsView.as_view(), name="settings"),

    # ========================================================
    # REPORTS & ANALYTICS
    # ========================================================
    path("reports/daily/",
         DailyReportsListView.as_view(), name="daily_reports"),

    path("reports/daily/csv/",
         DailyReportCSV, name="daily_report_csv"),

    path("reports/daily/excel/",
         DailyReportExcel, name="daily_report_excel"),

    path("reports/summary/",
         PeriodSummaryView.as_view(), name="period_summary"),

    path("analytics/",
         AnalyticsView.as_view(), name="analytics"),

    path("api/analytics/",
         AnalyticsAPIView.as_view(), name="analytics_api"),

    # ========================================================
    # API ROUTER
    # ========================================================
    path("api/v1/", include(router.urls)),
]