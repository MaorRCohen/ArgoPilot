"""A ForecastService on a FakeProvider, driven from plain (sync) tests."""

import asyncio

import httpx

from forecast import ForecastService
from provider import OpenMeteoClient
from tests.fakes import FakeProvider, make_settings


class Harness:
    """One event loop for the whole test, so the service keeps its state between requests."""

    def __init__(self, **settings) -> None:
        self.fake = FakeProvider()
        self._http = httpx.AsyncClient(transport=httpx.MockTransport(self.fake))
        config = make_settings(**settings)
        self.service = ForecastService(config, OpenMeteoClient(config, self._http))
        self._runner = asyncio.Runner()

    def run(self, coroutine):
        return self._runner.run(coroutine)

    def get(self, lat: float = 31.25, lon: float = 34.75, days: int = 7):
        return self.run(self.service.get(lat, lon, days))

    def close(self) -> None:
        self._runner.run(self._http.aclose())
        self._runner.close()
