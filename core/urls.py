from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import *
from .views import (register_restaurant_api, reports_summary, settings_api, staff_list_create_api, staff_detail_api, CustomerViewSet,
    InventoryViewSet, DiscountViewSet, MarkOrderPaidView, ChangePasswordView, PlaceOrderAPIView, WebhookConfigAPIView, PaymentSummaryAPIView, regenerate_api_key, InventoryViewSet, CategoryViewSet, ProductViewSet,  ModifierOptionViewSet, ManagerCategoryViewSet, ManagerProductViewSet, ManagerMenuViewSet, ManagerModifierGroupViewSet, ManagerModifierOptionViewSet, PublicMenuViewSet
)

app_name = "core"

# ============================================================
# DRF ROUTER (Register everything here ONCE)
# ============================================================
router = DefaultRouter()

# Core/POS API
router.register(r"tables", TableViewSet, basename="table")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"order-items", OrderItemViewSet, basename="orderitem")

# Manager API (The ones your Management pages use)
router.register(r"manager/categories", ManagerCategoryViewSet, basename="manager-categories")
router.register(r"manager/products", ManagerProductViewSet, basename="manager-products")
router.register(r"manager/modifiers", ManagerModifierGroupViewSet, basename="manager-modifiers")
router.register(r"manager/modifier-groups", ManagerModifierGroupViewSet, basename="manager-modifier-groups")
router.register(r"manager/modifier-options", ManagerModifierOptionViewSet, basename="manager-modifier-options")
router.register(r"manager/customers", CustomerViewSet, basename="customers")
router.register(r"manager/inventory", InventoryViewSet, basename="inventory")
router.register(r"manager/discounts", DiscountViewSet, basename="manager-discounts")

# ============================================================
# URL PATTERNS
# ============================================================
urlpatterns = [
    # 1. Include all router URLs under api/v1/
    path('api/v1/', include(router.urls)),

    # 2. Specific API Views
    path('api/v1/orders/place/', PlaceOrderAPIView.as_view(), name='place-order'),
    path("api/v1/restaurants/register/", register_restaurant_api, name="register_restaurant_api"),
    path("api/v1/reports/", reports_summary, name="reports-summary"),
    path("api/v1/settings/", settings_api, name="settings-api"),
    path("api/v1/manager/staff/", staff_list_create_api, name="staff-list-create-api"),
    path("api/v1/manager/staff/<int:pk>/", staff_detail_api, name="staff-detail-api"),
    path("api/v1/orders/<int:order_id>/mark-paid/", MarkOrderPaidView.as_view(), name="mark-order-paid"),
    
    # 3. Auth & User
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", MeView.as_view(), name="me"),
    path("api/change-password/", ChangePasswordView.as_view(), name="change-password"),
    
    # 4. Subscription & Developer
    path("api/v1/subscription/", subscription_detail),
    path("api/v1/subscription/create-checkout/", create_checkout_session),
    path('api/v1/developer/webhook-config/', WebhookConfigAPIView.as_view(), name='api-webhook-config'),
    path('api/v1/developer/regenerate-key/', regenerate_api_key, name='api-regenerate-key'),
    path('api/v1/payments/summary/', PaymentSummaryAPIView.as_view(), name='payment-summary'),

    # 5. Public Menu
    path("api/v1/public/<uuid:restaurant_id>/menus/", PublicMenuViewSet.as_view({"get": "list"}), name="public-menus"),
    path("api/v1/public/<uuid:restaurant_id>/menus/<uuid:pk>/", PublicMenuViewSet.as_view({"get": "retrieve"}), name="public-menu-detail"),

    # 6. Home/Web Views
    path("", api_home, name="home"),
    path("register/", register_restaurant, name="register"),
]