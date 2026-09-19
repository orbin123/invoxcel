from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from tests.base import AuthenticatedTestCase

from apps.processing.models import AnalysisBatch, DocumentAnalysis
from apps.templates.models import Template
from apps.uploads.models import UploadedDocument


GOOGLE_SETTINGS = {
    "GOOGLE_OAUTH_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
}


class SignUpFlowTests(TestCase):
    def test_signin_rejects_external_next_urls(self):
        user = User.objects.create_user(username="redirect-user", password="StrongPass123!")
        self.client.force_login(user)
        for target in ("https://example.org/phishing", "//example.org/phishing"):
            with self.subTest(target=target):
                response = self.client.get(reverse("accounts:signin"), {"next": target})
                self.assertRedirects(response, "/")

    def test_signin_preserves_local_next_url(self):
        user = User.objects.create_user(username="redirect-user", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:signin"), {"next": "/templates/"})
        self.assertRedirects(response, "/templates/")

    def test_signup_logs_user_in_and_shows_email_on_homepage(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "new-user@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(email="new-user@example.com").pk)

        home = self.client.get("/")
        self.assertContains(home, "header-user-email")
        self.assertContains(home, "new-user@example.com")
        self.assertNotContains(home, "Welcome! You are signed in as")
        self.assertContains(home, "profile-menu")
        self.assertNotContains(home, 'href="/accounts/signin/"')
        self.assertNotContains(home, "data-require-auth")


@override_settings(**GOOGLE_SETTINGS)
class GoogleOAuthTests(TestCase):
    @patch("apps.accounts.api_views.verify_id_token")
    def test_api_google_rejects_inactive_user(self, verify_id_token):
        User.objects.create_user(username="disabled@example.com", email="disabled@example.com", is_active=False)
        verify_id_token.return_value = {"email": "disabled@example.com", "email_verified": True}
        response = self.client.post(reverse("accounts:api_google"), {"id_token": "valid-token"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access", response.json())

    @patch("apps.accounts.views.fetch_userinfo")
    @patch("apps.accounts.views.exchange_code_for_tokens", return_value={"access_token": "token"})
    def test_google_callback_rejects_inactive_user(self, exchange, fetch):
        User.objects.create_user(username="disabled@example.com", email="disabled@example.com", is_active=False)
        fetch.return_value = {"email": "disabled@example.com", "email_verified": True}
        session = self.client.session
        session["google_oauth_state"] = "expected-state"
        session.save()
        response = self.client.get(reverse("accounts:google_callback"), {"code": "code", "state": "expected-state"})
        self.assertRedirects(response, reverse("accounts:signin"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_google_start_redirects_to_google(self):
        response = self.client.get(reverse("accounts:google_start"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", response["Location"])
        self.assertIn("client_id=test-client-id.apps.googleusercontent.com", response["Location"])
        self.assertIn("state=", response["Location"])

    def test_google_start_persists_oauth_state_in_session(self):
        response = self.client.get(reverse("accounts:google_start"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("google_oauth_state", self.client.session)
        self.assertIn("google_oauth_next", self.client.session)

    def test_google_callback_logs_in_new_user(self):
        session = self.client.session
        session["google_oauth_state"] = "expected-state"
        session["google_oauth_next"] = "/"
        session.save()

        token_payload = {"access_token": "google-access-token"}
        profile = {
            "email": "google-user@example.com",
            "email_verified": True,
        }

        with patch("apps.accounts.views.exchange_code_for_tokens", return_value=token_payload), patch(
            "apps.accounts.views.fetch_userinfo",
            return_value=profile,
        ):
            response = self.client.get(
                reverse("accounts:google_callback"),
                {"code": "auth-code", "state": "expected-state"},
                follow=True,
            )

        user = User.objects.get(email="google-user@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/")
        self.assertEqual(user.username, "google-user@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertContains(response, "header-user-email")
        self.assertContains(response, "google-user@example.com")
        self.assertNotContains(response, "Welcome! You are signed in as")

    def test_google_callback_logs_in_existing_user_by_email(self):
        existing = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="existing-pass-123",
        )
        session = self.client.session
        session["google_oauth_state"] = "expected-state"
        session["google_oauth_next"] = "/"
        session.save()

        with patch("apps.accounts.views.exchange_code_for_tokens", return_value={"access_token": "token"}), patch(
            "apps.accounts.views.fetch_userinfo",
            return_value={"email": "existing@example.com", "email_verified": True},
        ):
            response = self.client.get(
                reverse("accounts:google_callback"),
                {"code": "auth-code", "state": "expected-state"},
            )

        self.assertRedirects(response, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), existing.pk)

    def test_google_callback_rejects_invalid_state(self):
        session = self.client.session
        session["google_oauth_state"] = "expected-state"
        session.save()

        response = self.client.get(
            reverse("accounts:google_callback"),
            {"code": "auth-code", "state": "wrong-state"},
        )

        self.assertRedirects(response, reverse("accounts:signin"))
        self.assertFalse(User.objects.filter(email="google-user@example.com").exists())

    @patch("apps.accounts.api_views.verify_id_token")
    def test_api_google_returns_jwt_for_valid_id_token(self, verify_id_token):
        verify_id_token.return_value = {
            "email": "api-google@example.com",
            "email_verified": True,
        }
        response = self.client.post(
            reverse("accounts:api_google"),
            {"id_token": "valid-id-token"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["email"], "api-google@example.com")
        self.assertTrue(payload["access"])
        self.assertTrue(payload["refresh"])


@override_settings(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="", AZURE_DOCUMENT_INTELLIGENCE_KEY="")
class UserOwnershipTests(AuthenticatedTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="other-pass-123",
        )
        cls.standard_template = Template.objects.get(is_standard=True)

    def create_batch_for(self, user):
        batch = AnalysisBatch.objects.create(template=self.standard_template, user=user)
        return batch

    def test_batches_are_isolated_between_users(self):
        own_batch = self.create_batch_for(self.user)
        other_batch = self.create_batch_for(self.other_user)

        response = self.client.get(reverse("uploads:upload"))
        self.assertContains(response, "Batch 1")

        self.assertEqual(self.client.get(reverse("workspace:detail", args=[other_batch.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("processing:delete_batch", args=[other_batch.pk])).status_code, 404)

    def test_templates_are_isolated_between_users(self):
        own_template = Template.objects.create(name="My import", user=self.user)
        other_template = Template.objects.create(name="Other import", user=self.other_user)

        response = self.client.get(reverse("templates:list"))
        self.assertContains(response, own_template.name)
        self.assertNotContains(response, other_template.name)

        self.assertEqual(self.client.get(reverse("templates:edit", args=[other_template.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("templates:delete", args=[other_template.pk])).status_code, 404)

    def test_users_can_reuse_the_same_template_name(self):
        Template.objects.create(name="Shared name", user=self.user)
        other_template = Template.objects.create(name="Shared name", user=self.other_user)
        self.assertTrue(Template.objects.filter(pk=other_template.pk).exists())

    def test_upload_assigns_batch_to_current_user(self):
        uploaded = SimpleUploadedFile("mine.pdf", b"%PDF-1.4\n%%EOF")
        response = self.client.post(
            reverse("uploads:upload"),
            {"document": uploaded, "template": self.standard_template.pk},
        )
        batch = AnalysisBatch.objects.latest("pk")
        self.assertRedirects(response, reverse("workspace:detail", args=[batch.pk]))
        self.assertEqual(batch.user, self.user)

    def test_uploaded_files_are_stored_under_user_directory(self):
        uploaded = SimpleUploadedFile("mine.pdf", b"%PDF-1.4\n%%EOF")
        self.client.post(
            reverse("uploads:upload"),
            {"document": uploaded, "template": self.standard_template.pk},
        )
        document = UploadedDocument.objects.latest("pk")
        self.assertTrue(document.file.name.startswith(f"users/{self.user.pk}/invoices/"))
        self.assertEqual(document.user, self.user)

    def test_users_cannot_access_other_users_source_files(self):
        document = UploadedDocument.objects.create(
            user=self.other_user,
            original_filename="private.pdf",
            file=SimpleUploadedFile("private.pdf", b"%PDF-1.4\n%%EOF"),
            content_type="application/pdf",
            size_bytes=14,
            template=self.standard_template,
        )
        DocumentAnalysis.objects.create(
            batch=self.create_batch_for(self.other_user),
            document=document,
        )
        self.assertEqual(self.client.get(reverse("uploads:source", args=[document.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("uploads:detail", args=[document.pk])).status_code, 404)
