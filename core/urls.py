from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views

from .views import (
    # Main / Routing
    IndexView,
    ManagerDashboardView,
    RestaurantDashboardView,

    # POS
    PosDashboardView,
    pos_view,
    ProcessPosOrderView,
    PosDataView,
    ProductCreateView,
    ProductCreateView,
    DashboardRouterView,

    # Tables
    TableViewSet,
    TableOverviewView,
    open_table_order,

    # Categories
    CategoryViewSet,
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryDeleteView,
    UpdateCategoryOrderView,

    # Products
    ProductViewSet,
    ManagerProductViewSet,
    manage_products,
    
    # Orders
    OrderViewSet,
    OrderItemViewSet,
    OrderListView,
    OrderDetailView,
    OrderSuccessView,
    create_order,
    add_to_order,
    update_quantity,
    remove_item,
    order_status_api,
    table_order_status,

    # Payments
    PaymentViewSet,
    create_payment_intent,
    pay_order,
    payment_success,
    print_receipt,

    # Reports & Analytics
    DailyReportsListView,
    DailyReportCSV,
    DailyReportExcel,
    PeriodSummaryView,
    AnalyticsAPIView,
    AnalyticsView,

    # Displays
    KitchenDisplayView,
    CustomerDisplayView,
    customer_display_refresh,
    customer_display_shortcut,
    public_display,
    order_receipt,

    # Tables / QR
    PrintQRView,
    regenerate_qr,
    public_table_menu,

    # Badges
    orders_badge_count,
    kitchen_queue_count,

    # Staff
    start_shift,
    end_shift,
    create_staff,
    staff_list,

    # Settings
    SettingsView,

    # Auth
    CustomLoginView,

    # Subscription
    register_restaurant,
    subscription_expired,
    
    dashboard_table_open,
    dashboard_table_close,
)

app_name = "core"

# ============================================================
# DRF ROUTER
# ============================================================

router = DefaultRouter()
router.register(r"tables", TableViewSet, basename="table")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(
    r"manager/products",
    ManagerProductViewSet,
    basename="manager-products"
)
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
             template_name="core/registration/password_reset.html"
         ),
         name="password_reset"),

    path("password-reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="core/registration/password_reset_done.html"
         ),
         name="password_reset_done"),

    path("reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="core/registration/password_reset_confirm.html"
         ),
         name="password_reset_confirm"),

    path("reset/done/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="core/registration/password_reset_complete.html"
         ),
         name="password_reset_complete"),

    # JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ========================================================
    # DASHBOARDS
    # ========================================================

    path("manager-dashboard/",
         ManagerDashboardView.as_view(),
         name="manager_dashboard"),
    
    path("register/", register_restaurant, name="register"),

    path("restaurant-dashboard/",
         RestaurantDashboardView.as_view(),
         name="restaurant_dashboard"),

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
    path("api/pos/process-order/",
         ProcessPosOrderView.as_view(),
         name="process_pos_order"),

    # ========================================================
    # TABLES
    # ========================================================

    path("pos/tables/", TableOverviewView.as_view(), name="table_overview"),
    path("dashboard/tables/<int:table_id>/open/",
         open_table_order,
         name="dashboard_table_open"),

    path("tables/<int:pk>/print/",
         PrintQRView.as_view(),
         name="print_qr"),
    path("tables/<int:pk>/regenerate/",
         regenerate_qr,
         name="regenerate_qr"),

    path("table/<uuid:token>/",
         public_table_menu,
         name="public_table_menu"),

    # ========================================================
    # ORDERS
    # ========================================================

    path("orders/", OrderListView.as_view(), name="orders"),
    path("orders/<uuid:pk>/",
         OrderDetailView.as_view(),
         name="order_detail"),

    path("orders/new/", create_order, name="create_order"),
    path("order-success/<int:order_id>/",
         OrderSuccessView.as_view(),
         name="order_success"),

    path("order/<uuid:order_id>/status/",
         table_order_status,
         name="table_order_status"),

    path("api/order/<uuid:order_id>/status/",
         order_status_api,
         name="order_status_api"),

    # ========================================================
    # PAYMENTS
    # ========================================================

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/",
         pay_order,
         name="pay_order"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/success/",
         payment_success,
         name="payment_success"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/receipt/",
         print_receipt,
         name="print_receipt"),

    path("r/<slug:restaurant_slug>/order/<uuid:order_id>/create-payment-intent/",
         create_payment_intent,
         name="create_payment_intent"),

    # ========================================================
    # REPORTS & ANALYTICS
    # ========================================================

    path("reports/daily/", DailyReportsListView.as_view(), name="daily_reports"),
    path("reports/daily/csv/", DailyReportCSV, name="daily_report_csv"),
    path("reports/daily/excel/", DailyReportExcel, name="daily_report_excel"),
    path("reports/summary/", PeriodSummaryView.as_view(), name="period_summary"),

    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("api/analytics/", AnalyticsAPIView.as_view(), name="analytics_api"),

