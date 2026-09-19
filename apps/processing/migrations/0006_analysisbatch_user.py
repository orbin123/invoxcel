import os

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_batches_to_admin(apps, schema_editor):
    User = apps.get_model("auth", "User")
    AnalysisBatch = apps.get_model("processing", "AnalysisBatch")
    username = os.environ.get("INVOXCEL_ADMIN_USERNAME", "admin123")
    admin = User.objects.filter(username=username).first()
    if admin is None:
        admin = User.objects.filter(is_superuser=True).order_by("pk").first()
    if admin is None:
        return
    AnalysisBatch.objects.filter(user__isnull=True).update(user=admin)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("processing", "0005_column_value_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysisbatch",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="analysis_batches",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(assign_batches_to_admin, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="analysisbatch",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="analysis_batches",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
