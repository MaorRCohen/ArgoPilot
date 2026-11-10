import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import db


def test_unset_or_empty_url_uses_default_sqlite(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env here
    expected = f"sqlite:///{db.DEFAULT_SQLITE_PATH}"
    assert db.DEFAULT_SQLITE_PATH == Path(db.__file__).parent / "registry.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.database_url() == expected
    monkeypatch.setenv("DATABASE_URL", "")
    assert db.database_url() == expected


def test_real_env_var_beats_dotenv(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("DATABASE_URL=sqlite:////from/dotenv.db\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:////from/env.db")
    assert db.database_url() == "sqlite:////from/env.db"


def test_log_has_scheme_only(caplog):
    url = "postgresql+psycopg://u:secret@h/db"
    assert db.scheme_of(url) == "postgresql"
    assert db.scheme_of("sqlite:///x.db") == "sqlite"
    with caplog.at_level(logging.INFO):
        engine = db.make_engine(url)
        db.log_database(url)
    assert engine.url.drivername == "postgresql+psycopg"
    assert "secret" not in caplog.text
    assert "u:secret" not in caplog.text
    assert "postgresql" in caplog.text


def test_sqlite_engine_is_mode_rw_and_missing_file_raises(tmp_path):
    engine = db.make_engine(f"sqlite:///{tmp_path / 'missing.db'}")
    try:
        engine.connect()
    except Exception:
        pass
    else:
        raise AssertionError("missing file must raise")
    assert not (tmp_path / "missing.db").exists()


def test_engine_is_a_temp_file_not_the_default_sqlite():
    path = Path(db.engine.url.database.removeprefix("file:"))
    assert path != db.DEFAULT_SQLITE_PATH
    assert Path(tempfile.gettempdir()) in path.parents


SERVICE_DIR = Path(db.__file__).parent


def run_child(code: str, cwd: Path, database_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": str(SERVICE_DIR)}
    return subprocess.run(
        [sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, check=True
    )


def test_startup_log_is_visible_at_import_and_has_scheme_only(tmp_path):
    result = run_child("import db", tmp_path, "postgresql+psycopg://u:secret@h/db")
    output = result.stdout + result.stderr
    assert "Using database: postgresql" in output
    assert "secret" not in output


def test_real_env_var_wins_over_a_real_dotenv_in_a_fresh_process(tmp_path):
    (tmp_path / ".env").write_text(f"DATABASE_URL=sqlite:///{tmp_path / 'from_dotenv.db'}\n")
    env_db = tmp_path / "from_env.db"
    result = run_child("import db; print(db.engine.url.database)", tmp_path, f"sqlite:///{env_db}")
    assert result.stdout.strip() == f"file:{env_db}"
