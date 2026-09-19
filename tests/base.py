from django.contrib.auth.models import User
from django.test import TestCase


class AuthenticatedTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="test-pass-123",
        )

    def setUp(self):
        self.client.force_login(self.user)
