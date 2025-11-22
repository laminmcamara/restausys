"""
Django settings for restaurant_management project.

Enhanced for secure development & production readiness.
Reference:
- https://docs.djangoproject.com/en/5.2/topics/settings/
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
from django.urls import reverse_lazy
import os
import logging

# ==============================================================================
# BASE & ENVIRONMENT CONFIGURATION
# ==============================================================================

import environ

# --- Base directory ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Initialize environment handling ---
env = environ.Env(
    DEBUG=(bool, False)
)

# --- Determine which .env file to load ---
DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev")  # default to 'dev'

env_file = BASE_DIR / f".env.{DJANGO_ENV}"

if env_file.exists():
    print(f"🔧 Loading environment: {env_file}")
    environ.Env.read_env(env_file)
else:
    print(f"⚠️ No environment file found for: {env_file}, using system defaults.")

# --- Core Django settings ---
SECRET_KEY = env("SECRET_KEY", default="django-insecure-placeholder-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "localhost:8000")

# ==============================================================================
# ADMINS & MANAGERS
# ==============================================================================

ADMINS = [("Lamin M Camara", "laminmasana@gmail.com")]
MANAGERS = ADMINS

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    # 1. Third-party UI enhancements (must precede admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",

    # 2. Django core apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "django.contrib.sites",

    # 3. Third‑party apps
    "crispy_forms",
    "crispy_bootstrap5",
    "oauth2_provider",
    "rest_framework",

    # 4. Local apps
    "core.apps.CoreConfig",
    "staff",
    "tables",
    "menu",
    "ordering",
    "kitchen",
    "payments",
    "qr_screen",
    "notifications",
    "analytics",
]

SITE_ID = 1  # required for internationalization and multi-site features

# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # 🌍 enable language switching
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==============================================================================
# URL & ASGI CONFIGURATION
# ==============================================================================

ROOT_URLCONF = "restaurant_management.urls"
ASGI_APPLICATION = "restaurant_management.asgi.application"

# ==============================================================================
# TEMPLATES CONFIGURATION
# ==============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.static",
                "django.template.context_processors.i18n",  # 🌍 language context
            ],
        },
    },
]

# ==============================================================================
# DATABASE CONFIGURATION
# (SQLite in dev, override via environment variables for production)
# ==============================================================================

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

# ==============================================================================
# AUTHENTICATION & AUTHORIZATION
# ==============================================================================

AUTH_USER_MODEL = "core.CustomUser"
LOGIN_URL = reverse_lazy("core:login")
LOGIN_REDIRECT_URL = reverse_lazy("core:home")
LOGOUT_REDIRECT_URL = reverse_lazy("core:home")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ==============================================================================
# INTERNATIONALIZATION / LOCALIZATION
# ==============================================================================

LANGUAGE_CODE = "en"

# 🌍 Add major world languages
from django.utils.translation import gettext_lazy as _

LANGUAGES = [
    ("en", _("English")),
    ("es", _("Spanish")),
    ("fr", _("French")),
    ("de", _("German")),
    ("ar", _("Arabic")),
    ("zh-hans", _("Chinese (Simplified)")),
    ("ja", _("Japanese")),
    ("pt-br", _("Portuguese (Brazilian)")),
    ("ru", _("Russian")),
    ("hi", _("Hindi")),
    ("sw", _("Swahili")),
    ("tr", _("Turkish")), 
]

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

# ==============================================================================
# STATIC & MEDIA FILES
# ==============================================================================


STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / 'core' / 'static']
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# CHANNELS CONFIGURATION
# ==============================================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST", "127.0.0.1"), 6379)],
        },
    },
}

# ==============================================================================
# EMAIL CONFIGURATION (safely overridable)
# ==============================================================================

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "server@localhost")

# ==============================================================================
# SECURITY CONFIGURATIONS (production-ready but safe in dev)
# ==============================================================================

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("1", "true")
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] [{levelname}] {name}: {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "maxBytes": 5_000_000,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "verbose",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "include_html": True,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO"     # if DEBUG else "INFO",
        },
        "audit": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ==============================================================================
# DJANGO CRISPY FORMS
# ==============================================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ==============================================================================
# PRINTER CONFIGURATION
# ==============================================================================

PRINTERS = {
    "kitchen": {
        "NAME": "Kitchen Printer",
        "HOST": os.getenv("PRINTER_KITCHEN_HOST", "192.168.1.101"),
        "PORT": int(os.getenv("PRINTER_KITCHEN_PORT", 9100)),
        "TYPE": "network",
    },
    "pos": {
        "NAME": "POS Front Printer",
        "HOST": os.getenv("PRINTER_POS_HOST", "192.168.1.102"),
        "PORT": int(os.getenv("PRINTER_POS_PORT", 9100)),
        "TYPE": "network",
    },
    "drinks": {
        "NAME": "Drinks/Bar Printer",
        "HOST": os.getenv("PRINTER_DRINKS_HOST", "192.168.1.103"),
        "PORT": int(os.getenv("PRINTER_DRINKS_PORT", 9100)),
        "TYPE": "network",
    },
}

# ==============================================================================
# DEFAULT AUTO FIELD
# ==============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"