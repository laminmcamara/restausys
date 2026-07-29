# core/mixins.py

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


# =============================================================================
# Subscription Enforcement
# =============================================================================

# =============================================================================
# Subscription Enforcement
# =============================================================================

from core.utils import has_active_subscription


class SubscriptionRequiredMixin:
    """
    Ensures the user's restaurant has an active subscription.
    Superusers and platform owners bypass this check.
    """

    def dispatch(self, request, *args, **kwargs):

        user = request.user

        # ✅ Global authority bypass
        if user.is_superuser or getattr(user, "is_platform_owner", False):
            return super().dispatch(request, *args, **kwargs)

        if not user.is_authenticated:
            return redirect("core:login")

        restaurant = getattr(user, "restaurant", None)

        if not restaurant:
            return redirect("core:subscription_expired")

        # ✅ USE CENTRALIZED SUBSCRIPTION LOGIC
        if not has_active_subscription(restaurant):
            return redirect("core:subscription_expired")

        return super().dispatch(request, *args, **kwargs)

# =============================================================================
# Multi-Tenant Isolation
# =============================================================================

class RestaurantScopedMixin:
    """
    Multi-tenant safety mixin for SaaS architecture.
    """

    restaurant_field_name = "restaurant"

    def get_restaurant(self):
        user = getattr(self.request, "user", None)

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        # ✅ Global authority bypass
        if user.is_superuser or getattr(user, "is_platform_owner", False):
            return None

        restaurant = getattr(user, "restaurant", None)

        if not restaurant:
            raise PermissionDenied("User is not assigned to a restaurant.")

        return restaurant

    def get_queryset(self):
        base_qs = super().get_queryset()
        user = self.request.user

        # ✅ Global authority bypass
        if user.is_superuser or getattr(user, "is_platform_owner", False):
            return base_qs

        restaurant = self.get_restaurant()

        return base_qs.filter(**{
            self.restaurant_field_name: restaurant
        })

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        # ✅ Global authority bypass
        if user.is_superuser or getattr(user, "is_platform_owner", False):
            return obj

        obj_restaurant = getattr(obj, self.restaurant_field_name, None)

        if obj_restaurant != user.restaurant:
            raise PermissionDenied("Cross-restaurant access denied.")

        return obj

    def perform_create(self, serializer):
        user = self.request.user

        # ✅ Global authority bypass
        if user.is_superuser or getattr(user, "is_platform_owner", False):
            serializer.save()
        else:
            serializer.save(**{
                self.restaurant_field_name: self.get_restaurant()
            })