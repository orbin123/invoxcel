from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from .models import LINE_ITEM_COLUMNS, SUMMARY_COLUMNS, Template, TemplateColumn


class TemplateForm(forms.ModelForm):
    summary_columns = forms.MultipleChoiceField(
        choices=[(key, label) for key, label, _ in SUMMARY_COLUMNS],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    line_item_columns = forms.MultipleChoiceField(
        choices=[(key, label) for key, label, _ in LINE_ITEM_COLUMNS],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    custom_summary_columns = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Project code\nApproval status"}
        ),
    )
    custom_line_item_columns = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Cost centre"}),
    )

    class Meta:
        model = Template
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Monthly expense import"}
            )
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["name"].label = "Template name"
        self.fields["summary_columns"].label = "Summary columns"
        self.fields["line_item_columns"].label = "Line item columns"
        self.fields["custom_summary_columns"].label = "Additional summary columns"
        self.fields["custom_line_item_columns"].label = "Additional line item columns"

        if self.instance.pk:
            columns = self.instance.columns.all()
            self.initial["summary_columns"] = [
                column.key
                for column in columns
                if column.dataset == TemplateColumn.Dataset.SUMMARY
                and not column.is_custom
            ]
            self.initial["line_item_columns"] = [
                column.key
                for column in columns
                if column.dataset == TemplateColumn.Dataset.LINE_ITEM
                and not column.is_custom
            ]
            self.initial["custom_summary_columns"] = "\n".join(
                column.label
                for column in columns
                if column.dataset == TemplateColumn.Dataset.SUMMARY
                and column.is_custom
            )
            self.initial["custom_line_item_columns"] = "\n".join(
                column.label
                for column in columns
                if column.dataset == TemplateColumn.Dataset.LINE_ITEM
                and column.is_custom
            )

    def clean(self):
        cleaned_data = super().clean()
        summary_custom = self._custom_labels(
            cleaned_data.get("custom_summary_columns", "")
        )
        line_item_custom = self._custom_labels(
            cleaned_data.get("custom_line_item_columns", "")
        )
        cleaned_data["custom_summary_columns"] = summary_custom
        cleaned_data["custom_line_item_columns"] = line_item_custom

        if not (
            cleaned_data.get("summary_columns")
            or cleaned_data.get("line_item_columns")
            or summary_custom
            or line_item_custom
        ):
            raise ValidationError("Choose at least one summary or line item column.")

        self._validate_custom_labels(
            summary_custom,
            cleaned_data.get("summary_columns", []),
            SUMMARY_COLUMNS,
            "custom_summary_columns",
        )
        self._validate_custom_labels(
            line_item_custom,
            cleaned_data.get("line_item_columns", []),
            LINE_ITEM_COLUMNS,
            "custom_line_item_columns",
        )
        return cleaned_data

    def clean_name(self):
        name = self.cleaned_data["name"]
        if self.user and Template.objects.filter(user=self.user, name=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError("You already have a template with this name.")
        return name

    @staticmethod
    def _custom_labels(value):
        return [line.strip() for line in value.splitlines() if line.strip()]

    def _validate_custom_labels(self, labels, selected_keys, definitions, field_name):
        standard_labels = {
            label.lower()
            for key, label, _ in definitions
            if key in selected_keys
        }
        normalized_labels = [label.lower() for label in labels]
        normalized_keys = [slugify(label).replace("-", "_") for label in labels]
        if len(set(normalized_labels)) != len(normalized_labels):
            self.add_error(field_name, "Each custom column name must be unique.")
        if set(normalized_labels) & standard_labels:
            self.add_error(
                field_name, "Custom columns cannot duplicate selected standard columns."
            )
        if not all(normalized_keys):
            self.add_error(
                field_name, "Use letters or numbers in each custom column name."
            )
        if len(set(normalized_keys)) != len(normalized_keys):
            self.add_error(
                field_name, "Custom column names must produce unique keys."
            )
        if any(len(f"custom_{key}") > 80 for key in normalized_keys):
            self.add_error(field_name, "Custom column names must be 73 characters or fewer.")

    def save(self, commit=True):
        with transaction.atomic():
            template = super().save(commit=False)
            if not template.pk:
                template.user = self.user
            if commit:
                template.save()
            if not commit:
                return template
            template.columns.all().delete()
            self._save_columns(
                template,
                TemplateColumn.Dataset.SUMMARY,
                SUMMARY_COLUMNS,
                self.cleaned_data["summary_columns"],
                self.cleaned_data["custom_summary_columns"],
            )
            self._save_columns(
                template,
                TemplateColumn.Dataset.LINE_ITEM,
                LINE_ITEM_COLUMNS,
                self.cleaned_data["line_item_columns"],
                self.cleaned_data["custom_line_item_columns"],
            )
        return template

    @staticmethod
    def _save_columns(template, dataset, definitions, selected_keys, custom_labels):
        selected = set(selected_keys)
        columns = [
            TemplateColumn(
                template=template,
                dataset=dataset,
                key=key,
                label=label,
                data_type=data_type,
                position=position,
            )
            for position, (key, label, data_type) in enumerate(
                definition for definition in definitions if definition[0] in selected
            )
        ]
        next_position = len(columns)
        columns.extend(
            TemplateColumn(
                template=template,
                dataset=dataset,
                key=f"custom_{slugify(label).replace('-', '_')}",
                label=label,
                data_type=TemplateColumn.DataType.TEXT,
                position=next_position + offset,
                is_custom=True,
            )
            for offset, label in enumerate(custom_labels)
        )
        TemplateColumn.objects.bulk_create(columns)
