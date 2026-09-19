from django.urls import path
from . import views

app_name = "workspace"
urlpatterns = [
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/columns/<int:column_id>/", views.edit_column, name="edit_column"),
    path("<int:pk>/rows/<int:analysis_id>/delete/", views.delete_row, name="delete_row"),
    path("<int:pk>/columns/", views.columns, name="columns"),
    path("<int:pk>/retry/<int:analysis_id>/", views.retry, name="retry"),
]
