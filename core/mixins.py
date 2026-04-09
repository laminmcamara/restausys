# core/mixins.py

from django.core.exceptions import PermissionDenied


class RestaurantScopedMixin:
    """
    Multi-tenant safety mixin for SaaS architecture.

    ✅ Ensures users only access data belonging to their assigned restaurant.
    ✅ Superusers (platform owners) bypass restrictions.
    ✅ Prevents cross-restaurant data leakage.
    ✅ Auto-assigns restaurant on object creation (DRF compatible).
    ✅ Protects against URL tampering in Detail/Update/Delete views.
    """

    restaurant_field_name = "restaurant"  # Override if model uses different field

    # --------------------------------------------------------------------------
    # Get Restaurant
    # --------------------------------------------------------------------------

    def get_restaurant(self):
        """
        Returns the restaurant associated with the current user.
        Raises PermissionDenied if user is not assigned to a restaurant.
        """

        user = getattr(self.request, "user", None)

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        # ✅ Superuser bypass (Platform owner)
        if user.is_superuser:
            return None

        restaurant = getattr(user, "restaurant", None)

        if not restaurant:
            raise PermissionDenied("User is not assigned to a restaurant.")

        return restaurant

    # --------------------------------------------------------------------------
    # Queryset Isolation
    # --------------------------------------------------------------------------

    def get_queryset(self):
        """
        Filters queryset by current user's restaurant.
        Superusers can access all records.
        """

        base_qs = super().get_queryset()
        user = self.request.user

        # ✅ Platform owner sees everything
        if user.is_superuser:
            return base_qs

        restaurant = self.get_restaurant()

        return base_qs.filter(**{
            self.restaurant_field_name: restaurant
        })

    # --------------------------------------------------------------------------
    # Object-Level Protection (Prevents URL Tampering)
    # --------------------------------------------------------------------------

    def get_object(self, queryset=None):
        """
        Ensures retrieved object belongs to user's restaurant.
        Protects against accessing objects from other tenants.
        """

        obj = super().get_object(queryset)
        user = self.request.user

        # ✅ Superuser bypass
        if user.is_superuser:
            return obj

        obj_restaurant = getattr(obj, self.restaurant_field_name, None)

        if obj_restaurant != user.restaurant:
            raise PermissionDenied("Cross-restaurant access denied.")

        return obj

    # --------------------------------------------------------------------------
    # Auto-Assign Restaurant on Create (DRF Compatible)
    # --------------------------------------------------------------------------

    def perform_create(self, serializer):
        """
        Automatically attaches restaurant on object creation.
        For Django Rest Framework ViewSets.
        """

        user = self.request.user

        # ✅ Superuser can manually assign restaurant
        if user.is_superuser:
            serializer.save()
        else:
            serializer.save(**{
                self.restaurant_field_name: self.get_restaurant()
            })