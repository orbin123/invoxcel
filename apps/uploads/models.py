from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone


def uploaded_document_path(instance, filename):
    """Store uploads under per-user directories with generated names."""
    if not instance.user_id:
        raise ValueError("UploadedDocument requires a user before saving the file.")
    extension = Path(filename).suffix.lower()
    uploaded_at = instance.created_at or timezone.now()
    session_folder = f"{uploaded_at:%Y%m%dT%H%M%S%fZ}-{uuid4().hex[:8]}"
    return f"users/{instance.user_id}/invoices/{session_folder}/document{extension}"


class UploadedDocument(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Extraction failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=uploaded_document_path)
    content_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    template = models.ForeignKey(
        "templates.Template",
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename
