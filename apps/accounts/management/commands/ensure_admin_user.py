import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the local admin user from environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("INVOXCEL_ADMIN_USERNAME", "admin123")
        password = os.environ.get("INVOXCEL_ADMIN_PASSWORD")
        email = os.environ.get("INVOXCEL_ADMIN_EMAIL", "admin@invoxcel.local")

        if not password:
            self.stderr.write(
                "Set INVOXCEL_ADMIN_PASSWORD before running this command."
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} admin user '{username}'.")
