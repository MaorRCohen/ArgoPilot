import asyncio
import datetime as dt
import json
from pathlib import Path

import httpx

from config import Settings

NOW = dt.datetime(2026, 11, 18, 6, 0, tzinfo=dt.UTC)
SERVICE_DIR = Path(__file__).resolve().parent.parent
REGISTRY = "http://registry.test"
WEATHER = "http://weather.test"

PLOT = {
    "id": "p1", "farm_id": "f1", "name": "North block", "area_m2": 1000.0, "crop_id": "tomato",
    "planting_date": "2026-08-30", "soil_id": "loam", "row_spacing_m": 1.5, "emitter_spacing_m": 0.4,
    "emitter_id": "drip1", "lat": 31.25, "lon": 34.79,
}
SOIL = {"id": "loam", "name": "Loam", "available_water_mm_per_m": 175}
EMITTER = {"id": "drip1", "name": "Drip 1 L/h", "flow_lph": 1.0}

HANG = object()  # an answer that never comes


def forecast_body(days=3, stale=False, **day):
    return {
        "lat": 31.25, "lon": 34.79, "source": "open-meteo", "fetched_at": "2026-11-18T03:00:00Z", "stale": stale,
        "days": [{"date": f"2026-11-{18 + i}", "et0_mm": 5.0, "rain_mm": 0.0, "wind_10m_ms": 2.67,
                  "rh_min_pct": 45.0, **day} for i in range(days)],
    }


def make_settings(**overrides) -> Settings:
    values = {"registry_url": REGISTRY, "weather_url": WEATHER, **overrides}
    return Settings(_env_file=None, **values)


class FakeUpstreams:
    """One MockTransport for both services. Each answer is a Response, or an exception to raise."""

    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.plot = httpx.Response(200, json=PLOT)
        self.soil = httpx.Response(200, json=SOIL)
        self.emitter = httpx.Response(200, json=EMITTER)
        self.weather = lambda request: httpx.Response(
            200, json=forecast_body(int(request.url.params["days"])))

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if request.url.host == "weather.test":
            answer = self.weather(request) if callable(self.weather) else self.weather
        elif path.startswith("/v1/plots/"):
            answer = self.plot
        elif path.startswith("/v1/soils/"):
            answer = self.soil
        elif path.startswith("/v1/emitters/"):
            answer = self.emitter
        else:
            raise AssertionError(f"unexpected call {request.url}")
        if answer is HANG:
            await asyncio.sleep(30)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def calls_to(self, host: str) -> list[httpx.Request]:
        return [c for c in self.calls if c.url.host == host]


def write_profiles(path: Path, mutate=None) -> Path:
    data = json.loads((SERVICE_DIR / "crop_profiles.json").read_text())
    if mutate:
        mutate(data)
    path.write_text(json.dumps(data))
    return path
