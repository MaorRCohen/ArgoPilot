from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app

DEMO_FARM_ID = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"  # seeded, has North block and East block
NORTH_BLOCK_ID = "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002"
REQUESTS = 240
THREADS = 20


@pytest.fixture
def long_lived_client(db_path):
    # The with-block keeps one event loop and threadpool alive for every request, like uvicorn.
    with TestClient(app) as client:
        yield client


def test_concurrent_gets_all_succeed(long_lived_client):
    client = long_lived_client
    # One shared TestClient, so all threads hit the same app at the same time.
    plot_ids = [plot["id"] for plot in client.get("/v1/plots").json()]
    assert NORTH_BLOCK_ID in plot_ids
    paths = (
        ["/v1/farms", f"/v1/farms/{DEMO_FARM_ID}", "/v1/plots", f"/v1/plots/{NORTH_BLOCK_ID}"]
        + [f"/v1/plots/{plot_id}" for plot_id in plot_ids]
    )
    urls = [paths[i % len(paths)] for i in range(REQUESTS)]

    def fetch(url: str) -> str:
        # Count exceptions as failures too: TestClient re-raises server errors by default.
        try:
            response = client.get(url)
        except Exception as error:
            return type(error).__name__
        return str(response.status_code)

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        results = list(pool.map(fetch, urls))

    outcomes = Counter(results)
    failures = sum(count for outcome, count in outcomes.items() if outcome != "200")
    assert failures == 0, f"{failures} of {REQUESTS} failed; outcomes={dict(outcomes)}"
