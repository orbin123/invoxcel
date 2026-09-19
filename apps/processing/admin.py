from django.contrib import admin

from .models import AnalysisBatch, BatchColumn, DocumentAnalysis


class DocumentAnalysisInline(admin.TabularInline):
    model = DocumentAnalysis
    extra = 0
    readonly_fields = (
        "document",
        "status",
        "document_type",
        "suitability",
        "page_count",
        "has_line_items",
        "has_tables",
        "provider",
        "model",
        "analyzed_at",
    )


class BatchColumnInline(admin.TabularInline):
    model = BatchColumn
    extra = 0


@admin.register(AnalysisBatch)
class AnalysisBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "user", "template", "status", "created_at", "updated_at")
    list_filter = ("status", "template", "user")
    inlines = (DocumentAnalysisInline, BatchColumnInline)


@admin.register(DocumentAnalysis)
class DocumentAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "batch",
        "status",
        "document_type",
        "suitability",
        "model",
        "analyzed_at",
    )
    list_filter = ("status", "document_type", "suitability", "provider", "model")
    readonly_fields = ("raw_response", "error_message", "analyzed_at")
