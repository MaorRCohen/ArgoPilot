import logging

import pytest
from fastapi.testclient import TestClient

import db
import main
from main import app

FAKE_PASSWORD = "fakepass-123"
FAKE_URL = f"postgresql+psycopg://registry_app:{FAKE_PASSWORD}@127.0.0.1:1/registry"


def connection_fails(*args, **kwargs):
    raise RuntimeError("boom")


@pytest.fixture
def unexpected_error(monkeypatch):
    # An error that no handler expects: it reaches the catch-all Exception handler.
    monkeypatch.setattr(main, "get_connection", connection_fails)


def test_unexpected_error_keeps_the_500_body_and_logs_the_traceback(unexpected_error, caplog, assert_problem):
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR):
        response = client.get("/v1/farms")

    assert_problem(response, 500, "UNAVAILABLE")
    assert response.json()["detail"] == "Internal server error"
    assert "Traceback" in caplog.text
    assert "RuntimeError: boom" in caplog.text


def test_database_password_never_reaches_the_logs(monkeypatch, caplog):
    monkeypatch.setattr(db, "engine", db.make_engine(FAKE_URL))
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.DEBUG):
        db.log_database(FAKE_URL)
        unreachable = client.get("/health")  # connection refused: 503, no traceback
        monkeypatch.setattr(main, "get_connection", connection_fails)
        unexpected = client.get("/v1/farms")  # unexpected error: 500, traceback logged

    assert unreachable.status_code == 503
    assert unexpected.status_code == 500
    assert FAKE_PASSWORD not in caplog.text
    assert FAKE_PASSWORD not in repr(caplog.records)
    assert FAKE_PASSWORD not in unreachable.text + unexpected.text
