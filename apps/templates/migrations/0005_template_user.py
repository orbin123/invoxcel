import os

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_custom_templates_to_admin(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Template = apps.get_model("templates", "Template")
    username = os.environ.get("INVOXCEL_ADMIN_USERNAME", "admin123")
    admin = User.objects.filter(username=username).first()
    if admin is None:
        admin = User.objects.filter(is_superuser=True).order_by("pk").first()
    if admin is None:
        return
    Template.objects.filter(is_standard=False, user__isnull=True).update(user=admin)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("templates", "0004_company_standard"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="templates",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="template",
            name="name",
            field=models.CharField(max_length=120),
        ),
        migrations.RunPython(assign_custom_templates_to_admin, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="template",
            constraint=models.UniqueConstraint(
                fields=("user", "name"),
                name="unique_template_name_per_user",
            ),
        ),
    ]
