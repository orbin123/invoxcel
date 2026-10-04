import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles import finders
from django.test import override_settings
from django.urls import reverse

from tests.base import AuthenticatedTestCase

from .forms import MAX_UPLOAD_FILES
from .models import UploadedDocument
from apps.processing.models import AnalysisBatch, DocumentAnalysis
from apps.templates.models import Template


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="", AZURE_DOCUMENT_INTELLIGENCE_KEY="")
class InvoiceUploadTests(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.standard_template = Template.objects.get(is_standard=True)

    def test_home_links_the_official_favicon(self):
        response = self.client.get(reverse("uploads:upload"))

        self.assertContains(
            response,
            '<link rel="icon" href="/static/invoxcel/favicon.svg" type="image/svg+xml">',
            html=True,
        )
        self.assertIsNotNone(finders.find("invoxcel/favicon.svg"))

    def test_upload_defaults_to_automatic_columns_with_templates_available(self):
        response = self.client.get(reverse("uploads:upload"))
        self.assertContains(response, '<option value="" selected>None — automatically detect columns</option>', html=True)
        self.assertIsNone(response.context["upload_form"]["template"].value())
        self.assertContains(response, self.standard_template.name)
        self.client.logout()
        response = self.client.get(reverse("uploads:upload"))
        self.assertIsNone(response.context["upload_form"]["template"].value())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_valid_pdf_is_saved_and_redirects_to_analysis(self):
        uploaded = SimpleUploadedFile(
            "supplier invoice.pdf",
            b"%PDF-1.4\n%%EOF",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("uploads:upload"),
            {"document": uploaded, "template": self.standard_template.pk},
        )

        document = UploadedDocument.objects.get()
        batch = AnalysisBatch.objects.get()
        self.assertRedirects(
            response, reverse("workspace:detail", args=[batch.pk])
        )
        self.assertEqual(document.original_filename, "supplier invoice.pdf")
        self.assertEqual(document.content_type, "application/pdf")
        self.assertEqual(document.size_bytes, 14)
        self.assertEqual(document.status, UploadedDocument.Status.FAILED)
        self.assertEqual(document.template, self.standard_template)
        self.assertNotIn("supplier invoice", document.file.name)
        self.assertRegex(
            document.file.name,
            rf"^users/{self.user.pk}/invoices/\d{{8}}T\d{{12}}Z-[0-9a-f]{{8}}/document\.pdf$",
        )
        self.assertEqual(document.user, self.user)
        self.assertTrue(Path(document.file.path).exists())

        analysis = self.client.get(response.url)
        self.assertContains(analysis, "Review your invoices")
        self.assertContains(analysis, "Retry extraction")
        self.assertContains(analysis, "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")

        detail = self.client.get(reverse("uploads:detail", args=[document.pk]))
        source_url = reverse("uploads:source", args=[document.pk])
        self.assertContains(detail, "supplier invoice.pdf")
        self.assertContains(detail, source_url)
        self.assertNotContains(detail, document.file.url)
        self.assertContains(detail, 'type="application/pdf"')

    def test_valid_images_are_displayed_on_detail_page(self):
        image_types = (
            ("invoice.jpg", b"\xff\xd8\xffimage-data", "image/jpeg"),
            ("invoice.jpeg", b"\xff\xd8\xffimage-data", "image/jpeg"),
            ("invoice.png", b"\x89PNG\r\n\x1a\nimage-data", "image/png"),
        )

        for filename, contents, content_type in image_types:
            with self.subTest(filename=filename):
                uploaded = SimpleUploadedFile(filename, contents, content_type=content_type)
                response = self.client.post(
                    reverse("uploads:upload"),
                    {"document": uploaded, "template": self.standard_template.pk},
                )

                document = UploadedDocument.objects.latest("pk")
                detail = self.client.get(
                    reverse("uploads:detail", args=[document.pk])
                )
                self.assertContains(
                    detail,
                    f'<img src="{reverse("uploads:source", args=[document.pk])}"',
                )
                self.assertEqual(document.content_type, content_type)

    def test_multiple_files_are_saved(self):
        uploads = [
            SimpleUploadedFile("first.pdf", b"%PDF-1.4\n%%EOF"),
            SimpleUploadedFile("second.png", b"\x89PNG\r\n\x1a\nimage-data"),
        ]

        response = self.client.post(
            reverse("uploads:upload"),
            {"document": uploads, "template": self.standard_template.pk},
        )

        batch = AnalysisBatch.objects.get()
        self.assertRedirects(
            response, reverse("workspace:detail", args=[batch.pk])
        )
        self.assertEqual(UploadedDocument.objects.count(), 2)
        self.assertEqual(batch.document_analyses.count(), 2)
        self.assertEqual(
            set(UploadedDocument.objects.values_list("original_filename", flat=True)),
            {"first.pdf", "second.png"},
        )

    def test_uploaded_documents_use_the_template_selected_on_the_upload_page(self):
        custom_template = Template.objects.create(name="Expense import", user=self.user)
        uploaded = SimpleUploadedFile("expense.pdf", b"%PDF-1.4\n%%EOF")

        response = self.client.get(reverse("uploads:upload"))
        self.assertContains(response, custom_template.name)

        response = self.client.post(
            reverse("uploads:upload"),
            {"document": uploaded, "template": custom_template.pk},
        )

        document = UploadedDocument.objects.get()
        batch = AnalysisBatch.objects.get()
        self.assertRedirects(
            response, reverse("workspace:detail", args=[batch.pk])
        )
        self.assertEqual(document.template, custom_template)
        self.assertEqual(batch.template, custom_template)

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES=1024 * 1024)
    def test_limit_applies_per_file_not_to_combined_batch(self):
        uploads = [SimpleUploadedFile(f"{i}.pdf", b"%PDF-" + b"0" * 600000) for i in range(2)]
        response = self.client.post(reverse("uploads:upload"), {"document": uploads})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UploadedDocument.objects.count(), 2)

    def test_file_count_limit_bounds_analysis_requests(self):
        uploads = [
            SimpleUploadedFile(f"invoice-{index}.pdf", b"%PDF-1.4\n%%EOF")
            for index in range(MAX_UPLOAD_FILES + 1)
        ]

        response = self.client.post(
            reverse("uploads:upload"),
            {"document": uploads, "template": self.standard_template.pk},
        )

        self.assertContains(response, "Choose no more than 10 files at a time.")
        self.assertFalse(UploadedDocument.objects.exists())

    def test_unsupported_extension_is_rejected(self):
        uploaded = SimpleUploadedFile("invoice.txt", b"not an invoice")

        response = self.client.post(reverse("uploads:upload"), {"document": uploaded})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a PDF, JPG, PNG, BMP, or TIFF file.")
        self.assertFalse(UploadedDocument.objects.exists())

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES=1024 * 1024)
    def test_oversized_file_is_rejected(self):
        uploaded = SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-" + b"0" * (1024 * 1024),
            content_type="application/pdf",
        )

        response = self.client.post(reverse("uploads:upload"), {"document": uploaded})

        self.assertContains(response, "Choose a file that is 1 MB or smaller.")
        self.assertFalse(UploadedDocument.objects.exists())

    def test_file_with_mismatched_contents_is_rejected(self):
        uploaded = SimpleUploadedFile(
            "invoice.pdf", b"<html>not a pdf</html>", content_type="application/pdf"
        )

        response = self.client.post(reverse("uploads:upload"), {"document": uploaded})

        self.assertContains(response, "file contents do not match")
        self.assertFalse(UploadedDocument.objects.exists())

    def test_home_keeps_overview_and_sample_workspace_in_the_header(self):
        response = self.client.get(reverse("uploads:upload"))

        self.assertContains(response, "Overview")
        self.assertContains(response, "My batches")
        self.assertContains(response, "Templates")
        self.assertContains(response, self.standard_template.name)
        self.assertNotContains(response, "How it works")
        self.assertContains(response, "Extract invoices")
        self.assertNotContains(response, "Choose your columns")

    def test_home_collapses_batches_after_five_with_view_more(self):
        batches = [
            AnalysisBatch.objects.create(template=self.standard_template, user=self.user)
            for _ in range(6)
        ]

        response = self.client.get(reverse("uploads:upload"))

        self.assertContains(response, "View more")
        self.assertContains(response, "Batch 6")
        self.assertEqual(response.content.count(b'data-batch-extra hidden'), 1)

    def test_batch_numbers_are_sequential_per_user_and_used_in_labels(self):
        other_user = User.objects.create_user(username="other-batches@example.com")
        first = AnalysisBatch.objects.create(template=self.standard_template, user=self.user)
        second = AnalysisBatch.objects.create(template=self.standard_template, user=self.user)
        other_first = AnalysisBatch.objects.create(template=self.standard_template, user=other_user)

        self.assertEqual((first.number, second.number, other_first.number), (1, 2, 1))
        self.assertEqual(str(second), "Batch 2")
        response = self.client.get(reverse("workspace:detail", args=[second.pk]))
        self.assertContains(response, "Batch 2")

    def test_delete_batch_removes_records_and_source_files(self):
        batch = AnalysisBatch.objects.create(template=self.standard_template, user=self.user)
        document = UploadedDocument.objects.create(
            user=self.user,
            original_filename="delete-me.pdf",
            file=SimpleUploadedFile("delete-me.pdf", b"%PDF-1.4\n%%EOF"),
            content_type="application/pdf",
            size_bytes=14,
            template=self.standard_template,
        )
        DocumentAnalysis.objects.create(batch=batch, document=document)
        storage, file_name = document.file.storage, document.file.name

        delete_url = reverse("processing:delete_batch", args=[batch.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 405)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(delete_url)

        self.assertRedirects(response, reverse("uploads:upload") + "#batches")
        self.assertFalse(AnalysisBatch.objects.filter(pk=batch.pk).exists())
        self.assertFalse(UploadedDocument.objects.filter(pk=document.pk).exists())
        self.assertFalse(storage.exists(file_name))

    def test_unknown_document_returns_not_found(self):
        response = self.client.get(reverse("uploads:detail", args=[999]))
        self.assertEqual(response.status_code, 404)
