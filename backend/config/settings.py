"""
Django settings for the easyES backend.

All configuration is sourced from environment variables (see .env.example).
Sensible defaults let the project run locally on SQLite without any setup.
"""
from pathlib import Path
import os

import dj_database_url
from corsheaders.defaults import default_headers
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from repo root or backend dir if present (dev convenience only).
for candidate in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if candidate.exists():
        load_dotenv(candidate)
        break


def env_value(key: str, default: str = "", *legacy_keys: str) -> str:
    for candidate in (key, *legacy_keys):
        val = os.environ.get(candidate)
        if val is not None:
            return val
    return default


def env_bool(key: str, default: bool = False, *legacy_keys: str) -> bool:
    val = env_value(key, "", *legacy_keys)
    if val == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "", *legacy_keys: str) -> list[str]:
    raw = env_value(key, default, *legacy_keys)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Core -----------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-easyes-change-this-before-production-2026",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "*") or ["*"]

# Field-level encryption key for credential secrets (Fernet). Dev default is
# NOT secure; production must supply EASYES_ENCRYPTION_KEY.
ENCRYPTION_KEY = env_value("EASYES_ENCRYPTION_KEY", "", "COMPANYOS_ENCRYPTION_KEY")

# Root directory for isolated per-project agent workspaces.
WORKSPACES_ROOT = Path(
    env_value(
        "EASYES_WORKSPACES_ROOT",
        str(BASE_DIR.parent / "data" / "workspaces"),
        "COMPANYOS_WORKSPACES_ROOT",
    )
)

# Whether seed commands may create the demo user/credentials. Off in prod.
ALLOW_DEMO_SEED = env_bool("EASYES_ALLOW_DEMO_SEED", True, "COMPANYOS_ALLOW_DEMO_SEED")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.accounts",
    "apps.organizations",
    "apps.structure",
    "apps.actors",
    "apps.agents",
    "apps.models_registry",
    "apps.prompts",
    "apps.tools",
    "apps.projects",
    "apps.workflows",
    "apps.executions",
    "apps.communications",
    "apps.artifacts",
    "apps.evaluations",
    "apps.policies",
    "apps.audit",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

# --- Database -------------------------------------------------------------
# DATABASE_URL wins; otherwise fall back to SQLite for zero-setup local dev.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "easyES API",
    "DESCRIPTION": "Universal Human + AI Organization & Execution Platform — Foundation/Demo API.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# --- CORS -----------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ALLOW_CREDENTIALS = True
# Organization selection is carried in a custom request header by the web app.
# django-cors-headers only allows its built-in header set unless it is extended,
# so browser preflight requests were rejecting every organization-scoped call.
CORS_ALLOW_HEADERS = (*default_headers, "x-organization")
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)

# --- Execution ------------------------------------------------------------
# Pluggable backend that runs workflow runs. "thread" keeps everything
# in-process (great for the demo); the interface allows Celery/Temporal later.
EXECUTION_BACKEND = env_value("EASYES_EXECUTION_BACKEND", "thread", "COMPANYOS_EXECUTION_BACKEND")

# Default model provider used when an agent/credential does not specify one.
DEFAULT_MODEL_PROVIDER = env_value("EASYES_DEFAULT_PROVIDER", "fake", "COMPANYOS_DEFAULT_PROVIDER")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
