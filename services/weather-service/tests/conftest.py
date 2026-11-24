import pytest
import time_machine

from tests.fakes import NOW


@pytest.fixture(autouse=True)
def clock():
    # Frozen: time moves only when a test says so, with clock.shift(seconds).
    with time_machine.travel(NOW, tick=False) as traveller:
        yield traveller


@pytest.fixture
def harness(waits, monkeypatch):
    """harness(**settings): a ForecastService on a fake provider.

    Retry waits never really wait, and they are 0 seconds long, so a failed fetch takes no fake time.
    """
    import provider
    from tests.harness import Harness

    monkeypatch.setattr(provider, "jitter", lambda upper: 0)
    made = []

    def make(**settings) -> Harness:
        made.append(Harness(**settings))
        return made[-1]

    yield make
    for item in made:
        item.close()


@pytest.fixture
def api(waits, monkeypatch):
    """api(**settings): the real app, started, on a fake provider. Retry waits are 0 s and never wait."""
    import provider
    from tests.api import Api

    monkeypatch.setattr(provider, "jitter", lambda upper: 0)
    made = []

    def make(raise_server_exceptions: bool = True, **settings) -> Api:
        made.append(Api(raise_server_exceptions, **settings))
        return made[-1]

    yield make
    for item in made:
        item.close()


@pytest.fixture
def waits(monkeypatch, clock) -> list[float]:
    """Retry waits do not really wait: each one is recorded and moves the fake clock."""
    import provider

    recorded: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)
        clock.shift(seconds)

    monkeypatch.setattr(provider, "sleep", fake_sleep)
    return recorded
