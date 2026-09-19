from django.contrib.auth.models import User
from django.test import TestCase, override_settings


class HomeAndAdminSmokeTests(TestCase):
    def test_private_media_has_no_direct_route_even_in_debug(self):
        from importlib import reload
        from django.urls import Resolver404, resolve
        from config import urls

        try:
            with override_settings(DEBUG=True):
                reload(urls)
                with self.assertRaises(Resolver404):
                    resolve("/media/users/1/invoices/private.pdf", urlconf=urls)
        finally:
            reload(urls)

    def test_home_route_returns_invoxcel(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "InvoXcel")

    def test_home_shows_auth_prompt_markup_for_anonymous_users(self):
        response = self.client.get("/")
        self.assertContains(response, "data-require-auth")
        self.assertContains(response, "Sign in")

    @override_settings(DEBUG=True)
    def test_localhost_middleware_redirects_127_requests(self):
        response = self.client.get("/", HTTP_HOST="127.0.0.1:8000")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://localhost:8000/")

    def test_home_shows_signed_in_email_for_authenticated_users(self):
        user = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="member-pass-123",
        )
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertContains(response, "header-user-email")
        self.assertContains(response, "member@example.com")
        self.assertNotContains(response, "Welcome! You are signed in as")
        self.assertNotContains(response, "data-require-auth")

    def test_admin_is_available(self):
        response = self.client.get("/admin/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
