from django.urls import path

from . import views

app_name = "uploads"

urlpatterns = [
    path("uploads/<int:pk>/pages/<int:page_number>/", views.preview, name="preview"),
    path("", views.upload, name="upload"),
    path("uploads/<int:pk>/source/", views.source, name="source"),
    path("uploads/<int:pk>/", views.detail, name="detail"),
]
