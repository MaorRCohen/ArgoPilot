"""HTTP clients for the registry-service and the weather-service. One call per request, no retries."""

import asyncio
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ValidationError

from models import RegistryEmitter, RegistryPlot, RegistrySoil, WeatherForecast


class UpstreamError(Exception):
    """A service did not give a usable answer. `service` is named in the 503 detail."""

    def __init__(self, service: str, reason: str, retry_after_s: int | None = None):
        super().__init__(f"{service}: {reason}")
        self.service = service
        self.reason = reason
        self.retry_after_s = retry_after_s


class PlotNotFound(Exception):
    pass


class Upstream:
    def __init__(self, name: str, base_url: str, timeout_s: float, http: httpx.AsyncClient):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.http = http

    async def get(self, path: str, params: dict | None = None) -> httpx.Response:
        """One GET. A 5xx, a timeout or a connection problem is UpstreamError. Other statuses are returned."""
        try:
            # httpx limits each phase; asyncio.timeout limits the whole call.
            async with asyncio.timeout(self.timeout_s):
                response = await self.http.get(self.base_url + path, params=params, timeout=self.timeout_s)
        except TimeoutError:
            raise UpstreamError(self.name, "did not answer in time") from None
        except httpx.TimeoutException:
            raise UpstreamError(self.name, "did not answer in time") from None
        except httpx.HTTPError:
            raise UpstreamError(self.name, "cannot be reached") from None
        if response.status_code >= 500:
            retry_after = response.headers.get("Retry-After", "")
            raise UpstreamError(
                self.name, f"answered {response.status_code}", int(retry_after) if retry_after.isdigit() else None
            )
        return response

    def parse(self, response: httpx.Response, model: type[BaseModel]):
        if response.status_code != 200:
            raise UpstreamError(self.name, f"answered {response.status_code}")
        try:
            return model.model_validate_json(response.content)
        except ValidationError:
            raise UpstreamError(self.name, "sent an answer we cannot use") from None


class RegistryClient(Upstream):
    async def get_plot(self, plot_id: str) -> RegistryPlot:
        # quote: an id with "/" or ".." must stay one path segment.
        response = await self.get(f"/v1/plots/{quote(plot_id, safe='')}")
        if response.status_code == 404:
            raise PlotNotFound
        return self.parse(response, RegistryPlot)

    async def get_soil(self, soil_id: str) -> RegistrySoil:
        return self.parse(await self.get(f"/v1/soils/{quote(soil_id, safe='')}"), RegistrySoil)

    async def get_emitter(self, emitter_id: str) -> RegistryEmitter:
        return self.parse(await self.get(f"/v1/emitters/{quote(emitter_id, safe='')}"), RegistryEmitter)


class WeatherClient(Upstream):
    async def get_forecast(self, lat: float, lon: float, days: int) -> WeatherForecast:
        response = await self.get("/v1/forecast", {"lat": lat, "lon": lon, "days": days})
        forecast = self.parse(response, WeatherForecast)
        dates = [d.date for d in forecast.days]
        if len(dates) != days or any((b - a).days != 1 for a, b in zip(dates, dates[1:])):
            # A short or gappy forecast would be filled with nothing: refuse it (FR-2.14).
            raise UpstreamError(self.name, f"did not send {days} consecutive days")
        return forecast
