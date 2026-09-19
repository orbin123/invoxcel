"""Provider-independent, deterministic normalization. Decimal values persist as strings."""
from datetime import date
from decimal import Decimal, InvalidOperation

import pycountry

from apps.templates.models import SUMMARY_COLUMNS, LINE_ITEM_COLUMNS

SUMMARY_TYPES = {key: kind for key, _, kind in SUMMARY_COLUMNS}
ITEM_TYPES = {key: kind for key, _, kind in LINE_ITEM_COLUMNS}


def normalize_value(value, kind):
    if value is None or value == "":
        return None
    if isinstance(value, bool) and kind == "boolean":
        return value
    if isinstance(value, (dict, list, bool)):
        raise ValueError("Enter a valid value.")
    text = str(value).strip()
    if not text:
        return None
    if kind in ("number", "currency"):
        try:
            number = Decimal(text)
            if not number.is_finite() or abs(number) >= Decimal("1e18") or number.as_tuple().exponent < -8:
                raise InvalidOperation
            return format(number, "f")
        except InvalidOperation as exc:
            raise ValueError("Enter a finite number with at most 8 decimal places (no currency symbols or separators).") from exc
    if kind == "date":
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError as exc:
            raise ValueError("Use a valid date in YYYY-MM-DD format.") from exc
    if kind == "boolean":
        if text.lower() not in ("true", "false"):
            raise ValueError("Choose true or false.")
        return text.lower() == "true"
    if len(text) > 4000:
        raise ValueError("Use at most 4,000 characters.")
    return text


def normalize_values(values, types):
    normalized, findings = {}, []
    for key, value in values.items():
        try:
            normalized[key] = normalize_value(value, types.get(key, "text"))
        except ValueError:
            normalized[key] = None
            findings.append({"field": key, "message": "The extracted value could not be parsed. Check the source and enter it manually."})
    return normalized, findings


def validate_invoice(values, items, columns):
    findings = []
    def warn(field, message):
        findings.append({"field": field, "message": message})
    for key in ("invoice_number", "vendor_name", "grand_total"):
        if values.get(key) in (None, ""):
            warn(key, f"{key.replace('_', ' ').capitalize()} is missing. Check the source.")
    for column in columns:
        rows = [values] if column.dataset == "summary" else items
        if getattr(column, "is_required", False):
            for index, row in enumerate(rows):
                if row.get(column.key) in (None, ""):
                    field = column.key if column.dataset == "summary" else f"line_items.{index}.{column.key}"
                    warn(field, f"{column.label} is required by this output template.")
    currency = values.get("currency")
    if not currency:
        warn("currency", "Currency is missing; confirm it from the source.")
    elif pycountry.currencies.get(alpha_3=currency) is None:
        warn("currency", "Use a recognized three-letter currency code, such as INR or USD.")
    if values.get("invoice_date") and values.get("due_date") and values["due_date"] < values["invoice_date"]:
        warn("due_date", "Due date is earlier than the invoice date.")
    difference = values.get("total_difference")
    if difference is not None and abs(Decimal(difference)) > Decimal("0.02"):
        warn("grand_total", "Taxable amount + tax + other charges does not match the extracted grand total.")
    elif "calculated_total" not in values and values.get("taxable_amount") is not None and values.get("grand_total") is not None and values.get("tax_amount") is not None:
        # Existing batches stored Azure's subtotal under taxable_amount.
        expected = Decimal(values["taxable_amount"]) + Decimal(values["tax_amount"]) - Decimal(values.get("discount") or "0") + Decimal(values.get("shipping") or "0")
        if abs(expected - Decimal(values["grand_total"])) > Decimal("0.02"):
            warn("grand_total", "Subtotal + tax − discount + shipping does not match the total.")
    for index, item in enumerate(items):
        if all(item.get(key) is not None for key in ("quantity", "unit_price", "amount")):
            if abs(Decimal(item["quantity"]) * Decimal(item["unit_price"]) - Decimal(item["amount"])) > Decimal("0.02"):
                warn(f"line_items.{index}.amount", f"Line {index + 1}: quantity × unit price does not match amount; check discounts or tax on the source.")
    return findings


def confidence_findings(provenance):
    findings = []
    for field, source in provenance.items():
        confidence = source.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < 0.8:
            findings.append({"field": field, "message": "Azure reported low confidence. Compare this value with the source."})
    return findings


def update_derived_values(invoice, changed_keys=None):
    """Recalculate from current normalized values; absent tax is not invented."""
    values = invoice.values
    if values.get("subtotal") is not None and (changed_keys is None or {"subtotal", "discount"} & set(changed_keys)):
        values["taxable_amount"] = format(Decimal(values["subtotal"]) - Decimal(values.get("discount") or "0"), "f")
    tax_parts = [values.get(key) for key in ("cgst", "sgst", "igst")]
    tax = sum(Decimal(v) for v in tax_parts if v is not None) if any(v is not None for v in tax_parts) else values.get("tax_amount")
    calculated = None
    if values.get("taxable_amount") is not None and tax is not None:
        calculated = Decimal(values["taxable_amount"]) + Decimal(tax) + Decimal(values.get("other_charges") or values.get("shipping") or "0")
    values["calculated_total"] = format(calculated, "f") if calculated is not None else None
    values["total_difference"] = format(calculated - Decimal(values["grand_total"]), "f") if calculated is not None and values.get("grand_total") is not None else None
    values["invoice_id"] = f"INV{invoice.analysis.document_id:03d}"
    values["source_file"] = invoice.analysis.document.original_filename
    values["verification_status"] = "Approved" if invoice.reviewed_at else "Review Required"
    confidences = [Decimal(str(source["confidence"])) for key, source in invoice.provenance.items()
                   if not key.startswith("custom_") and isinstance(source.get("confidence"), (int, float)) and 0 <= source["confidence"] <= 1]
    values["confidence"] = format((sum(confidences) / len(confidences) * 100).quantize(Decimal("0.01")), "f") if confidences else None


def review_findings(invoice, columns):
    """Recheck saved data independently of column visibility and extraction time."""
    items = list(invoice.line_items.all())
    azure = confidence_findings(invoice.provenance)
    for index, item in enumerate(items):
        azure.extend({"field": f"line_items.{index}.{f['field']}", "message": f["message"]}
                     for f in confidence_findings(item.provenance))
    programmatic = validate_invoice(invoice.values, [item.values for item in items], columns)
    for finding in invoice.findings:
        if finding["message"].startswith("The extracted value"):
            parts = finding["field"].split(".")
            row = invoice.values
            if len(parts) == 3 and parts[0] == "line_items":
                index = int(parts[1])
                row = items[index].values if index < len(items) else {}
            if row.get(parts[-1]) in (None, ""):
                programmatic.append(finding)
    if invoice.analysis.batch.template_id:
        for column in columns:
            rows = [invoice.values] if column.dataset == "summary" else [item.values for item in items]
            if column.dataset == "line_item" and not rows:
                programmatic.append({"field": column.key, "message": f"{column.label}: no line items to review for this template column."})
            for index, row in enumerate(rows):
                if row.get(column.key) in (None, "") and not column.is_required:
                    field = column.key if column.dataset == "summary" else f"line_items.{index}.{column.key}"
                    programmatic.append({"field": field, "message": f"{column.label} is missing from the saved output. Check the source and fill it in if applicable."})
    return azure, list({(f["field"], f["message"]): f for f in programmatic}.values())
