from django.test import SimpleTestCase


class HomeAndAdminSmokeTests(SimpleTestCase):
    def test_home_route_returns_invoxcel(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "InvoXcel")

    def test_admin_is_available(self):
        response = self.client.get("/admin/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