# ==============================
    # ✅ CATEGORY MANAGEMENT
    # ==============================

    path(
        "dashboard/categories/",
        CategoryListView.as_view(),
        name="category_list"
    ),

    path(
        "dashboard/categories/add/",
        CategoryCreateView.as_view(),
        name="category_add"
    ),

    path(
        "dashboard/categories/<uuid:pk>/edit/",
        CategoryUpdateView.as_view(),
        name="category_edit"
    ),

    path(
        "dashboard/categories/<uuid:pk>/delete/",
        CategoryDeleteView.as_view(),
        name="category_delete"
    ),

    path(
        "dashboard/categories/reorder/",
        UpdateCategoryOrderView.as_view(),
        name="update_category_order"
    ),

    # ========================================================
    # PRODUCTS
    # ========================================================

    path("dashboard/products/",
         manage_products,
         name="manage_products"),

    # ========================================================
    # STAFF
    # ========================================================

    path("start-shift/", start_shift, name="start_shift"),
    path("end-shift/", end_shift, name="end_shift"),
    path("staff/create/", create_staff, name="create_staff"),
    path("staff/", staff_list, name="staff_list"),

    # ========================================================
    # DISPLAYS
    # ========================================================

    path("kitchen/", KitchenDisplayView.as_view(), name="kitchen_display"),

    path("display/<uuid:token>/<int:table_id>/",
         CustomerDisplayView.as_view(),
         name="customer_display"),

    path("display/<uuid:token>/<int:table_id>/refresh/",
         customer_display_refresh,
         name="customer_display_refresh"),

    path("customer/",
         customer_display_shortcut,
         name="customer_display_shortcut"),

    path("orders/<uuid:pk>/receipt/",
         order_receipt,
         name="order-receipt"),

    path("display/<uuid:token>/",
         public_display,
         name="public_display"),

    # ========================================================
    # BADGES
    # ========================================================

    path("badges/orders/", orders_badge_count, name="orders_badge_count"),
    path("badges/kitchen/", kitchen_queue_count, name="kitchen_queue_count"),

    # ========================================================
    # SETTINGS
    # ========================================================

    path("settings/", SettingsView.as_view(), name="settings"),

    # ========================================================
    # SUBSCRIPTION (Middleware Redirect Targets)
    # ========================================================

    

    path("subscription-expired/",
         subscription_expired,
         name="subscription_expired"),

    # ========================================================
    # API ROUTER
    # ========================================================

    path("api/v1/", include(router.urls)),
    
    path("dashboard/", DashboardRouterView.as_view(), name="dashboard"),
    
    path("dashboard/products/add/",
     ProductCreateView.as_view(),
     name="product_add"),
    
    path(
        "dashboard/tables/<int:table_id>/open/",
        dashboard_table_open,
        name="dashboard_table_open"
    ),

    path(
        "dashboard/sessions/<int:session_id>/close/",
        dashboard_table_close,
        name="dashboard_table_close"
    ),

]