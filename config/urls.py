from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.uploads.urls")),
    path("processing/", include("apps.processing.urls")),
    path("templates/", include("apps.templates.urls")),
    path("workspace/", include("apps.workspace.urls")),
    path("exports/", include("apps.exports.urls")),
    path("admin/", admin.site.urls),
]
