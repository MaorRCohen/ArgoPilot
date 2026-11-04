import pytest


def test_missing_db_file_returns_503_and_is_not_created(client, db_path, assert_problem):
    db_path.unlink()

    for path in ["/health", "/v1/farms"]:
        response = client.get(path)

        assert_problem(response, 503, "UNAVAILABLE")
        assert response.headers["Retry-After"] == "30"
        assert response.json()["detail"] == "Database unavailable"

    # mode=rw must fail instead of creating an empty registry.db.
    assert not db_path.exists()


def test_db_without_tables_returns_500_without_sqlite_text(client, db_path, assert_problem):
    db_path.write_bytes(b"")

    for path in ["/health", "/v1/farms"]:
        response = client.get(path)

        assert_problem(response, 500, "UNAVAILABLE")
        assert response.json()["detail"] == "Internal server error"
        assert "Retry-After" not in response.headers
        assert "sqlite" not in response.text.lower()
        assert "no such table" not in response.text
