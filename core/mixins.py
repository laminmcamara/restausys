# core/mixins.py

from django.core.exceptions import PermissionDenied


class RestaurantScopedMixin:
    """
    Multi-tenant safety mixin.

    Ensures users can only access data belonging to their assigned restaurant.
    Automatically filters queryset and enforces restaurant assignment on create.
    """

    restaurant_field_name = "restaurant"  # override if model uses different field

    # --------------------------------------------------------------------------
    # Get Restaurant
    # --------------------------------------------------------------------------

    def get_restaurant(self):
        """
        Returns the restaurant associated with the current user.
        Raises PermissionDenied if none is assigned.
        """

        user = getattr(self.request, "user", None)

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

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
        """

        base_qs = super().get_queryset()
        restaurant = self.get_restaurant()

        return base_qs.filter(**{
            self.restaurant_field_name: restaurant
        })

    # --------------------------------------------------------------------------
    # Auto-Assign Restaurant on Create (DRF compatible)
    # --------------------------------------------------------------------------

    def perform_create(self, serializer):
        """
        Automatically attaches restaurant on object creation.
        (For Django Rest Framework ViewSets)
        """

        serializer.save(**{
            self.restaurant_field_name: self.get_restaurant()
        })