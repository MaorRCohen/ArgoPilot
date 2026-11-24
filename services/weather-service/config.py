"""The only place that reads settings. Values are checked once, at startup."""

from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Next to this file, so the same path is found from any working directory.
SERVICE_DIR = Path(__file__).resolve().parent
ENV_FILE = SERVICE_DIR / ".env"


class SettingsError(RuntimeError):
    """Startup is refused. The message names the variables and never prints a value."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # The only required variable: where the provider lives is not a decision for the code.
    open_meteo_base_url: AnyHttpUrl
    # Empty means the free tier: no key is sent.
    open_meteo_api_key: SecretStr = SecretStr("")
    # One attempt, and all attempts together (seconds).
    provider_timeout_s: float = Field(default=1.5, gt=0)
    provider_total_budget_s: float = Field(default=4, gt=0)
    # Retries after the first attempt, and the base of the jittered exponential wait between them.
    provider_retries: int = Field(default=2, ge=0)
    backoff_base_s: float = Field(default=0.2, ge=0)
    # Fresh: served without a provider call. Max stale: the oldest forecast served when the provider fails.
    fresh_for_s: float = Field(default=3 * 3600, gt=0)
    max_stale_s: float = Field(default=24 * 3600, gt=0)
    # After a cell failed, the provider is left alone for it this long.
    failure_cooldown_s: float = Field(default=30, ge=0)
    cache_max_cells: int = Field(default=10_000, ge=1)
    # Today + 7: even a 24 h old forecast still covers 7 days from today.
    forecast_fetch_days: int = Field(default=8, ge=7, le=16)


def load_settings(env_file: Path = ENV_FILE) -> Settings:
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        # str(exc) prints the rejected values, so the message is built from names and rules only.
        problems = []
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            name = ".".join(str(part) for part in error["loc"]).upper()
            if error["type"] == "missing":
                problems.append(f"{name}: missing")
            else:
                problems.append(f"{name}: {error['msg']}")
        raise SettingsError(
            "Invalid settings for weather-service (see .env.example):\n  " + "\n  ".join(problems)
        ) from None


_settings: Settings | None = None


def get_settings() -> Settings:
    # Read on first use, not at import, so tests can build their own settings first.
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
