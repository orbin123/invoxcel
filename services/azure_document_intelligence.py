"""Bounded synchronous Azure REST adapter; no implicit resubmissions or add-ons."""
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import quote, urlsplit

import requests
from django.conf import settings
from pypdf import PdfReader

API_VERSION = "2024-11-30"
SUMMARY_FIELDS = {
    "InvoiceId": "invoice_number", "InvoiceDate": "invoice_date",
    "DueDate": "due_date", "PurchaseOrder": "po_number",
    "VendorName": "vendor_name", "VendorAddress": "vendor_address", "VendorTaxId": "vendor_gstin",
    "CustomerName": "customer_name", "CustomerTaxId": "customer_gstin",
    "SubTotal": "subtotal", "TotalTax": "tax_amount",
    "InvoiceTotal": "grand_total", "TotalDiscount": "discount",
    "ShippingCharges": "other_charges", "PaymentTerm": "payment_terms",
    "CGST": "cgst", "SGST": "sgst", "IGST": "igst",
}
ITEM_FIELDS = {
    "Description": "description", "Quantity": "quantity", "UnitPrice": "unit_price",
    "TaxRate": "tax_rate", "Tax": "tax_amount", "Amount": "amount",
    "ProductCode": "product_code", "Unit": "unit",
}


class ExtractionError(Exception):
    def __init__(self, message, raw_response="", metadata=None):
        super().__init__(message)
        self.raw_response = raw_response
        self.metadata = metadata or {}


@dataclass
class ExtractionResult:
    raw_response: str
    metadata: dict
    summary: dict
    line_items: list
    provenance: dict
    page_count: int


def _field_value(field):
    if not isinstance(field, dict):
        return None
    for key in ("valueString", "valueDate", "valueNumber", "valueInteger", "valueBoolean"):
        if key in field:
            return field[key]
    currency = field.get("valueCurrency")
    if isinstance(currency, dict):
        return currency.get("amount")
    return field.get("content")


def _map_fields(fields, mapping):
    values, provenance = {}, {}
    mapping = dict(mapping)
    for source, field in fields.items():
        if source not in mapping and isinstance(field, dict) and field.get("type") not in ("array", "object"):
            key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", source)
            key = re.sub(r"[^a-z0-9_]+", "_", key.lower()).strip("_")[:80]
            if key and key not in mapping.values():
                mapping[source] = key
    for source, key in mapping.items():
        field = fields.get(source, {})
        values[key] = _field_value(field)
        if isinstance(field, dict) and field:
            provenance[key] = {name: field[name] for name in
                               ("confidence", "boundingRegions", "spans", "content", "type") if name in field}
    return values, provenance


def map_response(raw_response, metadata=None):
    metadata = dict(metadata or {})
    try:
        payload = json.loads(raw_response, parse_float=Decimal)
        result = payload["analyzeResult"]
        documents = result.get("documents", [])
        if not isinstance(documents, list) or len(documents) != 1:
            raise ExtractionError(
                "Azure returned no single usable invoice. Upload one invoice per file.",
                raw_response, metadata,
            )
        document = documents[0]
        fields = document["fields"]
        if document.get("docType") != "invoice" or not isinstance(fields, dict) or not fields:
            raise ExtractionError("Azure returned no usable invoice fields. Try a clearer invoice.", raw_response, metadata)
        summary, summary_sources = _map_fields(fields, SUMMARY_FIELDS)
        # A currency symbol alone is ambiguous: use only Azure's explicit ISO code.
        summary["currency"] = None
        for source in ("InvoiceTotal", "SubTotal", "AmountDue"):
            field = fields.get(source, {})
            currency = field.get("valueCurrency", {}) if isinstance(field, dict) else {}
            if isinstance(currency, dict) and currency.get("currencyCode"):
                summary["currency"] = currency["currencyCode"]
                summary_sources["currency"] = {k: v for k, v in field.items() if k in ("confidence", "spans", "boundingRegions")}
                break
        items, item_sources = [], []
        for item in fields.get("Items", {}).get("valueArray", []):
            values, sources = _map_fields(item["valueObject"], ITEM_FIELDS)
            items.append(values)
            item_sources.append(sources)
        if not any(value is not None for value in summary.values()) and not items:
            raise ExtractionError("Azure returned no mapped invoice data. Try a clearer invoice.", raw_response, metadata)
        types = {"currency": "currency", "number": "number", "integer": "number", "date": "date", "boolean": "boolean"}
        metadata["summary_types"] = {key: types.get(source.get("type"), "text") for key, source in summary_sources.items()}
        metadata["item_types"] = {key: types.get(source.get("type"), "text") for sources in item_sources for key, source in sources.items()}
        metadata.update({"model_id": result.get("modelId"), "api_version": result.get("apiVersion"), "document_type": document.get("docType"), "status": payload.get("status")})
        # Confidence is not financial data; JSON storage accepts ordinary floats here.
        provenance = json.loads(json.dumps({"summary": summary_sources, "line_items": item_sources}, default=float))
        return ExtractionResult(raw_response, metadata, summary, items, provenance, len(result.get("pages", [])))
    except ExtractionError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ExtractionError("Azure returned an unexpected response. Retry extraction.", raw_response, metadata) from exc


