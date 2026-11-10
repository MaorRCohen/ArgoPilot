import os

from sqlalchemy.engine import make_url

ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
LIBPQ_OVERRIDES = ("PGHOST", "PGHOSTADDR", "PGSERVICE", "PGDATABASE")


def assert_safe_to_wipe(url: str) -> None:
    # The tests DROP SCHEMA public CASCADE. Only a local database with "test" in its name may be wiped.
    parsed = make_url(url)
    # Query parameters (host, hostaddr, dbname, service...) and these libpq variables override the URL.
    if parsed.query:
        raise RuntimeError("Refusing to wipe: the URL must not have a query string")
    for name in LIBPQ_OVERRIDES:
        if os.environ.get(name):
            raise RuntimeError(f"Refusing to wipe: {name} is set and can redirect the connection")
    if parsed.host not in ALLOWED_HOSTS:
        raise RuntimeError(f"Refusing to wipe: host {parsed.host!r} is not localhost/127.0.0.1")
    if not parsed.database or "test" not in parsed.database:
        raise RuntimeError(f"Refusing to wipe: database {parsed.database!r} does not contain 'test'")
