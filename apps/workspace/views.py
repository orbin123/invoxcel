from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.accounts.ownership import get_user_batch
from apps.invoices.models import Invoice, LineItem
from apps.invoices.validation import validate_invoice, update_derived_values, review_findings
from apps.processing.models import AnalysisBatch, BatchColumn, DocumentAnalysis
from apps.processing.schema import merge_columns, output_columns, matched_key
from apps.processing.services import extract_batch
from .forms import ValuesForm, LineItemFormSet


@login_required
def detail(request, pk):
    batch = get_user_batch(
        request.user,
        pk,
        AnalysisBatch.objects.select_related("template"),
    )
    analyses = list(batch.document_analyses.select_related("document", "invoice").prefetch_related("invoice__line_items").all())
    selected_id = request.GET.get("document")
    selected = next((a for a in analyses if str(a.pk) == selected_id), None)
    if selected_id and selected is None:
        return HttpResponseBadRequest("Document is not in this batch.")
    selected = selected or next(iter(analyses), None)
    selected_index = analyses.index(selected) if selected else None
    previous_analysis = analyses[selected_index - 1] if selected_index and selected_index > 0 else None
    next_analysis = analyses[selected_index + 1] if selected_index is not None and selected_index + 1 < len(analyses) else None
    invoice = getattr(selected, "invoice", None)
    columns = list(batch.columns.all())
    summary_columns, item_columns = output_columns(batch, [a.invoice for a in analyses if getattr(a, "invoice", None)])
    azure_findings, programmatic_findings = review_findings(invoice, columns) if invoice else ([], [])
    form = formset = None
    if invoice:
        items = list(invoice.line_items.all())
        form = ValuesForm(request.POST if request.method == "POST" else None, columns=summary_columns, initial=dict(invoice.values), prefix="summary")
        formset = LineItemFormSet(request.POST if request.method == "POST" else None, initial=[dict(item.values, row_id=item.pk) for item in items], prefix="items", form_kwargs={"columns": item_columns})
        if request.method == "POST":
            valid_form, valid_items = form.is_valid(), formset.is_valid()
            if valid_form and valid_items:
                ids = [f.cleaned_data.get("row_id") for f in formset.forms if f.cleaned_data.get("row_id")]
                if sorted(ids) != sorted(item.pk for item in items):
                    return HttpResponseBadRequest("Line items changed or are not part of this invoice. Reload before saving.")
                try:
                    revision = parse_datetime(request.POST.get("revision", ""))
                except ValueError:
                    revision = None
                if revision is None:
                    return HttpResponseBadRequest("Invalid revision. Reload before saving.")
                with transaction.atomic():
                    # Claim the revision before writes; stale tabs must not overwrite newer edits.
                    claimed = Invoice.objects.filter(pk=invoice.pk, updated_at=revision).update(updated_at=timezone.now()) if request.POST.get("revision") else 0
                    if claimed:
                        invoice.values.update(form.cleaned_data)
                        for column in summary_columns:
                            if column.value_key and column.key in form.changed_data:
                                invoice.values[column.value_key] = form.cleaned_data[column.key]
                                invoice.provenance.pop(column.value_key, None)
                        invoice.provenance = _remaining_sources(invoice.provenance, form.changed_data)
                        existing = {item.pk: item for item in items}
                        current_items = []
                        for position, row_form in enumerate(formset.forms):
                            data = row_form.cleaned_data
                            if not data:
                                continue
                            row = existing.get(data.get("row_id"))
                            if data.get("DELETE"):
                                if row:
                                    row.delete()
                                continue
                            values = {c.key: data.get(c.key) for c in item_columns}
                            if row is None and not any(v is not None for v in values.values()):
                                continue
                            row = row or LineItem(invoice=invoice)
                            row.values.update(values)
                            for column in item_columns:
                                if column.value_key and column.key in row_form.changed_data:
                                    row.values[column.value_key] = values[column.key]
                            row.provenance = _remaining_sources(row.provenance, row_form.changed_data)
                            row.position = position
                            row.save()
                            current_items.append(row.values)
                        invoice.reviewed_at = timezone.now() if request.POST.get("action") == "review" else None
                        update_derived_values(invoice, [c.value_key or c.key for c in summary_columns if c.key in form.changed_data])
                        merge_columns(invoice.values, invoice.provenance, [c for c in columns if c.dataset == "summary"])
                        invoice.findings = validate_invoice(invoice.values, current_items, columns)
                        invoice.save()
                if claimed:
                    messages.success(request, "Saved and marked reviewed." if invoice.reviewed_at else "Changes saved. Mark this invoice reviewed before export.")
                    return redirect(f"{reverse('workspace:detail', args=[batch.pk])}?document={selected.pk}")
                form.add_error(None, "This invoice changed in another tab. Reload before saving; your changes have not been applied.")
    elif request.method == "POST":
        return HttpResponseBadRequest("Extract this document before editing it.")
    for analysis in analyses:
        record = getattr(analysis, "invoice", None)
        analysis.has_invoice = bool(record)
        analysis.review_label = "Reviewed" if record and record.reviewed_at else "Needs review" if record else analysis.get_status_display()
        analysis.summary_cells = [record.values.get(column.key) for column in summary_columns] if record else []
    return render(request, "invoxcel/workspace.html", {
        "source_pages": range(1, (selected.page_count if selected else 1) + 1),
        "batch": batch, "analyses": analyses, "selected": selected, "invoice": invoice,
        "selected_position": selected_index + 1 if selected_index is not None else None,
        "previous_analysis": previous_analysis, "next_analysis": next_analysis,
        "azure_findings": azure_findings, "programmatic_findings": programmatic_findings,
        "form": form, "formset": formset, "summary_columns": summary_columns,
        "item_columns": item_columns, "columns": columns,
        "export_ready": bool(analyses) and any(getattr(a, "invoice", None) for a in analyses) and all(a.invoice.reviewed_at for a in analyses if getattr(a, "invoice", None)),
        "failed_count": sum(a.status == DocumentAnalysis.Status.FAILED for a in analyses),
    })


