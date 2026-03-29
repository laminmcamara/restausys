# restaurant_management/urls.py

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

# ==============================================================================
# ✅ CORRECTED PROJECT URLs
#
# We have removed the direct path to 'pos_views.dashboard_view' from this file.
# Now, any request to the root URL ('') will be handed off to your 'core.urls'
# file to be processed there. This resolves the URL conflict and keeps your
# project organized.
#
# We also no longer need to import 'pos_views' here, because it's not being
# used in this file anymore.
# ==============================================================================

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    # This single line now handles your homepage and all other URLs for the 'core' app.
    # path('', include('core.urls')),
    path('', include('core.urls', namespace='core')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)