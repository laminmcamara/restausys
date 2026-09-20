from django.urls import include, path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    ChangePasswordView,
    CategoryViewSet,
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
    ProductViewSet,
    PublicMenuViewSet,
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
    PublicTableMenuAPIView,
    PublicTableOrderAPIView,
)
app_name = "core"


router = DefaultRouter()

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
    basename="orderitem",
)

router.register(
    r"sessions",
    SessionViewSet,
    basename="session",
)

router.register(
    r"payment-methods",
    PaymentMethodViewSet,
    basename="paymentmethod",
)

router.register(
    r"payments",
    PaymentViewSet,
    basename="payment",
)

router.register(
    r"manager/categories",
    ManagerCategoryViewSet,
    basename="manager-categories",
)

router.register(
    r"manager/products",
    ManagerProductViewSet,
    basename="manager-products",
)

router.register(
    r"manager/modifiers",
    ManagerModifierGroupViewSet,
    basename="manager-modifiers",
)

router.register(
    r"manager/modifier-groups",
    ManagerModifierGroupViewSet,
    basename="manager-modifier-groups",
)

router.register(
    r"manager/modifier-options",
    ManagerModifierOptionViewSet,
    basename="manager-modifier-options",
)

router.register(
    r"manager/customers",
    CustomerViewSet,
    basename="customers",
)

router.register(
    r"manager/inventory",
    InventoryViewSet,
    basename="inventory",
)

router.register(
    r"manager/discounts",
    DiscountViewSet,
    basename="manager-discounts",
)


urlpatterns = [
    # Put explicit endpoints before the router.
    path(
        "api/v1/payments/summary/",
        PaymentSummaryAPIView.as_view(),
        name="payment-summary",
    ),

    path(
        "api/v1/orders/place/",
        PlaceOrderAPIView.as_view(),
        name="place-order",
    ),

    path(
        "api/v1/restaurants/register/",
        register_restaurant_api,
        name="register-restaurant-api",
    ),

    path(
        "api/v1/reports/",
        reports_summary,
        name="reports-summary",
    ),

    path(
        "api/v1/settings/",
        settings_api,
        name="settings-api",
    ),

    path(
        "api/v1/manager/staff/",
        staff_list_create_api,
        name="staff-list-create-api",
    ),

    path(
        "api/v1/manager/staff/<int:pk>/",
        staff_detail_api,
        name="staff-detail-api",
    ),

    path(
        "api/v1/developer/webhook-config/",
        WebhookConfigAPIView.as_view(),
        name="api-webhook-config",
    ),

    path(
        "api/v1/developer/regenerate-key/",
        regenerate_api_key,
        name="api-regenerate-key",
    ),

    path(
        "api/v1/subscription/",
        subscription_detail,
        name="subscription-detail",
    ),

    path(
        "api/v1/subscription/create-checkout/",
        create_checkout_session,
        name="create-checkout-session",
    ),

    path(
        "api/v1/public/<uuid:restaurant_id>/menus/",
        PublicMenuViewSet.as_view(
            {
                "get": "list",
            }
        ),
        name="public-menus",
    ),

    path(
        "api/v1/public/<uuid:restaurant_id>/menus/<uuid:pk>/",
        PublicMenuViewSet.as_view(
            {
                "get": "retrieve",
            }
        ),
        name="public-menu-detail",
    ),
    
    path(
        "api/v1/public/tables/<uuid:token>/menu/",
        PublicTableMenuAPIView.as_view(),
        name="public-table-menu-api",
    ),

    path(
        "api/v1/public/tables/<uuid:token>/orders/",
        PublicTableOrderAPIView.as_view(),
        name="public-table-order-api",
    ),

    # Router routes come after explicit routes.
    path(
        "api/v1/",
        include(router.urls),
    ),

    # Authentication.
    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),

    path(
        "api/me/",
        MeView.as_view(),
        name="me",
    ),

    path(
        "api/change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),

    path(
        "orders/<str:token>/<int:order_id>/status/",
        order_status_api,
        name="order-status-api",
    ),

    path(
        "",
        api_home,
        name="home",
    ),

    path(
        "register/",
        register_restaurant,
        name="register",
    ),
]