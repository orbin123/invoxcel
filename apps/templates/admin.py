from django.contrib import admin

from .models import Template, TemplateColumn


class TemplateColumnInline(admin.TabularInline):
    model = TemplateColumn
    extra = 0
    ordering = ("dataset", "position")


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_standard", "created_at", "updated_at")
    list_filter = ("is_standard", "user")
    search_fields = ("name",)
    inlines = (TemplateColumnInline,)
