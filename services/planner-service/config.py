"""The only place that reads settings. Values are checked once, at startup."""

from pathlib import Path

from pydantic import AnyHttpUrl, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Next to this file, so the same path is found from any working directory.
SERVICE_DIR = Path(__file__).resolve().parent
ENV_FILE = SERVICE_DIR / ".env"


class SettingsError(RuntimeError):
    """Startup is refused. The message names the variables and never prints a value."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # Required: where the other services live is not a decision for the code.
    registry_url: AnyHttpUrl
    weather_url: AnyHttpUrl
    # Seconds to wait for one answer. No retries here: the weather-service is the only retry point.
    registry_timeout_s: float = Field(default=1.0, gt=0)
    # A bit above the weather-service's own 4 s budget, so its stale answer arrives before we give up.
    weather_timeout_s: float = Field(default=4.5, gt=0)
    # Retry-After on a 503 when the failed service did not send one.
    retry_after_s: int = Field(default=30, ge=1)
    # Extra litres for drip non-uniformity (1.1 = 10 %). Applied to irrigation only, never to rain.
    uniformity_factor: float = Field(default=1.1, ge=1)
    crop_profiles_path: Path = SERVICE_DIR / "crop_profiles.json"


def load_settings(env_file: Path = ENV_FILE) -> Settings:
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        # str(exc) prints the rejected values, so the message is built from names and rules only.
        problems = []
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            name = ".".join(str(part) for part in error["loc"]).upper()
            problems.append(f"{name}: missing" if error["type"] == "missing" else f"{name}: {error['msg']}")
        raise SettingsError(
            "Invalid settings for planner-service (see .env.example):\n  " + "\n  ".join(problems)
        ) from None


_settings: Settings | None = None


def get_settings() -> Settings:
    # Read on first use, not at import, so tests can build their own settings first.
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
