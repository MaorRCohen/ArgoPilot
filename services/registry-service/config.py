"""The only place that reads settings. Values are checked once, at startup."""

from pathlib import Path

from pydantic import SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

# Next to this file, so it is found from any working directory.
ENV_FILE = Path(__file__).resolve().parent / ".env"
# SQLAlchemy backend names. "postgresql+psycopg" has backend "postgresql".
ALLOWED_BACKENDS = ("sqlite", "postgresql")
URL_RULE = "must start with sqlite:// or postgresql:// (a +driver suffix is allowed)"


class SettingsError(RuntimeError):
    """Startup is refused. The message names the variables and never prints a value."""


def _check_url(value: SecretStr) -> SecretStr:
    try:
        backend = make_url(value.get_secret_value()).get_backend_name()
    except ArgumentError:
        # make_url's own message contains the URL, so it is replaced here, not chained.
        raise ValueError(URL_RULE) from None
    if backend not in ALLOWED_BACKENDS:
        raise ValueError(URL_RULE)
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: SecretStr
    # Only the setup/seed command and Postgres tests use it. The API never reads it.
    database_owner_url: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, value: SecretStr) -> SecretStr:
        return _check_url(value)

    @field_validator("database_owner_url")
    @classmethod
    def _check_database_owner_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():  # empty counts as not set
            return None
        return _check_url(value)


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
                problems.append(f"{name}: {error['msg'].removeprefix('Value error, ')}")
        raise SettingsError(
            "Invalid settings for registry-service (see .env.example):\n  " + "\n  ".join(problems)
        ) from None


settings = load_settings()
