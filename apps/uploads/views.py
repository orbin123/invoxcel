from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.shortcuts import redirect, render

from apps.accounts.ownership import batches_for_user, get_user_document
from apps.processing.models import AnalysisBatch, DocumentAnalysis
from apps.processing.services import extract_batch

from .forms import InvoiceUploadForm
from .models import UploadedDocument


def upload(request):
    if request.method == "POST" and not request.user.is_authenticated:
        messages.info(request, "Sign in to upload and extract invoices.")
        return redirect(f"{reverse('accounts:signin')}?next=/")

    form = InvoiceUploadForm(
        request.POST or None,
        request.FILES or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            batch = AnalysisBatch.objects.create(
                user=request.user,
                template=form.cleaned_data["template"],
            )
            for uploaded_file in form.cleaned_data["document"]:
                document = UploadedDocument.objects.create(
                    user=request.user,
                    original_filename=Path(uploaded_file.name).name[:255],
                    file=uploaded_file,
                    content_type=uploaded_file.detected_content_type,
                    size_bytes=uploaded_file.size,
                    template=batch.template,
                )
                DocumentAnalysis.objects.create(batch=batch, document=document)
        extract_batch(batch)
        return redirect("workspace:detail", pk=batch.pk)

    batches = (
        batches_for_user(request.user).select_related("template").order_by("-number")[:10]
        if request.user.is_authenticated
        else []
    )
    return render(request, "invoxcel/prototype.html", {"upload_form": form, "batches": batches})


@login_required
def detail(request, pk):
    document = get_user_document(request.user, pk)
    return render(request, "invoxcel/upload_detail.html", {"document": document})


@login_required
@xframe_options_sameorigin
def source(request, pk):
    document = get_user_document(request.user, pk)
    try:
        response = FileResponse(document.file.open("rb"), content_type=document.content_type, filename=document.original_filename)
    except OSError as exc:
        raise Http404("Source file is unavailable.") from exc
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def preview(request, pk, page_number):
    import pypdfium2
    from .preview import render_page

    document = get_user_document(
        request.user,
        pk,
        content_type__in=["application/pdf", "image/tiff"],
    )
    try:
        with document.file.open("rb") as source:
            if document.content_type == "image/tiff":
                from io import BytesIO
                from PIL import Image
                with Image.open(source) as source_image:
                    if not 1 <= page_number <= source_image.n_frames:
                        raise ValueError("Unknown page")
                    source_image.seek(page_number - 1)
                    preview_image = source_image.convert("RGB")
                    preview_image.thumbnail((1600, 1600))
                    output = BytesIO()
                    preview_image.save(output, format="PNG")
                    image = output.getvalue()
            else:
                image = render_page(source.read(), page_number)
    except (OSError, ValueError, pypdfium2.PdfiumError) as exc:
        raise Http404("Page preview is unavailable. Open the original source.") from exc
    response = HttpResponse(image, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response
