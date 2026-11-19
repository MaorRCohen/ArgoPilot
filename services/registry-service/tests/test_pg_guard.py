import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.pg_guard import UnsafeTestDatabase, assert_safe_to_wipe, check_test_database

SERVICE_DIR = Path(__file__).resolve().parent.parent
SECRET = "hunter2"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@localhost:5432/registry_test",
        "postgresql+psycopg://u:p@127.0.0.1/app_test",
    ],
)
def test_accepts_local_test_database(url):
    assert_safe_to_wipe(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@db.prod.example.com/registry_test",
        "postgresql+psycopg://u:p@localhost.evil.com/registry_test",
        "postgresql+psycopg://user@evil/db_test",
        "postgresql+psycopg://u:p@localhost@evil.com/db_test",
        "postgresql+psycopg://u:p@localhost:5432",
        "postgresql+psycopg://u:p@localhost:5432/registry",
        "postgresql+psycopg://u:p@127.0.0.1/test",
        "postgresql+psycopg://u:p@127.0.0.1/test_registry",
        "postgresql+psycopg://u:p@evil.com/test",
        "sqlite:///tmp/test.db",
        "postgresql+psycopg://u:p@localhost/registry_test?host=prod.example.com",
        "postgresql+psycopg://u:p@localhost/registry_test?hostaddr=10.1.2.3",
        "postgresql+psycopg://u:p@localhost/registry_test?dbname=production",
    ],
)
def test_rejects_unsafe_url(url):
    with pytest.raises(RuntimeError):
        assert_safe_to_wipe(url)


@pytest.mark.parametrize("name", ["PGHOST", "PGHOSTADDR", "PGSERVICE", "PGDATABASE"])
def test_rejects_libpq_environment_override(monkeypatch, name):
    # libpq reads these and can send the connection somewhere other than the URL says.
    monkeypatch.setenv(name, "anything")
    with pytest.raises(RuntimeError):
        assert_safe_to_wipe("postgresql+psycopg://u:p@localhost:5432/registry_test")


@pytest.mark.parametrize(
    "test_url",
    [
        f"postgresql+psycopg://registry_owner:{SECRET}@127.0.0.1:5432/registry",
        f"postgresql+psycopg://registry_owner:{SECRET}@127.0.0.1:5432/test_registry",
        f"postgresql+psycopg://registry_owner:{SECRET}@127.0.0.1:5432/registry_testing",
    ],
)
def test_guard_rejects_a_name_that_does_not_end_with_test(test_url):
    with pytest.raises(UnsafeTestDatabase, match="_test") as info:
        check_test_database(test_url, app_url=None)
    assert SECRET not in str(info.value)


def test_guard_rejects_the_same_database_as_the_app():
    test_url = f"postgresql+psycopg://registry_owner:{SECRET}@127.0.0.1:5432/registry_test"
    app_url = "postgresql+psycopg://registry_owner:hunter3@127.0.0.1:5432/registry_test"
    with pytest.raises(UnsafeTestDatabase, match="same database") as info:
        check_test_database(test_url, app_url)
    assert SECRET not in str(info.value)
    assert "hunter3" not in str(info.value)


def test_guard_accepts_a_test_database_other_than_the_app_one():
    app_url = "postgresql+psycopg://registry_owner:hunter3@127.0.0.1:5432/registry"
    test_url = f"postgresql+psycopg://registry_owner:{SECRET}@127.0.0.1:5432/registry_test"
    check_test_database(test_url, app_url)


def test_guard_accepts_when_the_app_uses_sqlite():
    test_url = f"postgresql+psycopg://u:{SECRET}@127.0.0.1:5432/registry_test"
    check_test_database(test_url, "sqlite:////abs/registry.db")


def test_pytest_refuses_before_touching_any_database():
    # The guard runs in pytest_configure: the run stops with exit code 2 before any test or connection.
    env = {**os.environ, "TEST_DATABASE_URL": f"postgresql+psycopg://u:{SECRET}@127.0.0.1:5432/registry"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_pg_guard.py"],
        cwd=SERVICE_DIR, env=env, capture_output=True, text=True, timeout=120,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 2
    assert "_test" in output
    assert SECRET not in output
