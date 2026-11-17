"""The real app, started with TestClient, on a FakeProvider."""

import httpx
from fastapi.testclient import TestClient

from tests.fakes import FakeProvider, make_settings


class Api:
    def __init__(self, raise_server_exceptions: bool = True, **settings) -> None:
        from main import create_app

        self.fake = FakeProvider()
        app = create_app(make_settings(**settings), httpx.MockTransport(self.fake))
        # Entering the TestClient runs the app's startup, and keeps one event loop for the whole test.
        self._test_client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
        self.client = self._test_client.__enter__()

    def forecast(self, lat=31.25, lon=34.79, days=7, **params) -> httpx.Response:
        return self.client.get("/v1/forecast", params={"lat": lat, "lon": lon, "days": days, **params})

    def close(self) -> None:
        self._test_client.__exit__(None, None, None)
