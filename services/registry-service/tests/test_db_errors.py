import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError, TimeoutError as PoolTimeoutError

import main


class FakeDriverError(Exception):
    def __init__(self, message, sqlstate=None, sqlite_errorname=None):
        super().__init__(message)
        self.sqlstate = sqlstate
        self.sqlite_errorname = sqlite_errorname


def make_error(cls, message, sqlstate=None, sqlite_errorname=None, invalidated=False):
    exc = cls("SELECT 1", {}, FakeDriverError(message, sqlstate, sqlite_errorname))
    exc.connection_invalidated = invalidated
    return exc


@pytest.fixture
def raise_from_db(client, monkeypatch):
    def run(exc):
        def boom(*args, **kwargs):
            raise exc

        monkeypatch.setattr(main, "get_row", boom)
        return client.get("/v1/farms/any-id")

    return run


UNAVAILABLE_CASES = {
    "pg_connection_refused": make_error(OperationalError, "connection refused", sqlstate="08006"),
    "pg_connect_timeout": make_error(OperationalError, "connection timeout expired"),
    "pg_disconnect": make_error(OperationalError, "server closed the connection", invalidated=True),
    "pg_too_many_connections": make_error(OperationalError, "too many clients", sqlstate="53300"),
    "pg_lock_not_available": make_error(OperationalError, "could not obtain lock", sqlstate="55P03"),
    "pg_deadlock": make_error(OperationalError, "deadlock detected", sqlstate="40P01"),
    "pg_admin_shutdown": make_error(OperationalError, "terminating connection", sqlstate="57P01"),
    "pg_crash_shutdown": make_error(OperationalError, "server crashed", sqlstate="57P02"),
    "pool_exhausted": PoolTimeoutError("QueuePool limit of size 5 overflow 10 reached"),
    "sqlite_cantopen": make_error(
        OperationalError, "unable to open database file", sqlite_errorname="SQLITE_CANTOPEN"
    ),
    "sqlite_busy": make_error(OperationalError, "database is locked", sqlite_errorname="SQLITE_BUSY"),
    "sqlite_locked": make_error(
        OperationalError, "database table is locked", sqlite_errorname="SQLITE_LOCKED"
    ),
}


@pytest.mark.parametrize("exc", UNAVAILABLE_CASES.values(), ids=UNAVAILABLE_CASES.keys())
def test_temporary_db_failure_returns_503(raise_from_db, assert_problem, exc):
    response = raise_from_db(exc)

    assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["Retry-After"] == "30"
    assert response.json()["detail"] == "Database unavailable"


BUG_CASES = {
    "pg_undefined_table": make_error(ProgrammingError, 'relation "farms" does not exist', sqlstate="42P01"),
    "pg_syntax_error": make_error(ProgrammingError, 'syntax error at or near "SELEC"', sqlstate="42601"),
    "sqlite_no_such_table": make_error(
        OperationalError, "no such table: farms", sqlite_errorname="SQLITE_ERROR"
    ),
}


@pytest.mark.parametrize("exc", BUG_CASES.values(), ids=BUG_CASES.keys())
def test_other_db_errors_return_500_without_driver_text(raise_from_db, assert_problem, exc):
    response = raise_from_db(exc)

    assert_problem(response, 500, "UNAVAILABLE")
    assert response.json()["detail"] == "Internal server error"
    assert "Retry-After" not in response.headers
    for leaked in ("farms", "syntax error", "no such table", "does not exist"):
        assert leaked not in response.text


CONNECT_CASES = {
    "refused": (make_error(OperationalError, "connection refused", sqlstate="08006"), 503),
    "pool_exhausted": (PoolTimeoutError("QueuePool limit reached"), 503),
    "invalid_password": (
        make_error(OperationalError, 'password authentication failed for user "secret"', sqlstate="28P01"),
        500,
    ),
}


@pytest.mark.parametrize("exc,status", CONNECT_CASES.values(), ids=CONNECT_CASES.keys())
@pytest.mark.parametrize("path", ["/health", "/v1/farms"])
def test_failure_while_opening_connection(client, monkeypatch, assert_problem, path, exc, status):
    def fail_to_connect():
        raise exc

    monkeypatch.setattr(main, "get_connection", fail_to_connect)

    response = client.get(path)

    assert_problem(response, status, "UNAVAILABLE")
    if status == 503:
        assert response.headers["Retry-After"] == "30"
        assert response.json()["detail"] == "Database unavailable"
    else:
        assert "Retry-After" not in response.headers
        assert response.json()["detail"] == "Internal server error"
        for leaked in ("password", "secret", "28P01"):
            assert leaked not in response.text
