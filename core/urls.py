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
    MeView, me_api,
    subscription_detail,
    create_checkout_session,
   
)

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

# Manager API
router.register(r"manager/categories", ManagerCategoryViewSet, basename="manager-categories")
router.register(r"manager/products", ManagerProductViewSet, basename="manager-products")
router.register(r"manager/menus", ManagerMenuViewSet, basename="manager-menus")
router.register(r"manager/modifier-groups", ManagerModifierGroupViewSet, basename="manager-modifier-groups")
router.register(r"manager/modifier-options", ManagerModifierOptionViewSet, basename="manager-modifier-options")

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
    path("auth/me/", MeView.as_view(), name="me"),

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
    path("manager-dashboard/", ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("register/", register_restaurant, name="register"),
    path("subscription-expired/", subscription_expired, name="subscription_expired"),
    path("dashboard/", RestaurantDashboardView.as_view(), name="dashboard"),

    # ========================================================
    # POS
    # ========================================================
    path("pos/", PosDashboardView.as_view(), name="pos_dashboard"),
    path("pos/<uuid:order_id>/", pos_view, name="pos"),

    path("pos/<uuid:order_id>/add/<uuid:variant_id>/", add_to_order, name="add_to_order"),
    path("pos/<uuid:order_id>/update/<int:item_id>/", update_quantity, name="update_quantity"),
    path("pos/<uuid:order_id>/remove/<int:item_id>/", remove_item, name="remove_item"),

    path("api/v1/pos-data/", PosDataView.as_view(), name="pos_data"),

    # ========================================================
    # TABLE PUBLIC ORDERING
    # ========================================================
    path("table/<uuid:token>/", public_table_menu, name="public_table_menu"),
    path("table/<uuid:token>/place-order/", place_table_order, name="place-table-order"),
    path("table/<uuid:token>/checkout/", table_checkout, name="table-checkout"),

    # ========================================================
    # ORDERS
    # ========================================================
    path("orders/", OrderListView.as_view(), name="orders"),
    path("orders/<uuid:pk>/complete/", complete_order, name="complete_order"),
    path("orders/<uuid:pk>/send-to-kitchen/", send_to_kitchen, name="send_to_kitchen"),
    path("orders/<uuid:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("orders/<uuid:pk>/receipt/", order_receipt, name="order-receipt"),

    # ========================================================
    # PAYMENTS
    # ========================================================
    path("dashboard/orders/<uuid:order_id>/pay/", pay_order, name="dashboard_order_pay"),

    # ========================================================
    # PUBLIC MENU API (READ-ONLY)
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
    # API ROUTER
    # ========================================================
    path("api/v1/", include(router.urls)),
    

    path("api/me/", me_api, name="me_api"),
    
    path("api/subscription/", subscription_detail),
    path("api/subscription/create-checkout/", create_checkout_session),
    path("api/stripe/webhook/", stripe_webhook),
]