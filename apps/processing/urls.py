from django.urls import path

from . import views

app_name = "processing"

urlpatterns = [
    path("analysis/<int:pk>/", views.analysis_review, name="analysis"),
    path("batches/<int:pk>/delete/", views.delete_batch, name="delete_batch"),
]
