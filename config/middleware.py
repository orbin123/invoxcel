from django.conf import settings
from django.http import HttpResponseRedirect


class CanonicalLocalhostMiddleware:
    """Keep local sessions on one host so OAuth callbacks reuse the same cookie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.META.get("HTTP_HOST", "")
        if settings.DEBUG and host.startswith("127.0.0.1"):
            port = host.split(":", 1)[1] if ":" in host else ""
            target_host = f"localhost:{port}" if port else "localhost"
            scheme = "https" if request.is_secure() else "http"
            return HttpResponseRedirect(f"{scheme}://{target_host}{request.get_full_path()}")
        return self.get_response(request)
