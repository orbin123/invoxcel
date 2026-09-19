from django import forms
from django.forms import formset_factory
from apps.invoices.validation import normalize_value
from apps.processing.schema import DERIVED_KEYS


class ValuesForm(forms.Form):
    def __init__(self, *args, columns, **kwargs):
        super().__init__(*args, **kwargs)
        self.columns = columns
        for column in columns:
            if column.data_type == "boolean" and isinstance(self.initial.get(column.key), bool):
                self.initial[column.key] = str(self.initial[column.key]).lower()
            widget = forms.TextInput(attrs={"placeholder": "Missing", "aria-label": column.label})
            if column.data_type == "date":
                widget.attrs["placeholder"] = "YYYY-MM-DD"
            elif column.data_type in ("currency", "number"):
                widget.attrs.update({"inputmode": "decimal", "class": "numeric"})
            elif column.data_type == "boolean":
                widget = forms.Select(choices=[("", "Missing"), ("true", "True"), ("false", "False")])
            self.fields[column.key] = forms.CharField(disabled=column.dataset == "summary" and (column.value_key or column.key) in DERIVED_KEYS, required=False, max_length=4000, label=column.label, widget=widget)

    def clean(self):
        data = super().clean()
        for column in self.columns:
            if column.key not in data:
                continue
            try:
                data[column.key] = normalize_value(data[column.key], column.data_type)
                if column.key == "currency" and data[column.key]:
                    data[column.key] = data[column.key].upper()
            except ValueError as exc:
                self.add_error(column.key, str(exc))
        return data


class LineItemForm(ValuesForm):
    row_id = forms.IntegerField(required=False, widget=forms.HiddenInput)


LineItemFormSet = formset_factory(LineItemForm, extra=0, can_delete=True, max_num=200, validate_max=True, absolute_max=250)
