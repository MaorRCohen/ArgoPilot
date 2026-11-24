import os
import runpy
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

import config
import setup_db
from config import SettingsError
from setup_db import run_setup

SERVICE_DIR = Path(__file__).resolve().parent.parent
SETUP_SCRIPT = SERVICE_DIR / "setup_db.py"
TABLES = ["farms", "crops", "soils", "emitters", "plots"]


def run_cli(tmp_path: Path, owner_url: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'app.db'}",
        "DATABASE_OWNER_URL": owner_url,
    }
    return subprocess.run(
        [sys.executable, str(SETUP_SCRIPT)],
        cwd=SERVICE_DIR, env=env, capture_output=True, text=True, timeout=60,
    )


def table_names(path: Path) -> list[str]:
    with closing(sqlite3.connect(path)) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return sorted(name for (name,) in rows)


def snapshot(path: Path) -> dict[str, tuple[list[str], list[tuple]]]:
    # Column names and every row, per table, in a fixed order.
    with closing(sqlite3.connect(path)) as conn:
        out = {}
        for table in TABLES:
            cursor = conn.execute(f"SELECT * FROM {table} ORDER BY id")
            columns = [column[0] for column in cursor.description]
            out[table] = (columns, cursor.fetchall())
    return out


def total_rows(path: Path) -> int:
    return sum(len(rows) for _columns, rows in snapshot(path).values())


def test_empty_database_gets_five_tables_and_fifteen_rows(tmp_path):
    db = tmp_path / "empty.db"

    result = run_cli(tmp_path, f"sqlite:///{db}")

    assert result.returncode == 0, result.stderr
    assert table_names(db) == sorted(TABLES)
    assert total_rows(db) == 15
    assert "total: 15" in result.stdout


def test_running_twice_keeps_fifteen_rows(tmp_path):
    db = tmp_path / "twice.db"
    url = f"sqlite:///{db}"

    first = run_cli(tmp_path, url)
    second = run_cli(tmp_path, url)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert total_rows(db) == 15


def test_same_rows_as_seed_registry_sh(tmp_path, template_db):
    # template_db is the database built by running seed_registry.sh in a temp folder.
    db = tmp_path / "setup.db"

    run_setup(f"sqlite:///{db}")

    assert snapshot(db) == snapshot(template_db)


def test_failure_in_the_middle_saves_nothing(tmp_path, monkeypatch):
    db = tmp_path / "failed.db"
    # The last table fails its foreign key after the other four tables were written.
    plots = setup_db.SEED_ROWS["plots"]
    broken = {**setup_db.SEED_ROWS, "plots": [*plots[:3], {**plots[3], "crop_id": "no-such-crop"}]}
    monkeypatch.setattr(setup_db, "SEED_ROWS", broken)

    with pytest.raises(IntegrityError):
        run_setup(f"sqlite:///{db}")

    assert table_names(db) == []  # not even the tables were kept


def test_missing_owner_url_is_named_and_password_never_printed(tmp_path):
    secret = "hunter2-SECRET"
    env = {
        **os.environ,
        "DATABASE_URL": f"postgresql+psycopg://registry_app:{secret}@127.0.0.1:5432/registry",
        # Empty overrides any .env file, so the command can never reach a real database.
        "DATABASE_OWNER_URL": "",
    }

    result = subprocess.run(
        [sys.executable, str(SETUP_SCRIPT)],
        cwd=SERVICE_DIR, env=env, capture_output=True, text=True, timeout=60,
    )

    assert result.returncode == 1
    assert "DATABASE_OWNER_URL" in result.stderr
    assert secret not in result.stdout + result.stderr


def test_postgres_engine_gets_no_sqlite_hooks():
    # create_engine does not connect, so no database is touched here.
    engine = setup_db.make_engine("postgresql+psycopg://u:p@localhost:1/none")

    assert engine.dialect.name == "postgresql"
    engine.dispose()


def test_main_names_a_missing_database_url(monkeypatch, capsys):
    def no_settings():
        raise SettingsError("DATABASE_URL: missing")

    monkeypatch.setattr(setup_db, "get_settings", no_settings)

    assert setup_db.main() == 1
    assert "DATABASE_URL: missing" in capsys.readouterr().err


def test_main_without_owner_url_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(setup_db, "get_settings", lambda: SimpleNamespace(database_owner_url=None))

    assert setup_db.main() == 1
    assert "DATABASE_OWNER_URL is not set" in capsys.readouterr().err


def test_main_prints_counts_for_a_good_setup(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'main.db'}"
    monkeypatch.setattr(
        setup_db, "get_settings", lambda: SimpleNamespace(database_owner_url=SecretStr(url))
    )

    assert setup_db.main() == 0
    assert "total: 15" in capsys.readouterr().out
    assert total_rows(tmp_path / "main.db") == 15


def test_main_reports_a_failed_setup_and_saves_nothing(tmp_path, monkeypatch, capsys):
    db = tmp_path / "failed-main.db"
    plots = setup_db.SEED_ROWS["plots"]
    broken = {**setup_db.SEED_ROWS, "plots": [*plots[:3], {**plots[3], "crop_id": "no-such-crop"}]}
    monkeypatch.setattr(setup_db, "SEED_ROWS", broken)
    monkeypatch.setattr(
        setup_db, "get_settings", lambda: SimpleNamespace(database_owner_url=SecretStr(f"sqlite:///{db}"))
    )

    assert setup_db.main() == 1
    assert "Setup failed, nothing was saved" in capsys.readouterr().err
    assert table_names(db) == []


def test_script_entry_point_exits_with_main_result(monkeypatch):
    # Runs setup_db.py as a script in this process. The owner URL is unset, so nothing is connected.
    monkeypatch.setattr(config, "_settings", SimpleNamespace(database_owner_url=None))

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(SETUP_SCRIPT), run_name="__main__")

    assert exit_info.value.code == 1
