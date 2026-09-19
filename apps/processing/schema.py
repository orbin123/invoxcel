"""Match output labels to extracted fields without guessing missing values."""
import re

from apps.templates.models import SUMMARY_COLUMNS, LINE_ITEM_COLUMNS
from .models import BatchColumn

DERIVED_KEYS = {"invoice_id", "calculated_total", "total_difference", "confidence", "verification_status", "source_file"}


def normalized_name(name):
    return re.sub(r"[^\w]", "", name.casefold()).replace("_", "")


def matched_key(column, values):
    if column.value_key:
        return column.value_key
    definitions = SUMMARY_COLUMNS if column.dataset == "summary" else LINE_ITEM_COLUMNS
    if column.key in {key for key, _, _ in definitions}:
        return column.key
    aliases = {normalized_name(name): key for key, label, _ in definitions for name in (key, label)}
    if column.dataset == "summary":
        aliases.update({normalized_name(name): key for name, key in (
            ("Invoice number", "invoice_number"), ("PO number", "po_number"),
            ("Purchase order", "po_number"), ("Grand total", "grand_total"),
            ("Invoice total", "grand_total"), ("Vendor tax ID", "vendor_gstin"),
            ("Customer tax ID", "customer_gstin"),
        )})
    name = normalized_name(column.label)
    return aliases.get(name) or next((key for key in values if normalized_name(key) == name), column.key)


def merge_columns(values, provenance, columns):
    from apps.invoices.validation import normalize_value

    findings = []
    for column in columns:
        key = matched_key(column, values)
        updates = []
        if not column.value_key and key in values:
            column.value_key = key
            updates.append("value_key")
        if key != column.key:
            definitions = SUMMARY_COLUMNS if column.dataset == "summary" else LINE_ITEM_COLUMNS
            kind = next((kind for field, _, kind in definitions if field == key), column.data_type)
            if column.data_type != kind:
                column.data_type = kind
                updates.append("data_type")
        if updates:
            column.save(update_fields=updates)
        try:
            values[column.key] = normalize_value(values.get(key), column.data_type)
        except ValueError:
            values[column.key] = None
            findings.append({"field": column.key, "message": f"The extracted value does not match the type for {column.label}. Check the source."})
        if key != column.key and key in provenance:
            provenance[column.key] = provenance[key]
    return findings


def discover_columns(batch, values, dataset, types=None):
    definitions = {key: (label, kind) for key, label, kind in (SUMMARY_COLUMNS if dataset == "summary" else LINE_ITEM_COLUMNS)}
    position = batch.columns.filter(dataset=dataset).count()
    for key, value in values.items():
        if value is None or value == "" or key in DERIVED_KEYS:
            continue
        label, kind = definitions.get(key, (key.replace("_", " ").capitalize(), "text"))
        kind = (types or {}).get(key, kind)
        _, created = BatchColumn.objects.get_or_create(
            batch=batch, dataset=dataset, key=key,
            defaults={"label": label, "data_type": kind, "position": position,
                      "source": "custom", "is_selected": True, "fill_with_ai": False},
        )
        position += int(created)


def output_columns(batch, invoices):
    columns = [c for c in batch.columns.all() if c.is_selected]
    if batch.template_id and batch.hide_empty_columns:
        summary_rows = [i.values for i in invoices]
        item_rows = [item.values for i in invoices for item in i.line_items.all()]
        columns = [c for c in columns if any(row.get(c.key) not in (None, "") for row in (summary_rows if c.dataset == "summary" else item_rows))]
    return ([c for c in columns if c.dataset == "summary"], [c for c in columns if c.dataset == "line_item"])
