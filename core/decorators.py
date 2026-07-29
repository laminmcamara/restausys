from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.http import JsonResponse
from core.utils import has_active_subscription


# ============================================================
# ROLE-BASED DECORATOR
# ============================================================

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("core:login")

            if request.user.role not in allowed_roles:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# SUBSCRIPTION DECORATOR (For SaaS Protection)
# ============================================================

def subscription_required(view_func):
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("core:login")

        restaurant = getattr(request.user, "restaurant", None)

        if not restaurant or not has_active_subscription(restaurant):
            return JsonResponse(
                {"error": "Active subscription required."},
                status=403
            )

        return view_func(request, *args, **kwargs)

    return wrapper