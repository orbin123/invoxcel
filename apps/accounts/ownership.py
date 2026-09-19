"""User-scoped query helpers for domain resources."""

from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.processing.models import AnalysisBatch
from apps.templates.models import Template
from apps.uploads.models import UploadedDocument


def batches_for_user(user):
    return AnalysisBatch.objects.filter(user=user)


def get_user_batch(user, pk, queryset=None):
    base = queryset if queryset is not None else AnalysisBatch.objects.all()
    return get_object_or_404(base, pk=pk, user=user)


def templates_for_user(user):
    return Template.objects.filter(Q(user=user) | Q(is_standard=True))


def get_user_template(user, pk):
    return get_object_or_404(Template, pk=pk, is_standard=False, user=user)


def get_user_document(user, pk, **filters):
    return get_object_or_404(UploadedDocument, pk=pk, user=user, **filters)
