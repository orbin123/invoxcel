from pathlib import Path

from django import forms
from django.conf import settings

from apps.accounts.ownership import templates_for_user
from apps.templates.models import Template


MAX_UPLOAD_FILES = 10
ALLOWED_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]
        return [single_file_clean(data, initial)]

class InvoiceUploadForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=Template.objects.none(),
        empty_label="None — automatically detect columns",
        required=False,
        label="Template",
    )
    document = MultipleFileField(
        label="Invoice document",
        widget=MultipleFileInput(
            attrs={
                "accept": ".pdf,.jpg,.jpeg,.png,.bmp,.tif,.tiff",
                "class": "file-input",
                "multiple": True,
            }
        ),
    )
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.max_upload_mb = settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES // (1024 * 1024)
        self.max_pages = settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES
        self.timeout = settings.AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT
        queryset = (
            templates_for_user(user).order_by("-is_standard", "name")
            if user and user.is_authenticated
            else Template.objects.filter(is_standard=True).order_by("name")
        )
        self.fields["template"].initial = queryset.filter(is_standard=True).first()
        self.fields["template"].queryset = queryset

    def clean_document(self):
        documents = self.cleaned_data["document"]
        if not isinstance(documents, (list, tuple)):
            documents = [documents]

        if len(documents) > MAX_UPLOAD_FILES:
            raise forms.ValidationError("Choose no more than 10 files at a time.")
        if any(document.size > settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES for document in documents):
            raise forms.ValidationError(f"Choose a file that is {self.max_upload_mb} MB or smaller.")

        for document in documents:
            extension = Path(document.name).suffix.lower()

            if extension not in ALLOWED_FILE_TYPES:
                raise forms.ValidationError("Choose a PDF, JPG, PNG, BMP, or TIFF file.")

            header = document.read(1024)
            document.seek(0)
            signature_matches = {
                ".pdf": b"%PDF-" in header,
                ".jpg": header.startswith(b"\xff\xd8\xff"),
                ".jpeg": header.startswith(b"\xff\xd8\xff"),
                ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
                ".bmp": header.startswith(b"BM"),
                ".tif": header.startswith((b"II*\x00", b"MM\x00*")),
                ".tiff": header.startswith((b"II*\x00", b"MM\x00*")),
            }
            if not signature_matches[extension]:
                raise forms.ValidationError(
                    "The file contents do not match its PDF, JPG, PNG, BMP, or TIFF extension."
                )

            document.detected_content_type = ALLOWED_FILE_TYPES[extension]
        return documents
