from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@company.com",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {
                "autocomplete": "new-password",
                "placeholder": "Create a password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "autocomplete": "new-password",
                "placeholder": "Confirm your password",
            }
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.email = email
        user.username = email
        if commit:
            user.save()
        return user


def resolve_login_username(identifier: str) -> str:
    identifier = identifier.strip()
    if "@" in identifier:
        user = User.objects.filter(email__iexact=identifier).first()
        if user is not None:
            return user.username
    return identifier


class SignInForm(forms.Form):
    email = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": "you@company.com or yourusername",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Enter your password",
            }
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("email", "")
        password = cleaned_data.get("password")
        if not identifier or not password:
            return cleaned_data

        user = authenticate(
            self.request,
            username=resolve_login_username(identifier),
            password=password,
        )
        if user is None:
            raise forms.ValidationError("Enter a valid email or username and password.")
        self.user_cache = user
        return cleaned_data

    def get_user(self):
        return self.user_cache
