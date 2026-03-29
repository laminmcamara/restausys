class TenantWebMixin:
    """
    Enforces restaurant isolation for Django Template Views.
    """

    def get_restaurant(self):
        user = self.request.user
        if user.is_superuser:
            return None
        return getattr(user, "restaurant", None)

    def filter_by_restaurant(self, queryset, field="restaurant"):
        restaurant = self.get_restaurant()

        if self.request.user.is_superuser:
            return queryset

        if restaurant:
            return queryset.filter(**{field: restaurant})

        return queryset.none()