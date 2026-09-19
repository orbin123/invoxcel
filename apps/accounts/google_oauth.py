import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth.models import User

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

SESSION_STATE_KEY = "google_oauth_state"
SESSION_NEXT_KEY = "google_oauth_next"
OAUTH_SCOPES = "openid email profile"


class GoogleOAuthError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def store_oauth_session(request, *, next_url: str) -> str:
    state = secrets.token_urlsafe(32)
    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_NEXT_KEY] = next_url
    # Persist before redirecting to Google so the callback can verify state.
    request.session.save()
    return state


def pop_oauth_session(request) -> tuple[str, str]:
    state = request.session.pop(SESSION_STATE_KEY, "")
    next_url = request.session.pop(SESSION_NEXT_KEY, settings.LOGIN_REDIRECT_URL)
    request.session.modified = True
    return state, next_url


def build_authorize_url(*, redirect_uri: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": OAUTH_SCOPES,
            "state": state,
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def exchange_code_for_tokens(*, code: str, redirect_uri: str) -> dict:
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise GoogleOAuthError("Google sign-in could not be completed.")
    return response.json()


def fetch_userinfo(*, access_token: str) -> dict:
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if response.status_code != 200:
        raise GoogleOAuthError("Google profile details could not be loaded.")
    return response.json()


def verify_id_token(*, id_token: str) -> dict:
    response = requests.get(
        GOOGLE_TOKENINFO_URL,
        params={"id_token": id_token},
        timeout=10,
    )
    if response.status_code != 200:
        raise GoogleOAuthError("Google sign-in token is invalid or expired.")
    payload = response.json()
    if payload.get("aud") != settings.GOOGLE_OAUTH_CLIENT_ID:
        raise GoogleOAuthError("Google sign-in token is invalid or expired.")
    if payload.get("email_verified") not in {True, "true"}:
        raise GoogleOAuthError("Google account email is not verified.")
    return payload


def get_or_create_user_from_google(profile: dict) -> User:
    email = (profile.get("email") or "").strip().lower()
    if not email:
        raise GoogleOAuthError("Google account did not provide an email address.")
    if profile.get("email_verified") not in {True, "true"}:
        raise GoogleOAuthError("Google account email is not verified.")

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User(username=email, email=email)
        user.set_unusable_password()
        user.save()

    if not user.is_active:
        raise GoogleOAuthError("This account is disabled.")

    given_name = (profile.get("given_name") or "").strip()
    family_name = (profile.get("family_name") or "").strip()
    full_name = " ".join(part for part in (given_name, family_name) if part).strip()
    updated_fields: list[str] = []
    if full_name and user.get_full_name() != full_name:
        user.first_name = given_name[:150]
        user.last_name = family_name[:150]
        updated_fields.extend(["first_name", "last_name"])
    if updated_fields:
        user.save(update_fields=updated_fields)
    return user
