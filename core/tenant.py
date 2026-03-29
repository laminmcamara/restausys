from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated


class TenantModelViewSet(ModelViewSet):
    """
    Enterprise multi-tenant base ViewSet.
    Enforces restaurant-level isolation.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Restrict queryset to user's restaurant.
        Superuser sees everything.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset

        if hasattr(user, "restaurant") and user.restaurant:
            if hasattr(queryset.model, "restaurant"):
                return queryset.filter(restaurant=user.restaurant)

        return queryset.none()

    def perform_create(self, serializer):
        """
        Automatically assign restaurant on object creation.
        """
        user = self.request.user

        if user.is_superuser:
            serializer.save()
        else:
            if hasattr(serializer.Meta.model, "restaurant"):
                serializer.save(restaurant=user.restaurant)
            else:
                serializer.save()