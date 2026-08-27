from rest_framework import authentication
from rest_framework import exceptions
from .models import WebhookConfiguration

class RestaurantApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY') # Look for X-API-Key header
        if not api_key:
            return None # Move to next auth method (like Session or JWT)

        try:
            # Check if the key matches a Live or Test key in our config
            config = WebhookConfiguration.objects.filter(
                live_api_key=api_key
            ).select_related('restaurant').first()
            
            if not config:
                config = WebhookConfiguration.objects.filter(
                    test_api_key=api_key
                ).select_related('restaurant').first()

            if not config:
                raise exceptions.AuthenticationFailed('Invalid API Key')

            # Return a dummy user or the owner of the restaurant
            # This associates the request with the specific restaurant
            owner = config.restaurant.owner 
            return (owner, None)

        except Exception:
            raise exceptions.AuthenticationFailed('API Key Authentication Error')