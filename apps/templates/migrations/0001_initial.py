import django.db.models.deletion
from django.db import migrations, models


def create_standard_invoice_template(apps, schema_editor):
    Template = apps.get_model("templates", "Template")
    TemplateColumn = apps.get_model("templates", "TemplateColumn")
    template, _ = Template.objects.get_or_create(
        name="Standard Invoice",
        defaults={"is_standard": True},
    )
    columns = [
        ("summary", "invoice_number", "Invoice number", "text"),
        ("summary", "invoice_date", "Invoice date", "date"),
        ("summary", "vendor_name", "Vendor name", "text"),
        ("summary", "vendor_gstin", "Vendor GSTIN", "text"),
        ("summary", "customer_name", "Customer name", "text"),
        ("summary", "customer_gstin", "Customer GSTIN", "text"),
        ("summary", "currency", "Currency", "text"),
        ("summary", "taxable_amount", "Taxable amount", "currency"),
        ("summary", "cgst", "CGST", "currency"),
        ("summary", "sgst", "SGST", "currency"),
        ("summary", "igst", "IGST", "currency"),
        ("summary", "grand_total", "Grand total", "currency"),
        ("line_item", "description", "Description", "text"),
        ("line_item", "quantity", "Quantity", "number"),
        ("line_item", "unit_price", "Unit price", "currency"),
        ("line_item", "tax_amount", "Tax amount", "currency"),
        ("line_item", "amount", "Amount", "currency"),
    ]
    TemplateColumn.objects.bulk_create(
        [
            TemplateColumn(
                template=template,
                dataset=dataset,
                key=key,
                label=label,
                data_type=data_type,
                position=position,
            )
            for position, (dataset, key, label, data_type) in enumerate(columns)
        ]
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Template",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("is_standard", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-is_standard", "name")},
        ),
        migrations.CreateModel(
            name="TemplateColumn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dataset", models.CharField(choices=[("summary", "Summary"), ("line_item", "Line items")], max_length=16)),
                ("key", models.SlugField(max_length=80)),
                ("label", models.CharField(max_length=120)),
                ("data_type", models.CharField(choices=[("text", "Text"), ("number", "Number"), ("currency", "Currency"), ("date", "Date"), ("boolean", "Boolean")], max_length=16)),
                ("position", models.PositiveSmallIntegerField()),
                ("is_custom", models.BooleanField(default=False)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="columns", to="templates.template")),
            ],
            options={"ordering": ("dataset", "position")},
        ),
        migrations.AddConstraint(
            model_name="templatecolumn",
            constraint=models.UniqueConstraint(
                fields=("template", "dataset", "key"),
                name="unique_template_column_key",
            ),
        ),
        migrations.RunPython(create_standard_invoice_template, migrations.RunPython.noop),
    ]
