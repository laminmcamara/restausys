from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views




from .views import (
    IndexView,
    PosDashboardView,
    TableViewSet,
    TableOverviewView,
    CategoryViewSet,
    ProductViewSet,
    OrderViewSet,
    OrderItemViewSet,
    PaymentViewSet,
    PosDataView,
    PosSaveOrderView,
    DailyReportsListView,
    DailyReportCSV,
    DailyReportExcel,
    PeriodSummaryView,
    OrderSuccessView,
    SettingsView,
    ManagerDashboardView,
    RestaurantDashboardView,
    OrderListView,
    PosOrderScreenTakeoutView,
    KitchenDisplayView,
    CustomerDisplayView,
    order_receipt,
    customer_display_refresh,
    customer_display_shortcut,
    CustomLoginView,
    PrintQRView,
    regenerate_qr,
    create_takeout_order,
    orders_badge_count,
    kitchen_queue_count,
    start_shift,
    end_shift,
    create_staff,
    staff_list,
    manage_products,
    public_table_menu,
    pay_order,
    order_status_api,
    table_order_status,
    AnalyticsAPIView,
    AnalyticsView
)

app_name = "core"

# ============================================================
# DRF ROUTER
# ============================================================

router = DefaultRouter()
router.register(r"tables", TableViewSet, basename="table")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"order-items", OrderItemViewSet, basename="orderitem")
router.register(r"payments", PaymentViewSet, basename="payment")

# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

    # ======================
    # MAIN
    # ======================

    path("", IndexView.as_view(), name="home"),

    # ======================
    # AUTH
    # ======================

    # path("login/", CustomLoginView.as_view(), name="login"),
    # path("logout/", CustomLogoutView.as_view(), name="logout"),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='core:login'), name='logout'),
    

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="core/registration/password_reset.html"
        ),
        name="password_reset"
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="core/registration/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="core/registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="core/registration/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),

    
    
    # JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ======================
    # POS UI
    # ======================

    path("pos/", PosDashboardView.as_view(), name="pos_dashboard"),
    path("pos/screen/", PosOrderScreenTakeoutView.as_view(), name="pos_screen"),
    path("pos/tables/", TableOverviewView.as_view(), name="table_overview"),

    # ======================
    # DISPLAYS
    # ======================

    path("kitchen/", KitchenDisplayView.as_view(), name="kitchen_display"),
    
    path(
    "display/<uuid:token>/<int:table_id>/",
    CustomerDisplayView.as_view(),
    name="customer_display",
),

    path(
    "display/<uuid:token>/<int:table_id>/refresh/",
    customer_display_refresh,
    name="customer_display_refresh",
),
    
    path("customer/", customer_display_shortcut, name="customer_display_shortcut"),
    
    path("orders/<int:pk>/receipt/", order_receipt, name="order-receipt"),
    # ======================
    # API (Versioned)
    # ======================

    path("api/v1/pos-data/", PosDataView.as_view(), name="pos_data"),
    path("api/v1/pos-save-order/", PosSaveOrderView.as_view(), name="pos_save_order"),

    path("api/v1/", include(router.urls)),
    
    # ======================
    # ORDERS
    # ======================

    path("orders/", OrderListView.as_view(), name="orders"),
    path("order-success/<int:order_id>/", OrderSuccessView.as_view(), name="order_success"),
    path("order/<uuid:order_id>/status/", table_order_status, name="table_order_status"),
    path("order/<uuid:order_id>/pay/", pay_order, name="pay_order"),
    path("api/order/<uuid:order_id>/status/", order_status_api, name="order_status_api"),
    # ======================
    # REPORTS
    # ======================

    path("reports/daily/", DailyReportsListView.as_view(), name="daily_reports"),
    path("reports/daily/csv/", DailyReportCSV, name="daily_report_csv"),
    path("reports/daily/excel/", DailyReportExcel, name="daily_report_excel"),
    path("reports/summary/", PeriodSummaryView.as_view(), name="period_summary"),
    path("api/analytics/", AnalyticsAPIView.as_view(), name="analytics_api"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    
    # ======================
    # SETTINGS
    # ======================

    path("settings/", SettingsView.as_view(), name="settings"),

    # ======================
    # DASHBOARDS
    # ======================

    path("manager-dashboard/", ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("restaurant-dashboard/", RestaurantDashboardView.as_view(), name="restaurant_dashboard"),
    
    path("tables/<int:pk>/print/", PrintQRView.as_view(), name="print-qr"),
    path("tables/<int:pk>/regenerate/", regenerate_qr, name="regenerate-qr"),
    path("pos/create-takeout/", create_takeout_order, name="create_takeout_order"),
    path("table/<uuid:token>/", public_table_menu, name="public_table_menu"),
    
    
    path("badges/orders/", orders_badge_count, name="orders_badge_count"),
    path("badges/kitchen/", kitchen_queue_count, name="kitchen_queue_count"),
    
    path("start-shift/", start_shift, name="start_shift"),
    path("end-shift/", end_shift, name="end_shift"),
    
    path("staff/create/", create_staff, name="create_staff"),
    path("staff/", staff_list, name="staff_list"),
    
    path("dashboard/products/", manage_products, name="manage_products"),
]