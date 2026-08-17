from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import *
from .views_webhooks import stripe_webhook
from .views import register_restaurant_api, reports_summary, settings_api, staff_list_create_api, staff_detail_api 
from .views import (
    CustomerViewSet, PaymentViewSet,
    InventoryViewSet, DiscountViewSet, MarkOrderPaidView,
)
app_name = "core"

# ============================================================
# DRF ROUTER
# ============================================================

router = DefaultRouter()

# Core API
router.register(r"tables", TableViewSet, basename="table")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"order-items", OrderItemViewSet, basename="orderitem")
router.register(r"payments", PaymentViewSet, basename="payment")

# Manager API (SaaS Admin)
router.register(r"manager/categories", ManagerCategoryViewSet, basename="manager-categories")
router.register(r"manager/products", ManagerProductViewSet, basename="manager-products")
router.register(r"manager/menus", ManagerMenuViewSet, basename="manager-menus")
router.register(r"manager/modifier-groups", ManagerModifierGroupViewSet, basename="manager-modifier-groups")
router.register(r"manager/modifier-options", ManagerModifierOptionViewSet, basename="manager-modifier-options")
router.register(r"manager/customers", CustomerViewSet, basename="manager-customers")
router.register(r"manager/inventory", InventoryViewSet, basename="manager-inventory")
router.register(r"manager/discounts", DiscountViewSet, basename="manager-discounts")
# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

    # ========================================================
    # HOME PAGE
    # ========================================================
    path("", api_home, name="home"),
    
    path("register/", register_restaurant, name="register"),

    path(
        "api/v1/restaurants/register/",
        register_restaurant_api,
        name="register_restaurant_api",
    ),
    # ========================================================
    # JWT AUTH
    # ========================================================
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ========================================================
    # USER INFO
    # ========================================================
    path("api/me/", MeView.as_view(), name="me"),
    
    # ========================================================
    # SUBSCRIPTION
    # ========================================================
    path("api/v1/subscription/", subscription_detail),
    path("api/subscription/create-checkout/", create_checkout_session),

    # ========================================================
    # STRIPE WEBHOOK
    # ========================================================
    path("api/stripe/webhook/", stripe_webhook),

    # ========================================================
    # PUBLIC MENU API
    # ========================================================
    path(
        "api/v1/public/<uuid:restaurant_id>/menus/",
        PublicMenuViewSet.as_view({"get": "list"}),
        name="public-menus",
    ),

    path(
        "api/v1/public/<uuid:restaurant_id>/menus/<uuid:pk>/",
        PublicMenuViewSet.as_view({"get": "retrieve"}),
        name="public-menu-detail",
    ),
    
    path("api/v1/reports/", reports_summary, name="reports-summary"),
    # ========================================================
    # MAIN API ROUTER
    # ========================================================
    path("api/v1/", include(router.urls)),
    
    path("api/v1/settings/", settings_api, name="settings-api"),
    path("api/v1/staff/", staff_list_create_api, name="staff-list-create-api"),
    path("api/v1/staff/<int:pk>/", staff_detail_api, name="staff-detail-api"),
    path("api/v1/orders/<int:order_id>/mark-paid/", MarkOrderPaidView.as_view(), name="mark-order-paid"),
]