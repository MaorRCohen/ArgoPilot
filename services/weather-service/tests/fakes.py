"""Test doubles. Nothing here reaches the internet."""

import asyncio
from datetime import UTC, date, datetime, timedelta

import httpx

from config import Settings
from provider import Forecast, OpenMeteoClient

# Every test starts at this moment: 10:00 in Israel (UTC+2), so local "today" is 2026-11-17.
NOW = datetime(2026, 11, 17, 8, 0, tzinfo=UTC)
BASE_URL = "https://open-meteo.test/v1/forecast"

# Every setting is given, so a variable in a developer's shell cannot change a test.
SETTINGS = dict(
    open_meteo_base_url=BASE_URL,
    open_meteo_api_key="",
    provider_timeout_s=1.5,
    provider_retries=2,
    backoff_base_s=0.2,
    provider_total_budget_s=4,
    fresh_for_s=3 * 3600,
    max_stale_s=24 * 3600,
    failure_cooldown_s=30,
    cache_max_cells=10_000,
    forecast_fetch_days=8,
)


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **{**SETTINGS, **overrides})


# Day 0 and 1 follow the spec example: ET0 3.1 and 2.8 mm, rain 0.0 and 4.2 mm.
ET0 = [3.1, 2.8, 3.4, 3.0, 2.9, 3.3, 3.5, 3.2]
RAIN_SUM = [0.0, 4.0, 0.0, 0.2, 0.0, 0.0, 1.0, 0.0]
SHOWERS_SUM = [0.0, 0.2, 0.0, 0.1, 0.0, 0.0, 0.5, 0.0]
WIND = [2.1, 3.4, 4.0, 2.8, 1.9, 3.0, 5.2, 2.5]  # mean wind at 10 m, m/s
RH_MIN = [35.0, 28.5, 22.0, 40.0, 55.5, 60.0, 30.0, 25.5]  # minimum relative humidity at 2 m, %
RAIN_MM = [0.0, 4.2, 0.0, 0.3, 0.0, 0.0, 1.5, 0.0]  # what the service must answer: rain_sum + showers_sum


def fetch(handler, lat: float = 31.25, lon: float = 34.75, **settings) -> Forecast:
    """One OpenMeteoClient.fetch against `handler`, run to the end. Raises ProviderError on failure."""

    async def run() -> Forecast:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await OpenMeteoClient(make_settings(**settings), http).fetch(lat, lon)

    return asyncio.run(run())


def local_today(utc_offset_s: int = 7200) -> date:
    return (datetime.now(UTC) + timedelta(seconds=utc_offset_s)).date()


def open_meteo_body(utc_offset_s: int = 7200, first_day: date | None = None, days: int = 8) -> dict:
    """What Open-Meteo answers with timezone=auto: the first day is today at the point."""
    first_day = first_day or local_today(utc_offset_s)
    return {
        "latitude": 31.25,
        "longitude": 34.75,
        "utc_offset_seconds": utc_offset_s,
        "timezone": "Asia/Jerusalem",
        "daily_units": {
            "time": "iso8601",
            "et0_fao_evapotranspiration": "mm",
            "rain_sum": "mm",
            "showers_sum": "mm",
            "wind_speed_10m_mean": "m/s",
            "relative_humidity_2m_min": "%",
        },
        "daily": {
            "time": [(first_day + timedelta(days=i)).isoformat() for i in range(days)],
            "et0_fao_evapotranspiration": [ET0[i % 8] for i in range(days)],
            "rain_sum": [RAIN_SUM[i % 8] for i in range(days)],
            "showers_sum": [SHOWERS_SUM[i % 8] for i in range(days)],
            "wind_speed_10m_mean": [WIND[i % 8] for i in range(days)],
            "relative_humidity_2m_min": [RH_MIN[i % 8] for i in range(days)],
        },
    }


class FakeProvider:
    """Open-Meteo for httpx.MockTransport. Records every request it gets.

    `script` holds what the next requests get, oldest first. When it is empty, `default` answers;
    None means a good, up to date body. An outcome is a body (dict), an httpx.Response, an exception
    to raise, or a function(request) returning one of those.
    """

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.script: list = []
        self.default = None
        self.gate: asyncio.Event | None = None  # while set and closed, requests wait (single-flight tests)
        self.delay_s = 0.0  # a real delay before every answer, so concurrent requests overlap

    @property
    def calls(self) -> int:
        return len(self.requests)

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.gate is not None:
            await self.gate.wait()
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        return self._respond(self.script.pop(0) if self.script else self.default, request)

    def _respond(self, outcome, request: httpx.Request) -> httpx.Response:
        if outcome is None:  # a good body with as many days as the request asked for, like the real API
            outcome = open_meteo_body(days=int(request.url.params["forecast_days"]))
        if isinstance(outcome, Exception):
            raise outcome
        if callable(outcome):
            return self._respond(outcome(request), request)
        if isinstance(outcome, httpx.Response):
            return outcome
        return httpx.Response(200, json=outcome)
