from django.db import migrations


def mark_legacy_results(apps, schema_editor):
    Analysis = apps.get_model("processing", "DocumentAnalysis")
    Document = apps.get_model("uploads", "UploadedDocument")
    Invoice = apps.get_model("invoices", "Invoice")
    legacy = Analysis.objects.exclude(pk__in=Invoice.objects.values("analysis_id")).exclude(provider="azure_document_intelligence")
    document_ids = list(legacy.values_list("document_id", flat=True))
    legacy.update(status="failed", error_message="This document needs invoice extraction. Retry extraction to create editable values.")
    Document.objects.filter(pk__in=document_ids).update(status="failed")


class Migration(migrations.Migration):
    dependencies = [("processing", "0002_batchcolumn_is_required_and_more"), ("invoices", "0001_initial")]
    operations = [migrations.RunPython(mark_legacy_results, migrations.RunPython.noop)]
