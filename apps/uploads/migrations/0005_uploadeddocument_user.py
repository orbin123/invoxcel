import os
from pathlib import Path

import django.db.models.deletion
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import migrations, models


def _admin_user_id(User):
    username = os.environ.get("INVOXCEL_ADMIN_USERNAME", "admin123")
    admin = User.objects.filter(username=username).first()
    if admin is None:
        admin = User.objects.filter(is_superuser=True).order_by("pk").first()
    return admin.pk if admin else None


def backfill_upload_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UploadedDocument = apps.get_model("uploads", "UploadedDocument")
    DocumentAnalysis = apps.get_model("processing", "DocumentAnalysis")
    AnalysisBatch = apps.get_model("processing", "AnalysisBatch")
    admin_id = _admin_user_id(User)

    for document in UploadedDocument.objects.filter(user__isnull=True).iterator():
        analysis = DocumentAnalysis.objects.filter(document_id=document.pk).first()
        if analysis:
            batch = AnalysisBatch.objects.get(pk=analysis.batch_id)
            document.user_id = batch.user_id
        elif admin_id:
            document.user_id = admin_id
        else:
            continue
        document.save(update_fields=["user_id"])


def relocate_upload_files(apps, schema_editor):
    UploadedDocument = apps.get_model("uploads", "UploadedDocument")

    for document in UploadedDocument.objects.exclude(file="").iterator():
        old_name = document.file.name if hasattr(document.file, "name") else document.file
        if not old_name or old_name.startswith("users/"):
            continue
        if not document.user_id:
            continue

        parts = old_name.split("/")
        if parts[0] == "invoices" and len(parts) >= 3:
            new_name = f"users/{document.user_id}/{parts[0]}/{parts[1]}/{parts[2]}"
        else:
            extension = Path(old_name).suffix or ".pdf"
            new_name = (
                f"users/{document.user_id}/invoices/migrated-{document.pk}/document{extension}"
            )

        if default_storage.exists(old_name):
            with default_storage.open(old_name, "rb") as source:
                if default_storage.exists(new_name):
                    default_storage.delete(new_name)
                default_storage.save(new_name, source)
            default_storage.delete(old_name)

        document.file = new_name
        document.save(update_fields=["file"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("processing", "0006_analysisbatch_user"),
        ("uploads", "0004_alter_uploadeddocument_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadeddocument",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="uploaded_documents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_upload_users, migrations.RunPython.noop),
        migrations.RunPython(relocate_upload_files, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="uploadeddocument",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="uploaded_documents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
