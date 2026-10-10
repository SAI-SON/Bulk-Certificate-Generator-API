"""
Base Django settings for Bulk Certificate Generator API.

Shared across all environments. Environment-specific settings are in
development.py and production.py.
"""
import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    MAX_TEMPLATE_SIZE_MB=(int, 10),
    MAX_PARTICIPANT_FILE_SIZE_MB=(int, 5),
    MAX_PARTICIPANT_ROWS=(int, 10000),
    SYNC_GENERATION_THRESHOLD=(int, 20),
    CERTIFICATE_ID_PREFIX=(str, "CERT"),
    TEMP_FILE_RETENTION_DAYS=(int, 7),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))


# ──────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")


# ──────────────────────────────────────────────────────────────
# Application definition
# ──────────────────────────────────────────────────────────────

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.templates_mgmt",
    "apps.batches",
    "apps.certificates",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ──────────────────────────────────────────────────────────────
# Password validation
# ──────────────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ──────────────────────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ──────────────────────────────────────────────────────────────
# Static & Media files
# ──────────────────────────────────────────────────────────────

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# ──────────────────────────────────────────────────────────────
# Default primary key field type
# ──────────────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ──────────────────────────────────────────────────────────────
# Django REST Framework
# ──────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "verification": "200/hour",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
    "DATE_FORMAT": "%Y-%m-%d",
}


# ──────────────────────────────────────────────────────────────
# drf-spectacular (Swagger / OpenAPI)
# ──────────────────────────────────────────────────────────────

SPECTACULAR_SETTINGS = {
    "TITLE": "Bulk Certificate Generator API",
    "DESCRIPTION": (
        "A production-quality API for generating bulk PDF certificates. "
        "Upload a template, provide participant data via CSV/XLSX, and "
        "generate personalized certificates at scale."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
}


# ──────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True


# ──────────────────────────────────────────────────────────────
# Celery
# ──────────────────────────────────────────────────────────────

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55 minutes soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # Prevent memory leaks


# ──────────────────────────────────────────────────────────────
# Application-specific settings
# ──────────────────────────────────────────────────────────────

# Maximum upload size for certificate templates (bytes)
MAX_TEMPLATE_SIZE = env("MAX_TEMPLATE_SIZE_MB") * 1024 * 1024

# Maximum upload size for participant files (bytes)
MAX_PARTICIPANT_FILE_SIZE = env("MAX_PARTICIPANT_FILE_SIZE_MB") * 1024 * 1024

# Maximum number of rows allowed in a participant file
MAX_PARTICIPANT_ROWS = env("MAX_PARTICIPANT_ROWS")

# Number of records below which generation runs synchronously
SYNC_GENERATION_THRESHOLD = env("SYNC_GENERATION_THRESHOLD")

# Certificate ID prefix
CERTIFICATE_ID_PREFIX = env("CERTIFICATE_ID_PREFIX")

# Temporary file retention (days)
TEMP_FILE_RETENTION_DAYS = env("TEMP_FILE_RETENTION_DAYS")

# Allowed template image formats
ALLOWED_TEMPLATE_FORMATS = ["png", "jpeg", "jpg"]

# Maximum image dimensions (pixels)
MAX_TEMPLATE_WIDTH = 10000
MAX_TEMPLATE_HEIGHT = 10000

# Fonts directory
FONTS_DIR = BASE_DIR / "fonts"

# Approved fonts (filename -> display name)
APPROVED_FONTS = {
    "DejaVuSans.ttf": "DejaVu Sans",
    "DejaVuSans-Bold.ttf": "DejaVu Sans Bold",
}

# Default font for certificate text
DEFAULT_FONT = "DejaVuSans.ttf"
DEFAULT_FONT_SIZE = 24
DEFAULT_FONT_COLOR = "#000000"

# Upload directories (relative to MEDIA_ROOT)
TEMPLATE_UPLOAD_DIR = "templates"
PARTICIPANT_UPLOAD_DIR = "participants"
CERTIFICATE_UPLOAD_DIR = "certificates"
