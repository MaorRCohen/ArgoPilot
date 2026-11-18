"""The only module that knows Open-Meteo: its parameters, its field names and its units.

Anything unexpected in an answer is a ProviderError, never a default. A forecast of zeros
would read as "no water needed" (FR-2.8).
"""

import asyncio
import logging
import math
import random
from email.utils import parsedate_to_datetime
from asyncio import sleep
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx

from config import Settings
from grid import cell_key
from models import ForecastDay

logger = logging.getLogger(__name__)
# httpx logs every request at INFO with its full URL, and the API key is in that URL's query string.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

# Worth another try: the provider or the network may be fine a moment later. Any other status
# (400, 401, 403, 404, 422 ...) means the request is wrong, and no retry can fix that.
RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}
RETRY_AFTER_STATUSES = {429, 503}

# ET0 (FAO-56 Penman-Monteith), the liquid water that reaches the soil (rain plus showers, no snow),
# and the mean wind at 10 m and the minimum relative humidity at 2 m that the planner needs for
# the FAO-56 climate adjustment of Kc. This service only fetches and checks them.
ET0, RAIN, SHOWERS, WIND, RH_MIN = (
    "et0_fao_evapotranspiration",
    "rain_sum",
    "showers_sum",
    "wind_speed_10m_mean",
    "relative_humidity_2m_min",
)
DAILY_VARIABLES = (ET0, RAIN, SHOWERS, WIND, RH_MIN)
UNITS = {ET0: "mm", RAIN: "mm", SHOWERS: "mm", WIND: "m/s", RH_MIN: "%"}
MAX_UTC_OFFSET_S = 24 * 3600


class ProviderError(Exception):
    """The provider gave no usable forecast. The text names the problem, never the URL: it holds the API key.

    retryable: another attempt may work. retry_after_s: what the provider asked for, if it did.
    """

    def __init__(self, message: str, *, retryable: bool = True, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.retry_after_s = retry_after_s


@dataclass(frozen=True)
class Forecast:
    """Every day the provider gave, from its local today on, and when they were fetched."""

    days: tuple[ForecastDay, ...]
    utc_offset_s: int  # to find "today" at the point later, without a time zone database
    fetched_at: datetime


def jitter(upper: float) -> float:
    """Full jitter: a random wait between 0 and `upper`, so retries from many callers do not line up."""
    return random.uniform(0, upper)


class OpenMeteoClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http

    async def fetch(self, lat: float, lon: float) -> Forecast:
        """One forecast, or ProviderError. The only place in the system that retries (FR-2.6)."""
        settings = self._settings
        deadline = datetime.now(UTC) + timedelta(seconds=settings.provider_total_budget_s)
        # An attempt with less time than this cannot finish a round trip, so it is not started.
        shortest = settings.provider_timeout_s / 2
        failure = ProviderError("no attempt was made")
        attempts = settings.provider_retries + 1
        cell = cell_key(lat, lon)
        asked_to_wait: float | None = None
        for attempt in range(attempts):
            if attempt > 0:
                wait = jitter(settings.backoff_base_s * 2 ** (attempt - 1))
                if failure.retry_after_s is not None:
                    wait = max(wait, failure.retry_after_s)  # the provider asked for more time
                if _seconds_left(deadline) - wait < shortest:  # includes a Retry-After longer than the budget
                    break
                await sleep(wait)
            timeout = min(settings.provider_timeout_s, _seconds_left(deadline))
            if attempt > 0 and timeout < shortest:  # the wait took longer than planned
                break
            try:
                return await self._attempt(lat, lon, timeout)
            except ProviderError as exc:
                # The reason never holds the URL or the key (see ProviderError).
                logger.warning("attempt failed cell=%s attempt %d/%d reason=%s", cell, attempt + 1, attempts, exc)
                failure = exc
                if exc.retry_after_s is not None:
                    asked_to_wait = max(asked_to_wait or 0, exc.retry_after_s)
                if not exc.retryable:
                    break
        failure.retry_after_s = asked_to_wait
        raise failure

    async def _attempt(self, lat: float, lon: float, timeout: float) -> Forecast:
        try:
            # asyncio.timeout is the hard limit for the whole attempt; httpx's own timeouts are per step.
            async with asyncio.timeout(timeout):
                response = await self._http.get(
                    str(self._settings.open_meteo_base_url), params=self._params(lat, lon), timeout=timeout
                )
        except (httpx.HTTPError, TimeoutError) as exc:
            # httpx puts the URL, with the API key, into its messages: only the kind of error goes on.
            raise ProviderError(f"request failed: {type(exc).__name__}") from None
        if not response.is_success:
            status = response.status_code
            raise ProviderError(
                f"HTTP status {status}",
                retryable=status in RETRYABLE_STATUSES,
                retry_after_s=_retry_after_s(response) if status in RETRY_AFTER_STATUSES else None,
            )
        try:
            payload = response.json()
        except ValueError:
            raise ProviderError("body is not JSON") from None
        days, utc_offset_s = parse_forecast(payload, self._settings.forecast_fetch_days)
        return Forecast(days, utc_offset_s, datetime.now(UTC).replace(microsecond=0))

    def _params(self, lat: float, lon: float) -> dict[str, str | float | int]:
        params: dict[str, str | float | int] = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "auto",  # local days, anywhere in the world
            "precipitation_unit": "mm",
            "wind_speed_unit": "ms",
            "forecast_days": self._settings.forecast_fetch_days,
        }
        api_key = self._settings.open_meteo_api_key.get_secret_value()
        if api_key:
            params["apikey"] = api_key
        return params


