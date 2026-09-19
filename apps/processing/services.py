from django.db import transaction
from django.utils import timezone

from apps.invoices.models import Invoice, LineItem
from apps.invoices.validation import ITEM_TYPES, SUMMARY_TYPES, confidence_findings, normalize_values, validate_invoice, update_derived_values
from services.azure_document_intelligence import AzureInvoiceClient, ExtractionError
from .models import AnalysisBatch, BatchColumn, DocumentAnalysis
from .schema import discover_columns, merge_columns


def get_extraction_client():
    return AzureInvoiceClient()


def extract_batch(batch, client=None, analysis_id=None):
    client = client or get_extraction_client()
    if batch.template_id and not batch.columns.exists():
        BatchColumn.objects.bulk_create([
            BatchColumn(batch=batch, template_column=column, dataset=column.dataset,
                        key=column.key, label=column.label, data_type=column.data_type,
                        is_required=column.is_required, is_selected=True, fill_with_ai=False,
                        position=column.position)
            for column in batch.template.columns.all()
        ])
    analyses = batch.document_analyses.select_related("document").filter(
        status__in=[DocumentAnalysis.Status.PENDING, DocumentAnalysis.Status.FAILED]
    )
    if analysis_id is not None:
        analyses = analyses.filter(pk=analysis_id)
    for analysis in analyses:
        # Claim before calling Azure so repeated requests cannot submit the same file.
        claimed = DocumentAnalysis.objects.filter(pk=analysis.pk, status=analysis.status).update(status=DocumentAnalysis.Status.PROCESSING)
        if not claimed:
            continue
        try:
            result = client.extract(analysis.document)
            values, parse_findings = normalize_values(result.summary, {**result.metadata.get("summary_types", {}), **SUMMARY_TYPES})
            normalized_items = [normalize_values(item, {**result.metadata.get("item_types", {}), **ITEM_TYPES}) for item in result.line_items]
            invoice = Invoice(analysis=analysis, values=values, provenance=result.provenance.get("summary", {}))
            update_derived_values(invoice)
            if not batch.template_id:
                discover_columns(batch, result.summary, "summary", result.metadata.get("summary_types"))
                for item in result.line_items:
                    discover_columns(batch, item, "line_item", result.metadata.get("item_types"))
            columns = list(batch.columns.all())
            parse_findings += merge_columns(values, invoice.provenance, [c for c in columns if c.dataset == "summary"])
            for index, (item_values, _) in enumerate(normalized_items):
                sources = result.provenance.get("line_items", [])
                normalized_items[index][1].extend(merge_columns(item_values, sources[index] if index < len(sources) else {}, [c for c in columns if c.dataset == "line_item"]))
            findings = parse_findings + validate_invoice(values, [item[0] for item in normalized_items], columns)
            findings += confidence_findings(result.provenance.get("summary", {}))
            for index, (_, item_findings) in enumerate(normalized_items):
                sources = result.provenance.get("line_items", [])
                item_findings += confidence_findings(sources[index] if index < len(sources) else {})
                findings.extend({"field": f"line_items.{index}.{finding['field']}", "message": finding["message"]} for finding in item_findings)
            with transaction.atomic():
                invoice.findings = findings
                invoice.save()
                for index, (item_values, _) in enumerate(normalized_items):
                    sources = result.provenance.get("line_items", [])
                    LineItem.objects.create(invoice=invoice, position=index, values=item_values, provenance=sources[index] if index < len(sources) else {})
                analysis.status = DocumentAnalysis.Status.COMPLETE
                analysis.raw_response = result.raw_response
                analysis.provider_metadata = result.metadata
                analysis.page_count = max(1, result.page_count)
                analysis.is_multi_page = result.page_count > 1
                analysis.has_line_items = bool(normalized_items)
                analysis.document_type = "invoice"
                analysis.suitability = DocumentAnalysis.Suitability.REVIEW if findings else DocumentAnalysis.Suitability.SUITABLE
                analysis.error_message = ""
                analysis.document.status = "processed"
                _save_result(analysis, client)
        except ExtractionError as exc:
            analysis.status = DocumentAnalysis.Status.FAILED
            analysis.error_message = str(exc)
            analysis.raw_response = exc.raw_response
            analysis.provider_metadata = exc.metadata
            analysis.document.status = "failed"
            _save_result(analysis, client)
    batch.status = AnalysisBatch.Status.NEEDS_REVIEW
    batch.save(update_fields=("status", "updated_at"))
    return batch


def _save_result(analysis, client):
    analysis.provider = client.provider
    analysis.model = client.model
    analysis.analyzed_at = timezone.now()
    analysis.save()
    analysis.document.save(update_fields=("status",))
