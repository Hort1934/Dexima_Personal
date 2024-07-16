from django.urls import path, include
from django.contrib import admin
from main_service.views import register_request
from django.conf.urls.i18n import i18n_patterns

try:
    from dexima_ats_web_service import local_settings
except ImportError:
    local_settings = None

urlpatterns = [
    path("admin/", admin.site.urls),
]

urlpatterns += i18n_patterns(
    path("", include(("main_service.urls", "main_service"), namespace="main_service")),
    path("register/", register_request, name="register"),
    path("accounts/", include("django.contrib.auth.urls")),
    prefix_default_language=False,
)

app_name = "dexima_ats_web_service"

if local_settings is not None and getattr(local_settings, 'DEBUG', False):
    urlpatterns.append(path("debug/", include("debug_toolbar.urls")))
