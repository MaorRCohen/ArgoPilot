import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import time_machine
from fastapi.testclient import TestClient

# Must run before `import db` / `import main`: db.py builds its engine at import. A real env var beats .env,
# so tests can never reach the real registry.db or a real Postgres through a developer's .env.
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp(prefix='registry-test-')) / 'registry.db'}"

import db  # noqa: E402
from main import app  # noqa: E402
from tests.pg_guard import assert_safe_to_wipe  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")  # set -> Postgres mode

SERVICE_DIR = Path(__file__).parent.parent
SEED_SCRIPT = SERVICE_DIR / "seed_registry.sh"
SEED_PG = SERVICE_DIR / "seed_registry_pg.sql"

# Every test runs at this moment. It is 22:00 UTC on Nov 3: already Nov 4 in Tokyo, still Nov 3 in London.
NOW = datetime(2026, 11, 3, 22, 0, tzinfo=UTC)


def pytest_configure(config):
    config.addinivalue_line("markers", "postgres_only: needs TEST_DATABASE_URL (a local Postgres test database)")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if TEST_DATABASE_URL and "sqlite_only" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="SQLite-only test, running in Postgres mode"))
        if not TEST_DATABASE_URL and "postgres_only" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="needs TEST_DATABASE_URL"))


@pytest.fixture(scope="session")
def template_db(tmp_path_factory) -> Path:
    # Build the seeded DB once. The seed script runs in a temp dir, never in the service dir,
    # so its "rm -f registry.db" can never touch the real database.
    work_dir = tmp_path_factory.mktemp("seed")
    shutil.copy(SEED_SCRIPT, work_dir / "seed_registry.sh")
    subprocess.run(["bash", "seed_registry.sh"], cwd=work_dir, check=True)
    return work_dir / "registry.db"


@pytest.fixture(autouse=True)
def frozen_clock():
    with time_machine.travel(NOW, tick=True):
        yield


@pytest.fixture
def db_path(template_db, tmp_path, monkeypatch) -> Path:
    # A fresh copy per test, and the real get_db() runs against it (mode=rw, timeout=5, foreign_keys).
    path = tmp_path / "registry.db"
    shutil.copy(template_db, path)
    monkeypatch.setattr(db, "engine", db.make_engine(f"sqlite:///{path}"))
    return path


@pytest.fixture
def backend(request, monkeypatch):
    # SQLite mode: a fresh temp DB copy (db_path). Postgres mode: wipe the public schema, reseed, patch db.engine.
    if not TEST_DATABASE_URL:
        request.getfixturevalue("db_path")
        yield
        return
    assert_safe_to_wipe(TEST_DATABASE_URL)
    engine = db.make_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.exec_driver_sql(SEED_PG.read_text())
    monkeypatch.setattr(db, "engine", engine)
    yield
    engine.dispose()


@pytest.fixture
def client(backend) -> TestClient:
    return TestClient(app)


@pytest.fixture
def assert_problem():
    # Checks an error response: status, problem+json content type, and the code field.
    def check(response, status: int, code: str) -> None:
        assert response.status_code == status
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["code"] == code

    return check
