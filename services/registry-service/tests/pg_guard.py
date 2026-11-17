import os

from sqlalchemy.engine import make_url

ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
LIBPQ_OVERRIDES = ("PGHOST", "PGHOSTADDR", "PGSERVICE", "PGDATABASE")
TEST_SUFFIX = "_test"


class UnsafeTestDatabase(RuntimeError):
    """Refused before any database is touched. The message states the rule and never the URL."""


def _database_name(url: str) -> str:
    return make_url(url).database or ""


def check_test_database(test_url: str, app_url: str | None) -> None:
    # The tests wipe TEST_DATABASE_URL. Its name must mark it as a test database (like Django's test_
    # prefix), and it must never be the database the app itself uses.
    test_name = _database_name(test_url)
    if not test_name.endswith(TEST_SUFFIX):
        raise UnsafeTestDatabase("TEST_DATABASE_URL: the database name must end with '_test'.")
    if app_url is not None and _database_name(app_url) == test_name:
        raise UnsafeTestDatabase(
            "TEST_DATABASE_URL points to the same database as DATABASE_URL. "
            "Use a separate database whose name ends with '_test'."
        )


def assert_safe_to_wipe(url: str) -> None:
    # The tests DROP SCHEMA public CASCADE. Only a local database whose name ends with _test may be wiped.
    parsed = make_url(url)
    # Query parameters (host, hostaddr, dbname, service...) and these libpq variables override the URL.
    if parsed.query:
        raise RuntimeError("Refusing to wipe: the URL must not have a query string")
    for name in LIBPQ_OVERRIDES:
        if os.environ.get(name):
            raise RuntimeError(f"Refusing to wipe: {name} is set and can redirect the connection")
    if parsed.host not in ALLOWED_HOSTS:
        raise RuntimeError(f"Refusing to wipe: host {parsed.host!r} is not localhost/127.0.0.1")
    check_test_database(url, app_url=None)
