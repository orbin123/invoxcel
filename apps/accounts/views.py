import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .forms import SignInForm, SignUpForm
from .session_auth import establish_user_session
from .google_oauth import (
    GoogleOAuthError,
    build_authorize_url,
    exchange_code_for_tokens,
    fetch_userinfo,
    get_or_create_user_from_google,
    is_configured,
    pop_oauth_session,
    store_oauth_session,
)


def _auth_redirect_target(request, target=None):
    target = target if target is not None else request.GET.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return settings.LOGIN_REDIRECT_URL


@require_http_methods(["GET", "POST"])
def signin(request):
    if request.user.is_authenticated:
        return redirect(_auth_redirect_target(request))

    form = SignInForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        establish_user_session(request, user)
        return redirect(_auth_redirect_target(request))

    return render(
        request,
        "invoxcel/accounts/signin.html",
        {
            "form": form,
            "page_title": "Sign in",
            "page_description": "Sign in to your InvoXcel workspace.",
        },
    )


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect(_auth_redirect_target(request))

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        authenticated_user = authenticate(
            request,
            username=user.username,
            password=form.cleaned_data["password1"],
        )
        establish_user_session(request, authenticated_user or user)
        return redirect(_auth_redirect_target(request))

    return render(
        request,
        "invoxcel/accounts/signup.html",
        {
            "form": form,
            "page_title": "Sign up",
            "page_description": "Create your InvoXcel account.",
        },
    )


@require_http_methods(["POST"])
@login_required
def signout(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


def _google_redirect_uri(request):
    return request.build_absolute_uri(reverse("accounts:google_callback"))


def _google_failure_redirect(request, message: str):
    messages.error(request, message)
    return redirect("accounts:signin")


@require_http_methods(["GET"])
def google_start(request):
    if request.user.is_authenticated:
        return redirect(_auth_redirect_target(request))

    if not is_configured():
        messages.info(
            request,
            "Google sign-in is not configured yet. Use email and password for now.",
        )
        return redirect("accounts:signin")

    state = store_oauth_session(request, next_url=_auth_redirect_target(request))
    authorize_url = build_authorize_url(
        redirect_uri=_google_redirect_uri(request),
        state=state,
    )
    return redirect(authorize_url)


@require_http_methods(["GET"])
def google_callback(request):
    if request.user.is_authenticated:
        return redirect(_auth_redirect_target(request))

    if not is_configured():
        return _google_failure_redirect(
            request,
            "Google sign-in is not configured yet. Use email and password for now.",
        )

    oauth_error = request.GET.get("error")
    if oauth_error:
        return _google_failure_redirect(
            request,
            "Google sign-in was cancelled. Try again or use email and password.",
        )

    expected_state, next_url = pop_oauth_session(request)
    state = request.GET.get("state", "")
    code = request.GET.get("code", "")
    if not expected_state or not state or state != expected_state:
        return _google_failure_redirect(
            request,
            "Google sign-in could not be verified. Use http://localhost:8000 consistently and try again.",
        )
    if not code:
        return _google_failure_redirect(
            request,
            "Google sign-in did not complete. Please try again.",
        )

    redirect_uri = _google_redirect_uri(request)
    try:
        token_payload = exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)
        access_token = token_payload.get("access_token")
        if not access_token:
            raise GoogleOAuthError("Google sign-in could not be completed.")
        profile = fetch_userinfo(access_token=access_token)
        user = get_or_create_user_from_google(profile)
    except GoogleOAuthError as exc:
        return _google_failure_redirect(request, str(exc))
    except requests.RequestException:
        return _google_failure_redirect(
            request,
            "Google sign-in is temporarily unavailable. Please try again.",
        )

    establish_user_session(request, user)
    return redirect(_auth_redirect_target(request, next_url))
