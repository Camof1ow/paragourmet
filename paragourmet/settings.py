# paragourmet/settings.py
# NOTE: English comments only (per your preference)

import os
from pathlib import Path
from dotenv import load_dotenv

# --------------------------------------------------------------------------------------
# Paths & .env
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------------------
# Helpers for env parsing
# --------------------------------------------------------------------------------------
def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]

def derive_csrf_trusted_origins(hosts: list[str], scheme: str = "https") -> list[str]:
    # Django requires absolute origins with scheme
    # e.g., https://example.com, http://127.0.0.1:8000 (with port if needed)
    origins: list[str] = []
    for h in hosts:
        if "://" in h:
            # already looks like an origin (unlikely in ALLOWED_HOSTS), skip
            continue
        # common cases: bare host or host:port
        origins.append(f"{scheme}://{h}")
    return origins

# --------------------------------------------------------------------------------------
# Core security & debug
# --------------------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-default-key-for-dev")
# Support both DEBUG and DJANGO_DEBUG; latter wins if present
DEBUG = env_bool("DJANGO_DEBUG", env_bool("DEBUG", False))

# --------------------------------------------------------------------------------------
# Hosts & CSRF
# Use DJANGO_ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS from environment.
# Fallbacks:
#  - Dev: allow localhost/127.0.0.1
#  - Prod: require explicit env; if missing, keep empty to fail-fast
# --------------------------------------------------------------------------------------
if DEBUG:
    ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
else:
    ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "")  # explicit in prod

# If CSRF_TRUSTED_ORIGINS not provided, derive from ALLOWED_HOSTS (https in prod, http in dev)
_env_csrf = env_list("CSRF_TRUSTED_ORIGINS", "")
if _env_csrf:
    CSRF_TRUSTED_ORIGINS = _env_csrf
else:
    CSRF_TRUSTED_ORIGINS = derive_csrf_trusted_origins(
        ALLOWED_HOSTS,
        scheme="http" if DEBUG else "https",
    )

# --------------------------------------------------------------------------------------
# Django apps
# --------------------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "prompt.apps.PromptConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "paragourmet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "prompt" / "templates"],
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

WSGI_APPLICATION = "paragourmet.wsgi.application"

# --------------------------------------------------------------------------------------
# Database (sqlite by default)
# --------------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --------------------------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------------------
# I18N & TZ
# --------------------------------------------------------------------------------------
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------------------
# Static files (WhiteNoise)
# --------------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --------------------------------------------------------------------------------------
# Security headers (prod only)
# --------------------------------------------------------------------------------------
# If you're behind a reverse proxy/ALB and terminate TLS there:
#   set BEHIND_PROXY=1 to trust X-Forwarded-Proto and enable SECURE_SSL_REDIRECT.
if not DEBUG:
    if env_bool("BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    else:
        # Direct TLS at app container → allow opting out via env
        SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)
else:
    # Relaxed dev defaults
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------------------
# Logging
# - Console always on
# - File logging optional (LOG_TO_FILE=1). Directory auto-created.
# --------------------------------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_TO_FILE = env_bool("LOG_TO_FILE", False)
if LOG_TO_FILE:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
        },
        **(
            {
                "file": {
                    "level": "ERROR",
                    "class": "logging.FileHandler",
                    "filename": str(LOG_DIR / "django.log"),
                    "formatter": "json",
                }
            }
            if LOG_TO_FILE
            else {}
        ),
    },
    "root": {
        "handlers": ["console"] + (["file"] if LOG_TO_FILE else []),
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"] + (["file"] if LOG_TO_FILE else []),
            "level": "INFO",
            "propagate": False,
        },
        "prompt": {
            "handlers": ["console"] + (["file"] if LOG_TO_FILE else []),
            "level": "INFO",
            "propagate": False,
        },
    },
}

# --------------------------------------------------------------------------------------
# Debug prints at boot (optional; remove later if noisy)
# --------------------------------------------------------------------------------------
print("DEBUG=", DEBUG)
print("ALLOWED_HOSTS=", ALLOWED_HOSTS)
print("CSRF_TRUSTED_ORIGINS=", CSRF_TRUSTED_ORIGINS)
