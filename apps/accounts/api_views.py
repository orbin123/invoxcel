import requests
from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .google_oauth import GoogleOAuthError, get_or_create_user_from_google, is_configured, verify_id_token
from .serializers import RegisterSerializer


class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": {"id": user.pk, "email": user.email},
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class GoogleOAuthAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not is_configured():
            return Response(
                {
                    "detail": "Google OAuth is not configured yet. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.",
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        id_token = request.data.get("id_token", "").strip()
        if not id_token:
            return Response(
                {"detail": "id_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = verify_id_token(id_token=id_token)
            user = get_or_create_user_from_google(profile)
        except GoogleOAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException:
            return Response(
                {"detail": "Google sign-in is temporarily unavailable. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": {"id": user.pk, "email": user.email},
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


class ObtainTokenPairView(TokenObtainPairView):
    permission_classes = [AllowAny]


class RefreshTokenPairView(TokenRefreshView):
    permission_classes = [AllowAny]