def _retry_after_s(response: httpx.Response) -> float | None:
    """The provider's Retry-After: seconds, or an HTTP date. None if absent or unreadable."""
    value = response.headers.get("retry-after", "").strip()
    try:
        return max(0.0, float(value)) if value and math.isfinite(float(value)) else None
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def _seconds_left(deadline: datetime) -> float:
    return (deadline - datetime.now(UTC)).total_seconds()


def parse_forecast(payload: object, expected_days: int) -> tuple[tuple[ForecastDay, ...], int]:
    body = _object(payload, "body")
    daily = _object(body.get("daily"), "daily")
    units = _object(body.get("daily_units"), "daily_units")
    utc_offset_s = body.get("utc_offset_seconds")
    if isinstance(utc_offset_s, bool) or not isinstance(utc_offset_s, int) or abs(utc_offset_s) > MAX_UTC_OFFSET_S:
        raise ProviderError("utc_offset_seconds is missing or not a UTC offset")
    for name in DAILY_VARIABLES:
        if units.get(name) != UNITS[name]:
            raise ProviderError(f"daily_units.{name} is missing or not {UNITS[name]}")

    lists = {name: _list(daily.get(name), f"daily.{name}") for name in ("time", *DAILY_VARIABLES)}
    if any(len(values) != expected_days for values in lists.values()):
        raise ProviderError(f"daily lists are not all {expected_days} days long")
    dates = [_date(value) for value in lists["time"]]
    if any(after - before != timedelta(days=1) for before, after in zip(dates, dates[1:])):
        raise ProviderError("daily.time is not consecutive days")

    et0 = [_amount(value, f"daily.{ET0}") for value in lists[ET0]]
    rain = [_amount(value, f"daily.{RAIN}") for value in lists[RAIN]]
    showers = [_amount(value, f"daily.{SHOWERS}") for value in lists[SHOWERS]]
    wind = [_amount(value, f"daily.{WIND}") for value in lists[WIND]]
    rh_min = [_amount(value, f"daily.{RH_MIN}", maximum=100) for value in lists[RH_MIN]]
    days = tuple(
        # Open-Meteo gives at most 2 decimals: the rounding only removes float noise (0.2 + 0.1).
        ForecastDay(
            date=day,
            et0_mm=et0_mm,
            rain_mm=round(rain_mm + showers_mm, 2),
            wind_10m_ms=round(wind_ms, 2),
            rh_min_pct=round(rh_pct, 2),
        )
        for day, et0_mm, rain_mm, showers_mm, wind_ms, rh_pct in zip(dates, et0, rain, showers, wind, rh_min)
    )
    return days, utc_offset_s


def _object(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise ProviderError(f"{where} is missing or not an object")
    return value


def _list(value: object, where: str) -> list:
    if not isinstance(value, list):
        raise ProviderError(f"{where} is missing or not a list")
    return value


def _date(value: object) -> date:
    if not isinstance(value, str):
        raise ProviderError("daily.time has a value that is not text")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ProviderError("daily.time has a value that is not a date") from None


def _amount(value: object, where: str, maximum: float | None = None) -> float:
    # True is an int in Python and would become 1 mm of water.
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ProviderError(f"{where} has a value that is not a number (null included)")
    try:
        amount = float(value)
    except OverflowError:
        raise ProviderError(f"{where} has a value that is too large") from None
    if not math.isfinite(amount) or amount < 0:
        raise ProviderError(f"{where} has a negative or not finite value")
    if maximum is not None and amount > maximum:
        raise ProviderError(f"{where} has a value above {maximum}")
    return amount
