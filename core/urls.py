from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import *
from .views_webhooks import stripe_webhook

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
router.register(r"manager/menu", ManagerProductViewSet, basename="manager-products")
router.register(r"manager/menus", ManagerMenuViewSet, basename="manager-menus")
router.register(r"manager/modifier-groups", ManagerModifierGroupViewSet, basename="manager-modifier-groups")
router.register(r"manager/modifier-options", ManagerModifierOptionViewSet, basename="manager-modifier-options")

# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

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
    path("api/subscription/", subscription_detail),
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

    # ========================================================
    # MAIN API ROUTER
    # ========================================================
    path("api/v1/", include(router.urls)),
]