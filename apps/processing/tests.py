import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.core.files.base import ContentFile

from apps.invoices.validation import SUMMARY_TYPES, normalize_values, validate_invoice
from services.azure_document_intelligence import AzureInvoiceClient, ExtractionError, map_response

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/azure_invoice.json"


class ExtractionTests(SimpleTestCase):
    def test_maps_invoice_and_line_items_with_provenance_and_exact_decimals(self):
        result = map_response(FIXTURE.read_text())
        values, errors = normalize_values(result.summary, SUMMARY_TYPES)
        self.assertEqual(values["grand_total"], "110.11")
        self.assertEqual(values["subtotal"], "100.10")
        self.assertEqual(values["currency"], "USD")
        self.assertEqual(values["invoice_date"], "2026-09-15")
        self.assertIsNone(values["vendor_gstin"])
        self.assertEqual(len(result.line_items), 1)
        self.assertEqual(result.provenance["summary"]["invoice_number"]["boundingRegions"][0]["pageNumber"], 1)
        self.assertFalse(errors)

    def test_malformed_and_multiple_document_responses_fail_with_raw_payload(self):
        for raw in ('[]', 'not json', '{"analyzeResult":{"documents":[]}}', '{"analyzeResult":{"documents":[{},{}]}}'):
            with self.subTest(raw=raw), self.assertRaises(ExtractionError) as error:
                map_response(raw)
            self.assertEqual(error.exception.raw_response, raw)

    def test_normalization_rejects_nonfinite_amounts_and_invalid_dates(self):
        values, findings = normalize_values({"grand_total": "NaN", "invoice_date": "2026-02-30", "taxable_amount": {"unsafe": 12}}, SUMMARY_TYPES)
        self.assertEqual(values, {"grand_total": None, "invoice_date": None, "taxable_amount": None})
        self.assertEqual(len(findings), 3)

    def test_validation_flags_totals_currency_and_due_date(self):
        values = {"invoice_number": "A", "vendor_name": "B", "invoice_date": "2026-09-15", "due_date": "2026-09-01", "currency": "XYZ", "taxable_amount": "100", "tax_amount": "10", "grand_total": "125"}
        self.assertEqual({f["field"] for f in validate_invoice(values, [], [])}, {"grand_total", "due_date", "currency"})

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://example.cognitiveservices.azure.com", AZURE_DOCUMENT_INTELLIGENCE_KEY="secret-test-key")
    @patch("services.azure_document_intelligence.time.sleep")
    @patch("services.azure_document_intelligence.requests.Session")
    def test_rest_submission_polls_once_and_never_sends_template_or_instructions(self, session_class, sleep):
        session = session_class.return_value.__enter__.return_value
        session.post.return_value = Mock(status_code=202, headers={"Operation-Location": "https://example.cognitiveservices.azure.com/results/test-id"})
        session.get.return_value = Mock(status_code=200, text=FIXTURE.read_text())
        session.get.return_value.json.return_value = {"status": "succeeded"}
        document = SimpleNamespace(file=ContentFile(b"image", name="invoice.png"), content_type="image/png", size_bytes=5)
        result = AzureInvoiceClient().extract(document)
        self.assertEqual(result.summary["invoice_number"], "DEMO-001")
        self.assertEqual(session.post.call_count, 1)
        self.assertIn("api-version=2024-11-30", session.post.call_args.args[0])
        self.assertIs(session.post.call_args.kwargs["data"], document.file)

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://example.cognitiveservices.azure.com", AZURE_DOCUMENT_INTELLIGENCE_KEY="secret-test-key")
    @patch("services.azure_document_intelligence.requests.Session")
    def test_provider_errors_are_actionable_and_do_not_expose_response_or_key(self, session_class):
        session = session_class.return_value.__enter__.return_value
        session.post.return_value = Mock(status_code=429, text="secret-test-key")
        document = SimpleNamespace(file=ContentFile(b"image"), content_type="image/png", size_bytes=5)
        with self.assertRaisesMessage(ExtractionError, "quota") as error:
            AzureInvoiceClient().extract(document)
        self.assertNotIn("secret-test-key", str(error.exception))
        session.post.assert_called_once()
        session.get.assert_not_called()

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://example.cognitiveservices.azure.com", AZURE_DOCUMENT_INTELLIGENCE_KEY="secret-test-key", AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT=0)
    @patch("services.azure_document_intelligence.requests.Session")
    def test_timeout_is_bounded(self, session_class):
        session = session_class.return_value.__enter__.return_value
        session.post.return_value = Mock(status_code=202, headers={"Operation-Location": "https://example.cognitiveservices.azure.com/results/test-id"})
        document = SimpleNamespace(file=ContentFile(b"image"), content_type="image/png", size_bytes=5)
        with self.assertRaisesMessage(ExtractionError, "timed out"):
            AzureInvoiceClient().extract(document)
        session.get.assert_not_called()

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://example.cognitiveservices.azure.com", AZURE_DOCUMENT_INTELLIGENCE_KEY="secret-test-key")
    @patch("services.azure_document_intelligence.requests.Session")
    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES=2)
    def test_free_tier_rejects_more_than_two_pages_without_a_provider_call(self, session_class):
        from io import BytesIO
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=100, height=100)
        output = BytesIO()
        writer.write(output)
        document = SimpleNamespace(file=ContentFile(output.getvalue()), content_type="application/pdf", size_bytes=len(output.getvalue()))
        with self.assertRaisesMessage(ExtractionError, "2 pages"):
            AzureInvoiceClient().extract(document)
        session_class.assert_not_called()

    @override_settings(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://example.cognitiveservices.azure.com", AZURE_DOCUMENT_INTELLIGENCE_KEY="secret-test-key", AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES=2000, AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES=524288000)
    @patch("services.azure_document_intelligence.time.sleep")
    @patch("services.azure_document_intelligence.requests.Session")
    def test_s0_accepts_more_than_two_pages_and_streams_upload(self, session_class, sleep):
        from io import BytesIO
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=100, height=100)
        output = BytesIO()
        writer.write(output)
        document = SimpleNamespace(file=ContentFile(output.getvalue()), content_type="application/pdf", size_bytes=len(output.getvalue()))
        session = session_class.return_value.__enter__.return_value
        uploaded = []
        def submit(*args, **kwargs):
            uploaded.append(kwargs["data"].read())
            return Mock(status_code=202, headers={"Operation-Location": "https://example.cognitiveservices.azure.com/results/test-id"})
        session.post.side_effect = submit
        session.get.return_value = Mock(status_code=200, text=FIXTURE.read_text())
        session.get.return_value.json.return_value = {"status": "succeeded"}
        AzureInvoiceClient().extract(document)
        self.assertEqual(uploaded, [output.getvalue()])
        session.post.assert_called_once()
