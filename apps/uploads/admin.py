from django.contrib import admin

from .models import UploadedDocument


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "user",
        "template",
        "content_type",
        "size_bytes",
        "status",
        "created_at",
    )
    list_filter = ("status", "content_type", "template", "user")
    readonly_fields = (
        "original_filename",
        "file",
        "content_type",
        "size_bytes",
        "status",
        "template",
        "created_at",
    )
