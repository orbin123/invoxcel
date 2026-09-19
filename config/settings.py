"""
Django settings for config project.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-local-invoxcel-bootstrap"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is required when DEBUG is false."
        )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "apps.accounts",
    "apps.uploads",
    "apps.templates",
    "apps.processing",
    "apps.invoices",
    "apps.exports",
    "apps.workspace",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.CanonicalLocalhostMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/signin/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
AZURE_DOCUMENT_INTELLIGENCE_MODEL = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_MODEL", "prebuilt-invoice")
AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT = int(os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT", "90"))
AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES = int(os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_MAX_BYTES", "524288000"))
AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES = int(os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_MAX_PAGES", "2000"))
