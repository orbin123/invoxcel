from django.contrib import messages
from django.contrib.auth import login

AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


def establish_user_session(request, user, *, message=None):
    """Create a durable session for the authenticated user."""
    login(request, user, backend=AUTH_BACKEND)
    if message:
        messages.success(request, message)
    request.session.modified = True