class AzureInvoiceClient:
    provider = "azure_document_intelligence"

    def __init__(self):
        self.model = settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL

    def _configuration(self):
        endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT.rstrip("/")
        key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
        if not endpoint or not key:
            raise ExtractionError("Configure AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY in .env, then retry.")
        if urlsplit(endpoint).scheme != "https":
            raise ExtractionError("Azure endpoint must use HTTPS. Check .env, then retry.")
        return endpoint, key

    def check_connection(self):
        """Authenticate with resource info without submitting document bytes."""
        endpoint, key = self._configuration()
        try:
            with requests.Session() as session:
                session.headers.update({"Ocp-Apim-Subscription-Key": key})
                response = session.get(
                    f"{endpoint}/documentintelligence/info",
                    params={"api-version": API_VERSION}, timeout=(10, 20),
                    allow_redirects=False,
                )
                self._check_status(response, 200)
        except requests.RequestException as exc:
            raise ExtractionError("Could not reach Azure. Check the connection and retry.") from exc

    def extract(self, document):
        endpoint, key = self._configuration()
        if document.size_bytes > settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES:
            raise ExtractionError(f"This file exceeds the configured Azure size limit ({settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES // (1024 * 1024)} MB). Upload a smaller file.")
        try:
            with document.file.open("rb") as source:
                if document.content_type == "application/pdf":
                    try:
                        reader = PdfReader(source)
                        if reader.is_encrypted:
                            raise ValueError("encrypted")
                        page_count = len(reader.pages)
                    except Exception as exc:
                        raise ExtractionError("This PDF cannot be read or is password protected. Upload an unlocked PDF.") from exc
                    if page_count > settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES:
                        raise ExtractionError(f"This PDF exceeds the configured Azure page limit ({settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES} pages). Split it into supported files before uploading.")
                    source.seek(0)
                if document.content_type == "image/tiff":
                    from PIL import Image
                    try:
                        with Image.open(source) as image:
                            if image.n_frames > settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES:
                                raise ExtractionError(f"This TIFF exceeds the configured limit of {settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES} pages.")
                    except (OSError, ValueError) as exc:
                        raise ExtractionError("This TIFF cannot be read. Upload a readable image.") from exc
                    source.seek(0)
        except OSError as exc:
            raise ExtractionError("The stored source file is unavailable. Upload it again.") from exc
        url = f"{endpoint}/documentintelligence/documentModels/{quote(self.model, safe='')}:analyze?api-version={API_VERSION}"
        metadata = {"api_version": API_VERSION, "model_id": self.model}
        deadline = time.monotonic() + settings.AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT
        try:
            with document.file.open("rb") as content, requests.Session() as session:
                session.headers.update({"Ocp-Apim-Subscription-Key": key})
                response = session.post(url, data=content, headers={"Content-Type": document.content_type}, timeout=(10, 30), allow_redirects=False)
                self._check_status(response, 202, metadata)
                operation_url = response.headers.get("Operation-Location", "")
                parsed = urlsplit(operation_url)
                if parsed.scheme != "https" or parsed.netloc != urlsplit(endpoint).netloc:
                    raise ExtractionError("Azure returned an invalid operation address. Check the endpoint configuration.")
                metadata["request_id"] = response.headers.get("apim-request-id", "")
                metadata["operation_id"] = parsed.path.rsplit("/", 1)[-1]
                while time.monotonic() < deadline:
                    time.sleep(min(2, max(0, deadline - time.monotonic())))
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    response = session.get(operation_url, timeout=min(20, remaining), allow_redirects=False)
                    self._check_status(response, 200, metadata)
                    payload = response.json()
                    if payload.get("status") == "succeeded":
                        return map_response(response.text, metadata)
                    if payload.get("status") == "failed":
                        raise ExtractionError("Azure could not read this document. Try a clearer or unlocked invoice, then retry.", response.text, metadata)
                raise ExtractionError("Azure extraction timed out. The source is saved; retry when the service is available.", metadata=metadata)
        except (requests.RequestException, ValueError, AttributeError) as exc:
            # Never surface request URLs, keys, response bodies or provider exception text.
            raise ExtractionError("Could not reach Azure or read its response. Check the connection and retry.", metadata=metadata) from exc

    @staticmethod
    def _check_status(response, expected, metadata=None):
        if response.status_code == expected:
            return
        messages = {
            401: "Azure authentication failed. Check that the subscription is active and the endpoint and key in .env belong to the same resource. Check environment overrides, then restart Django after configuration changes before retrying.",
            403: "Azure denied access. Check the resource key and network access.",
            429: "Azure's rate or page quota was reached. Wait before retrying, or check the resource quota.",
            400: "Azure rejected the file. Check that it is a readable, unlocked invoice.",
            404: "Azure resource or invoice model was not found. Check .env.",
            413: "Azure rejected the file size. Upload a smaller file.",
        }
        details = dict(metadata or {})
        details["http_status"] = response.status_code
        # Provider data is untrusted: retain only short identifiers, never messages.
        try:
            payload = response.json()
            error = payload.get("error", payload) if isinstance(payload, dict) else {}
            code = error.get("code", error.get("statusCode")) if isinstance(error, dict) else None
        except ValueError:
            code = None
        for name, value in (("error_code", code), ("request_id", response.headers.get("apim-request-id"))):
            if isinstance(value, (str, int)):
                value = str(value)
                key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
                if re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value) and not (key and key in value):
                    details[name] = value
        raise ExtractionError(messages.get(response.status_code, "Azure is unavailable. Your source is saved; retry later."), metadata=details)
