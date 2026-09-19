from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from apps.accounts.ownership import get_user_batch
from apps.invoices.validation import review_findings
from apps.processing.schema import output_columns
from .services import datasets, render_csv, render_xlsx, export_headers


@login_required
@require_POST
def export(request, pk, format):
    if format not in ("summary.csv", "line-items.csv", "xlsx", "json"):
        return HttpResponseBadRequest("Unknown export format.")
    batch = get_user_batch(request.user, pk)
    analyses = list(batch.document_analyses.select_related("document", "invoice").prefetch_related("invoice__line_items"))
    invoices = [a.invoice for a in analyses if getattr(a, "invoice", None)]
    if not invoices or any(not invoice.reviewed_at for invoice in invoices) or any(a.status in ("pending", "processing") for a in analyses):
        messages.error(request, "Save and mark each extracted invoice reviewed before exporting.")
        return redirect("workspace:detail", pk=pk)
    columns = list(batch.columns.all())
    summary_columns, item_columns = output_columns(batch, invoices)
    exceptions = []
    for analysis in analyses:
        invoice = getattr(analysis, "invoice", None)
        if invoice:
            # Retain unresolved extraction warnings as well as current validation findings.
            azure, programmatic = review_findings(invoice, columns)
            findings = azure + programmatic
            invoice.export_findings = [dict(items) for items in dict.fromkeys(tuple(f.items()) for f in findings)]
            exceptions.extend([analysis.document_id, analysis.document.original_filename, f["field"], f["message"]] for f in invoice.export_findings)
        else:
            exceptions.append([analysis.document_id, analysis.document.original_filename, "processing", analysis.error_message or analysis.get_status_display()])
    summary, items = datasets(invoices, summary_columns, item_columns)
    if format == "json":
        response = JsonResponse({
            "batch_id": batch.number,
            "template": {"name": batch.template.name if batch.template else None, "columns": [{"key": c.key, "label": c.label, "dataset": c.dataset, "type": c.data_type} for c in summary_columns + item_columns]},
            "invoices": [{"document_id": i.analysis.document_id, "source_filename": i.analysis.document.original_filename,
                          "summary": {c.key: i.values.get(c.key) for c in summary_columns},
                          "line_items": [{c.key: item.values.get(c.key) for c in item_columns} for item in i.line_items.all()],
                          "reviewed_at": i.reviewed_at.isoformat(), "validation": i.export_findings} for i in invoices],
            "exceptions": exceptions,
        }, json_dumps_params={"indent": 2})
    elif format == "xlsx":
        response = HttpResponse(render_xlsx(summary_columns, item_columns, summary, items, exceptions), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        selected_columns, rows = (summary_columns, summary) if format == "summary.csv" else (item_columns, items)
        response = HttpResponse(render_csv(export_headers(selected_columns, summary=format == "summary.csv"), rows), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="invoxcel-batch-{batch.number}-{format if "." in format else "export." + format}"'
    return response
