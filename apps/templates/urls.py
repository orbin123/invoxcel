from django.urls import path

from . import views

app_name = "templates"

urlpatterns = [
    path("", views.template_list, name="list"),
    path("new/", views.template_create, name="create"),
    path("<int:pk>/edit/", views.template_edit, name="edit"),
    path("<int:pk>/delete/", views.template_delete, name="delete"),
]
