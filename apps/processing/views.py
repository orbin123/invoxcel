from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.ownership import get_user_batch
from apps.uploads.models import UploadedDocument

@login_required
def analysis_review(request, pk):
    # Existing batch bookmarks lead directly to the current review workspace.
    return redirect("workspace:detail", pk=pk)


@login_required
@require_POST
def delete_batch(request, pk):
    batch = get_user_batch(request.user, pk)
    documents = [
        analysis.document
        for analysis in batch.document_analyses.select_related("document")
        if analysis.document.user_id == request.user.id
    ]
    files = [(document.file.storage, document.file.name) for document in documents if document.file.name]
    batch_name = batch.display_name
    with transaction.atomic():
        batch.delete()
        UploadedDocument.objects.filter(user=request.user, pk__in=[document.pk for document in documents]).delete()
        transaction.on_commit(lambda: _delete_files(files))
    messages.success(request, f"{batch_name} and its source files were deleted.")
    return redirect(f"{reverse('uploads:upload')}#batches")


def _delete_files(files):
    for storage, name in files:
        storage.delete(name)
