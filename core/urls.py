# core/urls.py

from django.urls import include, path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    AnalyticsAPIView,
    CategoryViewSet,
    ChangePasswordView,
    CustomerViewSet,
    DiscountViewSet,
    InventoryViewSet,
    ManagerCategoryViewSet,
    ManagerMenuViewSet,
    ManagerModifierGroupViewSet,
    ManagerModifierOptionViewSet,
    ManagerProductViewSet,
    MeView,
    ModifierOptionViewSet,
    OrderItemViewSet,
    OrderViewSet,
    PaymentMethodViewSet,
    PaymentSummaryAPIView,
    PaymentViewSet,
    PlaceOrderAPIView,
    PosDashboardAPIView,
    ProductViewSet,
    PublicMenuViewSet,
    PublicTableMenuAPIView,
    PublicTableOrderAPIView,
    RestaurantDashboardView,
    SessionViewSet,
    TableViewSet,
    WebhookConfigAPIView,
    api_home,
    create_checkout_session,
    order_status_api,
    regenerate_api_key,
    register_restaurant,
    register_restaurant_api,
    reports_summary,
    settings_api,
    staff_detail_api,
    staff_list_create_api,
    subscription_detail,
)


app_name = "core"


router = DefaultRouter()


# ---------------------------------------------------------------------------
# Main resources
# ---------------------------------------------------------------------------

router.register(
    r"tables",
    TableViewSet,
    basename="table",
)

router.register(
    r"categories",
    CategoryViewSet,
    basename="category",
)

router.register(
    r"products",
    ProductViewSet,
    basename="product",
)

router.register(
    r"orders",
    OrderViewSet,
    basename="order",
)

router.register(
    r"order-items",
    OrderItemViewSet,
    basename="order-item",
)

router.register(
    r"sessions",
    SessionViewSet,
    basename="session",
)

router.register(
    r"payment-methods",
    PaymentMethodViewSet,
    basename="payment-method",
)

router.register(
    r"payments",
    PaymentViewSet,
    basename="payment",
)


# ---------------------------------------------------------------------------
# Manager resources
# ---------------------------------------------------------------------------

router.register(
    r"manager/categories",
    ManagerCategoryViewSet,
    basename="manager-category",
)

router.register(
    r"manager/menu",
    ManagerMenuViewSet,
    basename="manager-menu",
)

router.register(
    r"manager/products",
    ManagerProductViewSet,
    basename="manager-product",
)

router.register(
    r"manager/modifiers",
    ManagerModifierGroupViewSet,
    basename="manager-modifier",
)

router.register(
    r"manager/modifier-groups",
    ManagerModifierGroupViewSet,
    basename="manager-modifier-group",
)

router.register(
    r"manager/modifier-options",
    ManagerModifierOptionViewSet,
    basename="manager-modifier-option",
)

router.register(
    r"manager/customers",
    CustomerViewSet,
    basename="manager-customer",
)

router.register(
    r"manager/inventory",
    InventoryViewSet,
    basename="manager-inventory",
)

router.register(
    r"manager/discounts",
    DiscountViewSet,
    basename="manager-discount",
)


# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------

urlpatterns = [
    # Dashboard and reports
    path(
        "dashboard/",
        RestaurantDashboardView.as_view(),
        name="restaurant-dashboard",
    ),
    path(
        "reports/",
        AnalyticsAPIView.as_view(),
        name="reports",
    ),

    # Payments and orders
    path(
        "payments/summary/",
        PaymentSummaryAPIView.as_view(),
        name="payment-summary",
    ),
    path(
        "orders/place/",
        PlaceOrderAPIView.as_view(),
        name="place-order",
    ),

    # Restaurant registration
    path(
        "restaurants/register/",
        register_restaurant_api,
        name="register-restaurant-api",
    ),

    # Restaurant settings and profile
    path(
        "settings/",
        settings_api,
        name="settings-api",
    ),
    path(
        "me/",
        MeView.as_view(),
        name="me",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    
    path(
    "pos/dashboard/",
    PosDashboardAPIView.as_view(),
    name="pos-dashboard",
    ),

    # Staff management
    path(
        "manager/staff/",
        staff_list_create_api,
        name="staff-list-create-api",
    ),
    path(
        "manager/staff/<int:pk>/",
        staff_detail_api,
        name="staff-detail-api",
    ),

    # Developer configuration
    path(
        "developer/webhook-config/",
        WebhookConfigAPIView.as_view(),
        name="api-webhook-config",
    ),
    path(
        "developer/regenerate-key/",
        regenerate_api_key,
        name="api-regenerate-key",
    ),

    # Subscription and billing
    path(
        "subscription/",
        subscription_detail,
        name="subscription-detail",
    ),
    path(
        "subscription/create-checkout/",
        create_checkout_session,
        name="create-checkout-session",
    ),

    # Public menus
    path(
        "public/<uuid:restaurant_id>/menus/",
        PublicMenuViewSet.as_view(
            {
                "get": "list",
            }
        ),
        name="public-menus",
    ),
    path(
        "public/<uuid:restaurant_id>/menus/<uuid:pk>/",
        PublicMenuViewSet.as_view(
            {
                "get": "retrieve",
            }
        ),
        name="public-menu-detail",
    ),

    # Public table ordering
    path(
        "public/tables/<uuid:token>/menu/",
        PublicTableMenuAPIView.as_view(),
        name="public-table-menu-api",
    ),
    path(
        "public/tables/<uuid:token>/orders/",
        PublicTableOrderAPIView.as_view(),
        name="public-table-order-api",
    ),

    # JWT authentication
    path(
        "token/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),

    # Router-generated API routes
    path(
        "",
        include(router.urls),
    ),

    # Legacy or general endpoints
    path(
        "orders/<str:token>/<int:order_id>/status/",
        order_status_api,
        name="order-status-api",
    ),
    path(
        "home/",
        api_home,
        name="api-home",
    ),
    path(
        "register/",
        register_restaurant,
        name="register",
    ),
]