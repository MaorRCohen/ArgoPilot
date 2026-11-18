"""The real app, started with TestClient, on fake registry and weather services."""

import httpx
from fastapi.testclient import TestClient

from tests.fakes import FakeUpstreams, make_settings


class Api:
    def __init__(self, raise_server_exceptions: bool = True, **settings) -> None:
        from main import create_app

        self.fake = FakeUpstreams()
        app = create_app(make_settings(**settings), httpx.MockTransport(self.fake))
        self._test_client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
        self.client = self._test_client.__enter__()

    def plan(self, plot_id="p1", **params) -> httpx.Response:
        params = {"soil_moisture": 6, **params}
        return self.client.get(f"/v1/plots/{plot_id}/plan", params={k: v for k, v in params.items() if v is not None})

    def close(self) -> None:
        self._test_client.__exit__(None, None, None)
