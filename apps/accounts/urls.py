from django.urls import path

from . import views
from .api_views import (
    GoogleOAuthAPIView,
    ObtainTokenPairView,
    RefreshTokenPairView,
    RegisterAPIView,
)

app_name = "accounts"

urlpatterns = [
    path("signin/", views.signin, name="signin"),
    path("signup/", views.signup, name="signup"),
    path("signout/", views.signout, name="signout"),
    path("google/", views.google_start, name="google_start"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("api/register/", RegisterAPIView.as_view(), name="api_register"),
    path("api/token/", ObtainTokenPairView.as_view(), name="api_token"),
    path("api/token/refresh/", RefreshTokenPairView.as_view(), name="api_token_refresh"),
    path("api/google/", GoogleOAuthAPIView.as_view(), name="api_google"),
]
