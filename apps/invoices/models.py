from django.db import models


class Invoice(models.Model):
    analysis = models.OneToOneField("processing.DocumentAnalysis", on_delete=models.CASCADE, related_name="invoice")
    values = models.JSONField(default=dict)
    provenance = models.JSONField(default=dict)
    findings = models.JSONField(default=list)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.values.get("invoice_number") or f"Invoice {self.pk}"


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    position = models.PositiveIntegerField()
    values = models.JSONField(default=dict)
    provenance = models.JSONField(default=dict)

    class Meta:
        ordering = ("position", "pk")
