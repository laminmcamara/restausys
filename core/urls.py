from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


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
    LoginView,
    LogoutView,
    SettingsView,
    ManagerDashboardView,
    RestaurantDashboardView,
    OrderListView,
    PosOrderScreenTakeoutView,
    KitchenDisplayView,
    CustomerDisplayView,
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

    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

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
    path("customer/", CustomerDisplayView.as_view(), name="customer_display"),

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

    # ======================
    # REPORTS
    # ======================

    path("reports/daily/", DailyReportsListView.as_view(), name="daily_reports"),
    path("reports/daily/csv/", DailyReportCSV, name="daily_report_csv"),
    path("reports/daily/excel/", DailyReportExcel, name="daily_report_excel"),
    path("reports/summary/", PeriodSummaryView.as_view(), name="period_summary"),

    # ======================
    # SETTINGS
    # ======================

    path("settings/", SettingsView.as_view(), name="settings"),

    # ======================
    # DASHBOARDS
    # ======================

    path("manager-dashboard/", ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("restaurant-dashboard/", RestaurantDashboardView.as_view(), name="restaurant_dashboard"),
    
    
]