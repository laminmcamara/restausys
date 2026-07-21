from .models import Restaurant, CashierShift


def restaurant_context(request):
    """
    Global context:
    - restaurant
    - active_shift (for cashiers)
    """

    # ✅ Restaurant (single-tenant version)
    restaurant = Restaurant.objects.first()

    active_shift = None

    # ✅ Only check shift if user is authenticated
    if request.user.is_authenticated and hasattr(request.user, "restaurant"):

        active_shift = CashierShift.objects.filter(
            user=request.user,
            restaurant=request.user.restaurant,
            is_active=True
        ).first()

    return {
        "restaurant": restaurant,
        "active_shift": active_shift,
    }