def _remaining_sources(provenance, changed_keys):
    return {key: value for key, value in provenance.items() if key not in changed_keys}


@login_required
@require_POST
def retry(request, pk, analysis_id):
    batch = get_user_batch(request.user, pk)
    get_object_or_404(DocumentAnalysis, batch=batch, pk=analysis_id, status=DocumentAnalysis.Status.FAILED)
    extract_batch(batch, analysis_id=analysis_id)
    return redirect(f"{reverse('workspace:detail', args=[pk])}?document={analysis_id}")


@login_required
@require_POST
def columns(request, pk):
    batch = get_user_batch(request.user, pk)
    selected = request.POST.getlist("columns")
    available = list(batch.columns.all())
    if not selected or not set(selected) <= {str(c.pk) for c in available}:
        return HttpResponseBadRequest("Select at least one column from this batch.")
    with transaction.atomic():
        if "missing_columns" in request.POST:
            if not batch.template_id:
                return HttpResponseBadRequest("Missing-column options apply only to batches with a template.")
            if request.POST["missing_columns"] not in ("keep", "hide"):
                return HttpResponseBadRequest("Choose a valid missing-column option.")
            batch.hide_empty_columns = request.POST["missing_columns"] == "hide"
            batch.save(update_fields=("hide_empty_columns", "updated_at"))
        for column in available:
            column.is_selected = str(column.pk) in selected
            column.save(update_fields=("is_selected",))
    return redirect("workspace:detail", pk=pk)


@login_required
@require_POST
def edit_column(request, pk, column_id):
    batch = get_user_batch(request.user, pk)
    column = get_object_or_404(BatchColumn, pk=column_id, batch=batch)
    action = request.POST.get("action")
    if action == "rename":
        label = request.POST.get("label", "").strip()
        if not label or len(label) > 120:
            return HttpResponseBadRequest("Use a column name between 1 and 120 characters.")
        if batch.columns.filter(dataset=column.dataset, label__iexact=label).exclude(pk=column.pk).exists():
            return HttpResponseBadRequest("A column in this dataset already uses that name.")
        column.value_key = column.value_key or matched_key(column, {})
        column.label = label
        column.save(update_fields=("label", "value_key"))
        messages.success(request, "Column renamed for this batch.")
    elif action == "delete":
        if batch.columns.count() == 1:
            return HttpResponseBadRequest("Keep at least one column in the batch.")
        column.delete()
        messages.success(request, "Column deleted from this batch's workspace and exports.")
    else:
        return HttpResponseBadRequest("Choose rename or delete.")
    return redirect("workspace:detail", pk=pk)


@login_required
@require_POST
def delete_row(request, pk, analysis_id):
    batch = get_user_batch(request.user, pk)
    analysis = get_object_or_404(DocumentAnalysis, pk=analysis_id, batch=batch)
    if analysis.status == DocumentAnalysis.Status.PROCESSING:
        return HttpResponseBadRequest("Wait for extraction to finish before deleting this row.")
    analysis.delete()
    messages.success(request, "Invoice row and its line items removed from this batch. The original upload is retained.")
    return redirect("workspace:detail", pk=pk)
