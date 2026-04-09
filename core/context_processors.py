from .models import Restaurant

def restaurant_context(request):
    try:
        restaurant = Restaurant.objects.first()  # or filter by user if multi-tenant
    except Restaurant.DoesNotExist:
        restaurant = None

    return {
        "restaurant": restaurant
    }