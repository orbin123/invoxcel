from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.ownership import get_user_template, templates_for_user

from .forms import TemplateForm


@login_required
def template_list(request):
    templates = templates_for_user(request.user).prefetch_related("columns")
    return render(request, "invoxcel/templates/list.html", {"templates": templates})


@login_required
def template_create(request):
    form = TemplateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("templates:list")
    return render(
        request,
        "invoxcel/templates/form.html",
        {"form": form, "page_title": "Create template", "submit_label": "Save template"},
    )


@login_required
def template_edit(request, pk):
    template = get_user_template(request.user, pk)
    form = TemplateForm(request.POST or None, instance=template, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("templates:list")
    return render(
        request,
        "invoxcel/templates/form.html",
        {
            "form": form,
            "template": template,
            "page_title": "Edit template",
            "submit_label": "Save changes",
        },
    )


@login_required
def template_delete(request, pk):
    template = get_user_template(request.user, pk)
    is_in_use = template.uploaded_documents.exists()
    if request.method == "POST" and not is_in_use:
        template.delete()
        return redirect("templates:list")
    return render(
        request,
        "invoxcel/templates/delete.html",
        {"template": template, "is_in_use": is_in_use},
    )
