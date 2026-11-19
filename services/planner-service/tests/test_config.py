from pathlib import Path

import pytest

import config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in config.Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def load(tmp_path: Path) -> config.Settings:
    return config.load_settings(env_file=tmp_path / "missing.env")


@pytest.mark.parametrize("name", ["REGISTRY_URL", "WEATHER_URL"])
def test_missing_required_url_is_named(monkeypatch, tmp_path, name):
    other = "WEATHER_URL" if name == "REGISTRY_URL" else "REGISTRY_URL"
    monkeypatch.setenv(other, "http://127.0.0.1:9")
    with pytest.raises(config.SettingsError, match=f"{name}: missing"):
        load(tmp_path)


def test_defaults_are_the_decided_values(monkeypatch, tmp_path):
    monkeypatch.setenv("REGISTRY_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("WEATHER_URL", "http://127.0.0.1:8001")
    s = load(tmp_path)
    assert (s.registry_timeout_s, s.weather_timeout_s, s.uniformity_factor, s.retry_after_s) == (1.0, 4.5, 1.1, 30)
    assert s.max_run_minutes_per_day == 1440
    assert s.crop_profiles_path == config.SERVICE_DIR / "crop_profiles.json"


@pytest.mark.parametrize("name, value", [("REGISTRY_TIMEOUT_S", "0"), ("WEATHER_TIMEOUT_S", "-1"),
                                         ("UNIFORMITY_FACTOR", "0.5"), ("MAX_RUN_MINUTES_PER_DAY", "0"), ("REGISTRY_URL", "nope")])
def test_bad_value_is_refused_by_name_without_printing_it(monkeypatch, tmp_path, name, value):
    monkeypatch.setenv("REGISTRY_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("WEATHER_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv(name, value)
    with pytest.raises(config.SettingsError, match=name) as info:
        load(tmp_path)
    assert f"'{value}'" not in str(info.value)
