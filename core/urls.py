from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, pos_views  # ✅ Import your additional POS-related views

# ==============================================================================
# DRF ROUTER
# ==============================================================================
router = DefaultRouter()
router.register(r'users', views.CustomUserViewSet, basename='user')
# router.register(r'orders', views.OrderViewSet, basename='order')
# router.register(r'menu-items', views.MenuItemViewSet, basename='menu-item')

# ==============================================================================
# URL PATTERNS
# ==============================================================================
app_name = 'core'

urlpatterns = [
    # --------------------------------------------------------------------------
    # AUTH & REGISTRATION
    # --------------------------------------------------------------------------
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),

    # --------------------------------------------------------------------------
    # DASHBOARDS / HOME
    # --------------------------------------------------------------------------
    path('', pos_views.pos_dashboard, name='pos_dashboard'),  # new homepage
    path('home/', views.home, name='home'),                   # optional old home
    path('dashboard/', views.UserDashboardView.as_view(), name='user-dashboard'),
    path('dashboard/manager/', views.ManagerDashboardView.as_view(), name='manager-dashboard'),
    path("register/", views.RegisterView.as_view(), name="register"),

    # --------------------------------------------------------------------------
    # STAFF & SHIFTS
    # --------------------------------------------------------------------------
    path('clock/', views.ClockInOutView.as_view(), name='clock-in-out'),
    path('shifts/', views.ShiftListView.as_view(), name='shift-list'),
    path('shifts/create/', views.ShiftCreateView.as_view(), name='shift-create'),
    path('shifts/<int:pk>/update/', views.ShiftUpdateView.as_view(), name='shift-update'),
    path('shifts/<int:pk>/delete/', views.ShiftDeleteView.as_view(), name='shift-delete'),

    # --------------------------------------------------------------------------
    # MENU MANAGEMENT
    # --------------------------------------------------------------------------
    path('menu/', views.MenuItemListView.as_view(), name='menu-list'),
    path('menu/create/', views.MenuItemCreateView.as_view(), name='menu-create'),
    path('menu/<int:pk>/update/', views.MenuItemUpdateView.as_view(), name='menu-update'),
    path('menu/<int:pk>/delete/', views.MenuItemDeleteView.as_view(), name='menu-delete'),

    # --------------------------------------------------------------------------
    # ORDERS & PAYMENTS
    # --------------------------------------------------------------------------
    path('order/table/<uuid:token>/', views.TableOrderView.as_view(), name='table-order'),
    path('order/<uuid:order_id>/success/', views.OrderSuccessView.as_view(), name='order-success'),
    path('order/<uuid:order_id>/pay/', views.OrderPaymentView.as_view(), name='order-pay'),

    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<uuid:pk>/status/', views.order_status_json, name='order-status-json'),
    path('orders/<uuid:pk>/complete/', views.complete_order, name='order-complete'),
    path('orders/<uuid:pk>/delete/', views.delete_order, name='order-delete'),
    path('orders/history/', views.OrderHistoryView.as_view(), name='order-history'),

    # --------------------------------------------------------------------------
    # OPERATIONAL DISPLAYS (KDS + POS + CUSTOMER)
    # --------------------------------------------------------------------------
    # Original manager-facing display pages
    path('kitchen-display/', views.KitchenDisplayView.as_view(), name='kitchen_display'),
    path('customer-display/', views.CustomerDisplayView.as_view(), name='customer_display'),
    path('pos/', views.POSView.as_view(), name='pos'),

    # --------------------------------------------------------------------------
    # EXTENDED POS MODULE (real‑time channels + APIs)
    # --------------------------------------------------------------------------
    path('pos/dashboard/', pos_views.pos_dashboard, name='pos_dashboard'),
    path('pos/order/<int:table_id>/', pos_views.pos_order_screen, name='pos_order_screen'),
    path('pos/api/create-order/', pos_views.create_order, name='create_order'),
    
    # --- Direct Order API for categories & menu ---
    path('pos/api/categories/', pos_views.api_categories, name='api_categories'),
    path('pos/api/menu-items/', pos_views.api_menu_items, name='api_menu_items'),
    path('pos/api/order/new/', pos_views.api_create_order, name='api_create_order'),
    

    path('pos/kds/', pos_views.kds_screen, name='kds_screen'),
    path('pos/customer/<int:table_id>/', pos_views.customer_display, name='customer_display'),
    # future endpoints:
    # path('pos/api/update-status/', pos_views.update_status, name='update_status'),

    # --------------------------------------------------------------------------
    # INVENTORY MANAGEMENT
    # --------------------------------------------------------------------------
    path('inventory/', views.InventoryListView.as_view(), name='inventory-list'),
    path('inventory/create/', views.InventoryItemCreateView.as_view(), name='inventory-create'),
    path('inventory/<int:pk>/update/', views.InventoryItemUpdateView.as_view(), name='inventory-update'),
    # path('inventory/<int:pk>/delete/', views.InventoryItemDeleteView.as_view(), name='inventory-delete'),

    # --------------------------------------------------------------------------
    # API / AJAX / EXPORT
    # --------------------------------------------------------------------------
    path('api/v1/', include(router.urls)),
    path('ajax/ticket/<int:ticket_id>/update-status/', views.UpdateKitchenTicketStatusView.as_view(), name='ajax-update-ticket-status'),
    path('export/sales/', views.ExportSalesDataView.as_view(), name='export-sales-data'),

    # --------------------------------------------------------------------------
    # CHAT & SETTINGS
    # --------------------------------------------------------------------------
    path('chat/', views.ChatRoomView.as_view(), name='chat-room'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    
    # path('table/<uuid:access_token>/', views.TableDetailView.as_view(), name='table-detail-view'),
    path("table/<uuid:access_token>/", pos_views.table_detail_view, name="table-detail-view"),
    path("tables/<int:restaurant_id>/", views.table_dashboard_view, name="table-dashboard"),

]