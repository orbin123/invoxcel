from django.db import migrations


def update_default(apps, schema_editor):
    Template = apps.get_model("templates", "Template")
    Column = apps.get_model("templates", "TemplateColumn")
    template = Template.objects.filter(is_standard=True).first()
    if not template:
        return
    # Keep existing stable keys and all custom templates. General invoice output
    # does not assume the presence of India GST component taxes.
    columns = [
        ("invoice_number", "Invoice number", "text"), ("invoice_date", "Invoice date", "date"),
        ("due_date", "Due date", "date"), ("vendor_name", "Vendor name", "text"),
        ("vendor_gstin", "Vendor tax ID", "text"), ("customer_name", "Customer name", "text"),
        ("customer_gstin", "Customer tax ID", "text"), ("currency", "Currency", "text"),
        ("taxable_amount", "Subtotal", "currency"), ("discount", "Discount", "currency"),
        ("shipping", "Shipping", "currency"), ("tax_amount", "Total tax", "currency"),
        ("grand_total", "Total", "currency"), ("payment_terms", "Payment terms", "text"),
        ("notes", "Notes", "text"),
    ]
    Column.objects.filter(template=template, dataset="summary", key__in=["cgst", "sgst", "igst"]).delete()
    for position, (key, label, kind) in enumerate(columns):
        Column.objects.update_or_create(template=template, dataset="summary", key=key, defaults={"label": label, "data_type": kind, "position": position, "is_required": key in ("invoice_number", "vendor_name", "grand_total")})


class Migration(migrations.Migration):
    dependencies = [("templates", "0002_templatecolumn_is_required")]
    operations = [migrations.RunPython(update_default, migrations.RunPython.noop)]
