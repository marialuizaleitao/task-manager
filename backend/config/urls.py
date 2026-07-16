from django.contrib import admin
from django.urls import include, path

from config.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/", include("apps.accounts.urls", namespace="accounts")),
    path("api/", include("apps.categories.urls", namespace="categories")),
    path("api/", include("apps.tasks.urls", namespace="tasks")),
    path("api/", include("apps.sharing.urls", namespace="sharing")),
    path(
        "api/integrations/",
        include("apps.integrations.google_calendar.urls", namespace="google_calendar"),
    ),
    path(
        "api/integrations/",
        include("apps.integrations.telegram.urls", namespace="telegram"),
    ),
]
