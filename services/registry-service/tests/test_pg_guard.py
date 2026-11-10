import pytest

from tests.pg_guard import assert_safe_to_wipe


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@localhost:5432/registry_test",
        "postgresql+psycopg://u:p@127.0.0.1/test",
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
