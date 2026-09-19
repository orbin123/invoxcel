from django.conf import settings
from django.db import models


STANDARD_SUMMARY_COLUMNS = (
    ("invoice_id", "Invoice ID", "text"),
    ("invoice_number", "Invoice No.", "text"),
    ("invoice_date", "Invoice Date", "date"),
    ("vendor_name", "Vendor Name", "text"),
    ("vendor_gstin", "Vendor GSTIN", "text"),
    ("vendor_address", "Vendor Address", "text"),
    ("customer_name", "Customer Name", "text"),
    ("customer_gstin", "Customer GSTIN", "text"),
    ("po_number", "PO No.", "text"),
    ("currency", "Currency", "text"),
    ("subtotal", "Subtotal", "currency"),
    ("discount", "Discount", "currency"),
    ("taxable_amount", "Taxable Amount", "currency"),
    ("cgst", "CGST", "currency"),
    ("sgst", "SGST", "currency"),
    ("igst", "IGST", "currency"),
    ("other_charges", "Other Charges", "currency"),
    ("calculated_total", "Calculated Total", "currency"),
    ("grand_total", "Extracted Grand Total", "currency"),
    ("total_difference", "Total Difference", "currency"),
    ("due_date", "Due Date", "date"),
    ("payment_terms", "Payment Terms", "text"),
    ("confidence", "Confidence %", "number"),
    ("verification_status", "Verification Status", "text"),
    ("source_file", "Source File", "text"),
)

# Retain optional fields used by existing custom templates.
SUMMARY_COLUMNS = STANDARD_SUMMARY_COLUMNS + (
    ("tax_amount", "Total Tax", "currency"),
    ("shipping", "Shipping", "currency"),
    ("notes", "Notes", "text"),
)

LINE_ITEM_COLUMNS = (
    ("description", "Description", "text"),
    ("quantity", "Quantity", "number"),
    ("unit_price", "Unit price", "currency"),
    ("tax_rate", "Tax rate", "number"),
    ("tax_amount", "Tax amount", "currency"),
    ("amount", "Amount", "currency"),
)


class Template(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="templates",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    is_standard = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_standard", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "name"),
                name="unique_template_name_per_user",
            ),
        ]

    def __str__(self):
        return self.name


class TemplateColumn(models.Model):
    class Dataset(models.TextChoices):
        SUMMARY = "summary", "Summary"
        LINE_ITEM = "line_item", "Line items"

    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        CURRENCY = "currency", "Currency"
        DATE = "date", "Date"
        BOOLEAN = "boolean", "Boolean"

    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name="columns",
    )
    dataset = models.CharField(max_length=16, choices=Dataset.choices)
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=120)
    data_type = models.CharField(max_length=16, choices=DataType.choices)
    position = models.PositiveSmallIntegerField()
    is_custom = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)

    class Meta:
        ordering = ("dataset", "position")
        constraints = [
            models.UniqueConstraint(
                fields=("template", "dataset", "key"),
                name="unique_template_column_key",
            ),
        ]

    def __str__(self):
        return f"{self.template}: {self.label}"
