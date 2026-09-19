from django.conf import settings
from django.db import models
from django.db.models import Max


class AnalysisBatch(models.Model):
    class Status(models.TextChoices):
        ANALYZING = "analyzing", "Extracting"
        READY = "ready", "Ready for review"
        NEEDS_REVIEW = "needs_review", "Needs review"
        CONFIRMED = "confirmed", "Reviewed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_batches",
    )
    number = models.PositiveIntegerField(editable=False)
    template = models.ForeignKey(
        "templates.Template",
        on_delete=models.PROTECT,
        related_name="analysis_batches",
        null=True,
        blank=True,
    )
    hide_empty_columns = models.BooleanField(default=False)
    instructions = models.TextField(blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.ANALYZING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "number"),
                name="unique_user_batch_number",
            )
        ]

    def save(self, *args, **kwargs):
        if self._state.adding and self.number is None:
            latest = AnalysisBatch.objects.filter(user_id=self.user_id).aggregate(Max("number"))["number__max"]
            self.number = (latest or 0) + 1
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return f"Batch {self.number}"

    def __str__(self):
        return self.display_name


class DocumentAnalysis(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Extracting"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    class Suitability(models.TextChoices):
        SUITABLE = "suitable", "Suitable"
        REVIEW = "review", "Review recommended"
        UNSUPPORTED = "unsupported", "Unsupported"

    batch = models.ForeignKey(
        AnalysisBatch,
        on_delete=models.CASCADE,
        related_name="document_analyses",
    )
    document = models.OneToOneField(
        "uploads.UploadedDocument",
        on_delete=models.CASCADE,
        related_name="analysis",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    document_type = models.CharField(max_length=32, default="unknown")
    suitability = models.CharField(
        max_length=16,
        choices=Suitability.choices,
        default=Suitability.REVIEW,
    )
    page_count = models.PositiveSmallIntegerField(default=1)
    is_multi_page = models.BooleanField(default=False)
    has_line_items = models.BooleanField(default=False)
    has_tables = models.BooleanField(default=False)
    detected_summary_keys = models.JSONField(default=list)
    detected_line_item_keys = models.JSONField(default=list)
    custom_fields = models.JSONField(default=list)
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=64, blank=True)
    raw_response = models.TextField(blank=True)
    provider_metadata = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("document_id",)

    def __str__(self):
        return f"Analysis for {self.document}"

    @property
    def document_type_label(self):
        return {
            "invoice": "Invoice",
            "receipt": "Receipt",
            "credit_note": "Credit note",
            "purchase_order": "Purchase order",
            "unknown": "Unknown",
        }.get(self.document_type, "Unknown")


class BatchColumn(models.Model):
    class Dataset(models.TextChoices):
        SUMMARY = "summary", "Summary"
        LINE_ITEM = "line_item", "Line items"

    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        CURRENCY = "currency", "Currency"
        DATE = "date", "Date"
        BOOLEAN = "boolean", "Boolean"

    class Source(models.TextChoices):
        TEMPLATE = "template", "Template"
        CUSTOM = "custom", "Custom"

    batch = models.ForeignKey(
        AnalysisBatch,
        on_delete=models.CASCADE,
        related_name="columns",
    )
    template_column = models.ForeignKey(
        "templates.TemplateColumn",
        on_delete=models.SET_NULL,
        related_name="batch_columns",
        null=True,
        blank=True,
    )
    dataset = models.CharField(max_length=16, choices=Dataset.choices)
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=120)
    value_key = models.SlugField(max_length=80, blank=True)
    data_type = models.CharField(max_length=16, choices=DataType.choices)
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.TEMPLATE,
    )
    fill_with_ai = models.BooleanField(default=True)
    is_selected = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("dataset", "position")
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "dataset", "key"),
                name="unique_batch_column_key",
            )
        ]

    def __str__(self):
        return f"{self.batch}: {self.label}"
