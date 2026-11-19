import re
from pathlib import Path

import pytest

import config

SERVICE_DIR = Path(config.__file__).resolve().parent
URL = "https://open-meteo.test/v1/forecast"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # A developer's shell must not change these tests: only the variables a test sets count.
    for name in config.Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def no_env_file(tmp_path: Path) -> Path:
    # A path that does not exist: only real environment variables count.
    return tmp_path / "missing.env"


def load(tmp_path: Path) -> config.Settings:
    return config.load_settings(env_file=no_env_file(tmp_path))


def test_missing_base_url_is_named(tmp_path):
    with pytest.raises(config.SettingsError, match="OPEN_METEO_BASE_URL: missing"):
        load(tmp_path)


@pytest.mark.parametrize("url", ["", "open-meteo.com", "ftp://api.open-meteo.com/v1/forecast"])
def test_bad_base_url_is_refused_by_name(monkeypatch, tmp_path, url):
    monkeypatch.setenv("OPEN_METEO_BASE_URL", url)
    with pytest.raises(config.SettingsError, match="OPEN_METEO_BASE_URL"):
        load(tmp_path)


def test_defaults_are_the_decided_values(monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_METEO_BASE_URL", URL)
    settings = load(tmp_path)
    assert str(settings.open_meteo_base_url) == URL
    assert settings.open_meteo_api_key.get_secret_value() == ""  # empty = free tier
    assert settings.provider_timeout_s == 1.5
    assert settings.provider_retries == 2
    assert settings.backoff_base_s == 0.2
    assert settings.provider_total_budget_s == 4
    assert settings.fresh_for_s == 3 * 3600
    assert settings.max_stale_s == 24 * 3600
    assert settings.failure_cooldown_s == 30
    assert settings.cache_max_cells == 10_000
    assert settings.forecast_fetch_days == 8


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PROVIDER_TIMEOUT_S", "0"),
        ("PROVIDER_TIMEOUT_S", "abc"),
        ("PROVIDER_RETRIES", "-1"),
        ("BACKOFF_BASE_S", "-0.1"),
        ("PROVIDER_TOTAL_BUDGET_S", "0"),
        ("FRESH_FOR_S", "0"),
        ("MAX_STALE_S", "0"),
        ("FAILURE_COOLDOWN_S", "-1"),
        ("CACHE_MAX_CELLS", "0"),
        ("FORECAST_FETCH_DAYS", "6"),
        ("FORECAST_FETCH_DAYS", "17"),
    ],
)
def test_out_of_range_numbers_are_refused_by_name(monkeypatch, tmp_path, name, value):
    monkeypatch.setenv("OPEN_METEO_BASE_URL", URL)
    monkeypatch.setenv(name, value)
    with pytest.raises(config.SettingsError, match=name):
        load(tmp_path)


def test_api_key_is_a_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_METEO_BASE_URL", URL)
    monkeypatch.setenv("OPEN_METEO_API_KEY", "hunter2")
    settings = load(tmp_path)
    assert settings.open_meteo_api_key.get_secret_value() == "hunter2"
    for text in (repr(settings), str(settings), settings.model_dump_json()):
        assert "hunter2" not in text


def test_real_env_var_beats_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / "test.env"
    env_file.write_text("OPEN_METEO_BASE_URL=https://from-file.test/v1/forecast\nFRESH_FOR_S=100\n")
    monkeypatch.setenv("FRESH_FOR_S", "200")
    settings = config.load_settings(env_file=env_file)
    assert settings.fresh_for_s == 200
    assert str(settings.open_meteo_base_url) == "https://from-file.test/v1/forecast"


def test_env_file_is_next_to_config_not_the_working_directory():
    assert config.ENV_FILE == SERVICE_DIR / ".env"
    assert config.ENV_FILE.is_absolute()


def test_env_example_lists_every_setting_and_loads():
    text = (SERVICE_DIR / ".env.example").read_text()
    for name in config.Settings.model_fields:
        assert re.search(rf"^{name.upper()}=", text, re.MULTILINE), f"{name.upper()} missing in .env.example"
    example = config.load_settings(env_file=SERVICE_DIR / ".env.example")
    # The example shows the same values the code uses when a variable is not set.
    assert example == config.Settings(_env_file=None, open_meteo_base_url=example.open_meteo_base_url)
