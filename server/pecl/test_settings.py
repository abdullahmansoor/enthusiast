"""
Test settings: SQLite in-memory DB so pytest runs without a live Postgres.
"""
import os

# Satisfy all required env vars BEFORE the main settings module is imported.
os.environ.setdefault("ECL_DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ECL_DJANGO_DEBUG", "True")
os.environ.setdefault("ECL_DJANGO_ALLOWED_HOSTS", '["*"]')
os.environ.setdefault("ECL_DB_NAME", "test_db")
os.environ.setdefault("ECL_DB_USER", "test")
os.environ.setdefault("ECL_DB_PASSWORD", "test")
os.environ.setdefault("ECL_DB_HOST", "localhost")
os.environ.setdefault("ECL_DB_PORT", "5432")
os.environ.setdefault("ECL_CELERY_BROKER_URL", "memory://")
os.environ.setdefault("ECL_CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("ECL_CELERY_TIMEZONE", "UTC")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from pecl.settings import *  # noqa: F401, F403, E402

# Override DATABASES to use SQLite -- no real Postgres required.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": ":memory:"},
    }
}

ANALYTICS_CONFIG = {
    "enable_local_models": False,
    "enable_llm_judges": False,
    "llm_sampling_rate": 0.0,
    "async_evaluation": False,
    "openai_api_key": "sk-test",
    "llm_judge_model": "gpt-4o-mini",
    "llm_judge_temperature": 0.0,
}

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
