from django.contrib import admin
from .models import Invoice, LineItem


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis", "reviewed_at", "updated_at")
    readonly_fields = ("provenance", "updated_at")
    inlines = (LineItemInline,)
