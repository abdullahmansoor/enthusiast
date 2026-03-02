import os
import tempfile

import pytest
from django.test import override_settings
from model_bakery import baker
from rest_framework.test import APIClient

from account.models import User
from agent.models import Conversation
from catalog.models import DataSet

# ---------------------------------------------------------------------------
# Allow running tests locally without a real Postgres server.
# If the DB_HOST env is not set (or points to the Docker hostname "postgres"),
# fall back to SQLite so that `pytest` works on a developer machine.
# ---------------------------------------------------------------------------
def pytest_configure(config):
    db_host = os.environ.get("ECL_DB_HOST", "postgres")
    if db_host == "postgres":
        # Override DATABASES to use SQLite in-memory for local runs.
        from django.conf import settings
        settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
                "TEST": {"NAME": ":memory:"},
            }
        }


@pytest.fixture
def user():
    return baker.make(User)


@pytest.fixture
def admin_user():
    return baker.make(User, is_staff=True)


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_api_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def data_set():
    return baker.make(DataSet)


@pytest.fixture
def conversation(user, data_set):
    return baker.make(Conversation, user=user, data_set=data_set)


@pytest.fixture(autouse=True)
def temp_media_root():
    tmp_dir = tempfile.mkdtemp()
    with override_settings(DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage", MEDIA_ROOT=tmp_dir):
        yield
