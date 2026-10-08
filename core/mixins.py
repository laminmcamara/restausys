# core/mixins.py

from rest_framework.exceptions import (
    NotAuthenticated,
    PermissionDenied,
)

from core.utils import has_active_subscription


class GlobalAuthorityMixin:
    """
    Shared helpers for superusers and platform owners.
    """

    def is_global_authority(self):
        user = self.request.user

        return (
            user.is_authenticated
            and (
                user.is_superuser
                or getattr(
                    user,
                    "is_platform_owner",
                    False,
                )
            )
        )


class SubscriptionRequiredMixin(
    GlobalAuthorityMixin
):
    """
    Requires an authenticated user with an
    active restaurant subscription.

    Superusers and platform owners bypass
    subscription enforcement.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(
            request,
            *args,
            **kwargs,
        )

        user = request.user

        if not user.is_authenticated:
            raise NotAuthenticated(
                "Authentication credentials were not provided."
            )

        if self.is_global_authority():
            return

        restaurant = getattr(
            user,
            "restaurant",
            None,
        )

        if restaurant is None:
            raise PermissionDenied(
                "User is not assigned to a restaurant."
            )

        subscription = restaurant.subscription

        if subscription is None:
            raise PermissionDenied(
                "No subscription found for this restaurant."
            )

        if subscription.status not in ["active", "trialing"] or (subscription.current_period_end is not None and subscription.current_period_end < timezone.now()):
            raise PermissionDenied(
                "An active subscription or trial is required."
            )

class RestaurantScopedMixin(
    GlobalAuthorityMixin
):
    """
    Restricts queryset results and object access
    to the authenticated user's restaurant.
    """

    restaurant_field_name = "restaurant"

    def get_restaurant(self):
        user = self.request.user

        if not user.is_authenticated:
            raise NotAuthenticated(
                "Authentication credentials were not provided."
            )

        if self.is_global_authority():
            return None

        restaurant = getattr(
            user,
            "restaurant",
            None,
        )

        if restaurant is None:
            raise PermissionDenied(
                "User is not assigned to a restaurant."
            )

        return restaurant

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.is_global_authority():
            return queryset

        restaurant = self.get_restaurant()

        return queryset.filter(
            **{
                self.restaurant_field_name:
                restaurant
            }
        )

    def get_object(self):
        obj = super().get_object()

        if self.is_global_authority():
            return obj

        user_restaurant = self.get_restaurant()
        object_restaurant = getattr(
            obj,
            self.restaurant_field_name,
            None,
        )

        if object_restaurant != user_restaurant:
            raise PermissionDenied(
                "Cross-restaurant access denied."
            )

        return obj

    def perform_create(self, serializer):
        if self.is_global_authority():
            serializer.save()
            return

        serializer.save(
            **{
                self.restaurant_field_name:
                self.get_restaurant()
            }
        )