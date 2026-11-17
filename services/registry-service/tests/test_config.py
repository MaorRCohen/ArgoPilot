import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

import config
import db

SERVICE_DIR = Path(config.__file__).resolve().parent
SECRET_URL = "postgresql+psycopg://registry_app:hunter2@127.0.0.1:5432/registry"


def load(env_file: Path) -> config.Settings:
    return config.load_settings(env_file=env_file)


def no_env_file(tmp_path: Path) -> Path:
    # A path that does not exist: only real environment variables count.
    return tmp_path / "missing.env"


def run_python(code: str, cwd: Path, env_overrides: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(SERVICE_DIR), **env_overrides}
    return subprocess.run(
        [sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True
    )


def test_missing_database_url_is_named(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(config.SettingsError, match="DATABASE_URL: missing"):
        load(no_env_file(tmp_path))


@pytest.mark.parametrize(
    "url", ["", "registry.db", "mysql://u:secret@h/db", "postgres://u:secret@h/db"]
)
def test_bad_database_url_is_refused_without_printing_it(monkeypatch, tmp_path, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(config.SettingsError, match="DATABASE_URL") as info:
        load(no_env_file(tmp_path))
    assert "secret" not in str(info.value)


@pytest.mark.parametrize("url", ["postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"])
def test_good_database_url_is_accepted(monkeypatch, tmp_path, url):
    monkeypatch.setenv("DATABASE_URL", url)
    assert load(no_env_file(tmp_path)).database_url.get_secret_value() == url


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:////abs/registry.db",
        "sqlite:///:memory:",
        "sqlite://",
        "postgresql+psycopg://registry_app:hunter2@127.0.0.1:5432/registry",
    ],
)
def test_absolute_memory_and_postgres_urls_are_unchanged(monkeypatch, tmp_path, url):
    monkeypatch.setenv("DATABASE_URL", url)
    assert load(no_env_file(tmp_path)).database_url.get_secret_value() == url


def test_relative_sqlite_path_resolves_to_the_service_folder(monkeypatch, tmp_path):
    # Working directory is unrelated: the file must still land in the service folder.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///registry.db")
    resolved = load(no_env_file(tmp_path)).database_url.get_secret_value()
    assert resolved == f"sqlite:///{SERVICE_DIR / 'registry.db'}"


def test_relative_owner_sqlite_path_resolves_to_the_service_folder(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:////abs/registry.db")
    monkeypatch.setenv("DATABASE_OWNER_URL", "sqlite:///owner.db")
    owner = load(no_env_file(tmp_path)).database_owner_url.get_secret_value()
    assert owner == f"sqlite:///{SERVICE_DIR / 'owner.db'}"


def test_relative_sqlite_path_keeps_its_query(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///registry.db?mode=ro")
    resolved = make_url(load(no_env_file(tmp_path)).database_url.get_secret_value())
    assert resolved.database == str(SERVICE_DIR / "registry.db")
    assert resolved.query == {"mode": "ro"}


def test_relative_sqlite_path_resolves_from_another_process(tmp_path):
    result = run_python(
        "import config; print(config.settings.database_url.get_secret_value())",
        tmp_path,
        {"DATABASE_URL": "sqlite:///registry.db"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"sqlite:///{SERVICE_DIR / 'registry.db'}"


def test_owner_url_is_optional_and_checked_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///registry.db")
    monkeypatch.delenv("DATABASE_OWNER_URL", raising=False)
    assert load(no_env_file(tmp_path)).database_owner_url is None
    monkeypatch.setenv("DATABASE_OWNER_URL", "ftp://owner:secret@h/db")
    with pytest.raises(config.SettingsError, match="DATABASE_OWNER_URL") as info:
        load(no_env_file(tmp_path))
    assert "secret" not in str(info.value)


def test_repr_and_dumps_hide_the_passwords(monkeypatch, tmp_path):
    owner = "postgresql+psycopg://registry_owner:hunter3@127.0.0.1:5432/registry"
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)
    monkeypatch.setenv("DATABASE_OWNER_URL", owner)
    settings = load(no_env_file(tmp_path))
    for text in (repr(settings), str(settings), settings.model_dump_json()):
        assert "hunter2" not in text
        assert "hunter3" not in text
    assert settings.database_url.get_secret_value() == SECRET_URL


def test_real_env_var_beats_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / "test.env"
    env_file.write_text("DATABASE_URL=sqlite:////from/dotenv.db\n")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////from/env.db")
    assert load(env_file).database_url.get_secret_value() == "sqlite:////from/env.db"


def test_env_file_is_used_when_no_env_var(monkeypatch, tmp_path):
    env_file = tmp_path / "test.env"
    env_file.write_text("DATABASE_URL=sqlite:////from/dotenv.db\n")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert load(env_file).database_url.get_secret_value() == "sqlite:////from/dotenv.db"


def test_env_file_is_next_to_config_not_the_working_directory():
    assert config.ENV_FILE == SERVICE_DIR / ".env"
    assert config.ENV_FILE.is_absolute()


def test_service_refuses_to_start_with_a_bad_url_and_does_not_print_it(tmp_path):
    result = run_python("import db", tmp_path, {"DATABASE_URL": "mysql://u:secret@h/db"})
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "DATABASE_URL" in output
    assert "secret" not in output


def test_startup_log_is_visible_at_import_and_has_scheme_only(tmp_path):
    result = run_python("import db", tmp_path, {"DATABASE_URL": "postgresql+psycopg://u:secret@h/db"})
    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    assert "Using database: postgresql" in output
    assert "secret" not in output


def test_env_var_sets_the_engine_in_a_fresh_process(tmp_path):
    env_db = tmp_path / "from_env.db"
    result = run_python(
        "import db; print(db.engine.url.database)", tmp_path, {"DATABASE_URL": f"sqlite:///{env_db}"}
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"file:{env_db}"


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


def test_engine_points_at_the_temp_file_from_conftest():
    path = Path(db.engine.url.database.removeprefix("file:"))
    assert Path(tempfile.gettempdir()) in path.parents
