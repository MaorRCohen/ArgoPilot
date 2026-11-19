import pytest
import time_machine

from tests.fakes import NOW


@pytest.fixture(autouse=True)
def clock():
    # Frozen: generated_at is the same in every test run.
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def api():
    """api(**settings): the real app, started, on fake upstreams."""
    from tests.api import Api

    made = []

    def make(**settings) -> Api:
        made.append(Api(**settings))
        return made[-1]

    yield make
    for item in made:
        item.close()
