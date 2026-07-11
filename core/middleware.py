from django.shortcuts import redirect
from django.utils import timezone


class SubscriptionMiddleware:
    """
    Enforces subscription validity for restaurant users.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # ✅ Always allow these paths FIRST (prevents loop)
        allowed_paths = [
            "/login/",
            "/logout/",
            "/subscription-required/",
            "/subscription-expired/",
        ]

        if request.path in allowed_paths:
            return self.get_response(request)

        # ✅ Allow admin
        if request.path.startswith("/admin/"):
            return self.get_response(request)

        # ✅ Allow static/media
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return self.get_response(request)

        # ✅ Allow unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # ✅ Allow superusers
        if request.user.is_superuser:
            return self.get_response(request)

        restaurant = getattr(request.user, "restaurant", None)

        if not restaurant:
            return redirect("/login/")

        subscription = getattr(restaurant, "subscription", None)

        if not subscription:
            return redirect("/subscription-required/")

        if not subscription.is_active:
            return redirect("/subscription-required/")

        if subscription.end_date and subscription.end_date < timezone.now().date():
            return redirect("/subscription-expired/")

        return self.get_response(request)