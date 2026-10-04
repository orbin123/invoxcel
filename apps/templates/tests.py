from django.urls import reverse

from tests.base import AuthenticatedTestCase

from .models import Template, TemplateColumn
from apps.uploads.models import UploadedDocument


class TemplateTests(AuthenticatedTestCase):
    def test_invalid_template_keeps_selections_and_custom_text(self):
        response = self.client.post(
            reverse("templates:create"),
            {
                "name": "Invalid fixture",
                "summary_columns": ["invoice_number"],
                "line_item_columns": ["description"],
                "custom_summary_columns": "Project code\nProject code",
                "custom_line_item_columns": "Cost centre",
            },
        )

        self.assertContains(response, "Each custom column name must be unique.")
        self.assertFalse(Template.objects.filter(name="Invalid fixture").exists())
        form = response.context["form"]
        self.assertEqual(form["summary_columns"].value(), ["invoice_number"])
        self.assertEqual(form["line_item_columns"].value(), ["description"])
        self.assertContains(response, "Project code\nProject code")
        self.assertContains(response, "Cost centre")

    def test_invalid_edit_leaves_saved_columns_intact(self):
        template = Template.objects.create(name="Saved fixture", user=self.user)
        column = TemplateColumn.objects.create(
            template=template,
            dataset=TemplateColumn.Dataset.SUMMARY,
            key="invoice_number",
            label="Invoice number",
            data_type=TemplateColumn.DataType.TEXT,
            position=0,
        )

        response = self.client.post(
            reverse("templates:edit", args=[template.pk]),
            {"name": "Unsaved fixture"},
        )

        self.assertContains(response, "Choose at least one summary or line item column.")
        template.refresh_from_db()
        self.assertEqual(template.name, "Saved fixture")
        self.assertEqual(list(template.columns.all()), [column])

    def test_standard_invoice_template_is_seeded_and_visible(self):
        template = Template.objects.get(name="Standard Invoice")

        self.assertTrue(template.is_standard)
        self.assertEqual(template.columns.filter(dataset="summary").count(), 25)
        self.assertEqual(template.columns.filter(dataset="line_item").count(), 5)

        response = self.client.get(reverse("templates:list"))
        self.assertContains(response, "Standard Invoice")
        self.assertContains(response, "Built in")

    def test_user_can_create_template_with_separate_datasets(self):
        response = self.client.post(
            reverse("templates:create"),
            {
                "name": "Expense import",
                "summary_columns": ["invoice_number", "vendor_name", "grand_total"],
                "line_item_columns": ["description", "amount"],
                "custom_summary_columns": "Project code",
                "custom_line_item_columns": "Cost centre",
            },
        )

        template = Template.objects.get(name="Expense import")
        self.assertRedirects(response, reverse("templates:list"))
        self.assertFalse(template.is_standard)
        self.assertEqual(
            list(
                template.columns.filter(dataset="summary").values_list(
                    "key", "data_type"
                )
            ),
            [
                ("invoice_number", "text"),
                ("vendor_name", "text"),
                ("grand_total", "currency"),
                ("custom_project_code", "text"),
            ],
        )
        self.assertEqual(
            list(
                template.columns.filter(dataset="line_item").values_list(
                    "key", "data_type"
                )
            ),
            [
                ("description", "text"),
                ("amount", "currency"),
                ("custom_cost_centre", "text"),
            ],
        )

    def test_user_can_edit_and_delete_a_template(self):
        template = Template.objects.create(name="Initial import", user=self.user)
        TemplateColumn.objects.create(
            template=template,
            dataset=TemplateColumn.Dataset.SUMMARY,
            key="invoice_number",
            label="Invoice number",
            data_type=TemplateColumn.DataType.TEXT,
            position=0,
        )

        response = self.client.post(
            reverse("templates:edit", args=[template.pk]),
            {
                "name": "Updated import",
                "summary_columns": ["vendor_name"],
                "line_item_columns": ["description"],
                "custom_summary_columns": "",
                "custom_line_item_columns": "",
            },
        )

        template.refresh_from_db()
        self.assertRedirects(response, reverse("templates:list"))
        self.assertEqual(template.name, "Updated import")
        self.assertEqual(
            list(template.columns.values_list("dataset", "key")),
            [("line_item", "description"), ("summary", "vendor_name")],
        )

        response = self.client.post(reverse("templates:delete", args=[template.pk]))
        self.assertRedirects(response, reverse("templates:list"))
        self.assertFalse(Template.objects.filter(pk=template.pk).exists())

    def test_standard_template_cannot_be_changed_or_deleted(self):
        template = Template.objects.get(is_standard=True)

        self.assertEqual(
            self.client.get(reverse("templates:edit", args=[template.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("templates:delete", args=[template.pk])).status_code,
            404,
        )

    def test_used_template_cannot_be_deleted(self):
        template = Template.objects.create(name="Used import", user=self.user)
        UploadedDocument.objects.create(
            user=self.user,
            original_filename="invoice.pdf",
            file="invoices/test/document.pdf",
            content_type="application/pdf",
            size_bytes=1,
            template=template,
        )

        response = self.client.post(reverse("templates:delete", args=[template.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Template.objects.filter(pk=template.pk).exists())
        self.assertContains(response, "cannot be deleted")
