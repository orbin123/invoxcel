from django.db import migrations


COLUMNS = (
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

def update_standard(apps, schema_editor):
    Template = apps.get_model("templates", "Template")
    Column = apps.get_model("templates", "TemplateColumn")
    for template in Template.objects.filter(is_standard=True):
        template.columns.filter(dataset="summary").exclude(key__in=[c[0] for c in COLUMNS]).delete()
        for position, (key, label, kind) in enumerate(COLUMNS):
            Column.objects.update_or_create(
                template=template, dataset="summary", key=key,
                defaults={"label": label, "data_type": kind, "position": position,
                          "is_custom": False, "is_required": key in ("invoice_number", "vendor_name", "grand_total")},
            )


class Migration(migrations.Migration):
    dependencies = [("templates", "0003_default_azure_columns")]
    operations = [migrations.RunPython(update_standard, migrations.RunPython.noop)]
