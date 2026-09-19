from django.urls import path
from . import views
app_name = "exports"
urlpatterns = [path("<int:pk>/<str:format>/", views.export, name="download")]
