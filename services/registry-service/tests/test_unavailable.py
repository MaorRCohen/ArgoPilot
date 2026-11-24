import pytest

import main


@pytest.mark.sqlite_only
def test_missing_db_file_returns_503_and_is_not_created(client, db_path, assert_problem):
    db_path.unlink()

    for path in ["/health", "/v1/farms", "/v1/farms/any-id/area"]:
        response = client.get(path)

        assert_problem(response, 503, "UNAVAILABLE")
        assert response.headers["Retry-After"] == "30"
        assert response.json()["detail"] == "Database unavailable"

    # mode=rw must fail instead of creating an empty registry.db.
    assert not db_path.exists()


@pytest.mark.sqlite_only
def test_health_on_db_without_tables_is_503_schema_missing(client, db_path, assert_problem):
    db_path.write_bytes(b"")  # reachable, but the schema is not set up

    response = client.get("/health")

    assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["Retry-After"] == "30"
    assert response.json()["detail"] == "Database schema is missing: no farms table"
    assert "sqlite" not in response.text.lower()
    assert "no such table" not in response.text


@pytest.mark.sqlite_only
def test_db_without_tables_returns_500_without_sqlite_text(client, db_path, assert_problem):
    db_path.write_bytes(b"")

    response = client.get("/v1/farms")

    assert_problem(response, 500, "UNAVAILABLE")
    assert response.json()["detail"] == "Internal server error"
    assert "Retry-After" not in response.headers
    assert "sqlite" not in response.text.lower()
    assert "no such table" not in response.text


@pytest.mark.sqlite_only
def test_health_on_a_corrupt_file_is_500_not_503(client, db_path, assert_problem):
    # Not a SQLite file at all: a broken file, not a missing schema or a busy lock, so it is not retried.
    db_path.write_bytes(b"this is not a sqlite database" * 100)

    response = client.get("/health")

    assert_problem(response, 500, "UNAVAILABLE")
    assert response.json()["detail"] == "Internal server error"
    assert "Retry-After" not in response.headers
    assert "not a sqlite database" not in response.text


def test_unexpected_error_returns_500_without_leaking_message(
    client_no_reraise, monkeypatch, assert_problem
):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "list_rows", boom)

    response = client_no_reraise.get("/v1/farms")

    assert_problem(response, 500, "UNAVAILABLE")
    assert response.json()["detail"] == "Internal server error"
    assert "boom" not in response.text


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
