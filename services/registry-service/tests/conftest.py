import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import time_machine
from fastapi.testclient import TestClient

import db
from main import app

SERVICE_DIR = Path(__file__).parent.parent
SEED_SCRIPT = SERVICE_DIR / "seed_registry.sh"

# Every test runs at this moment. It is 22:00 UTC on Nov 3: already Nov 4 in Tokyo, still Nov 3 in London.
NOW = datetime(2026, 11, 3, 22, 0, tzinfo=UTC)


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
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


@pytest.fixture
def client(db_path) -> TestClient:
    return TestClient(app)


@pytest.fixture
def assert_problem():
    # Checks an error response: status, problem+json content type, and the code field.
    def check(response, status: int, code: str) -> None:
        assert response.status_code == status
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["code"] == code

    return check
