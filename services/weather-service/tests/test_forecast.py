"""The forecast cache: grid cells, freshness, stale answers, 503 (FR-2.5, FR-2.6, FR-2.7)."""

import asyncio
from datetime import UTC, date, datetime

import httpx
import pytest

from forecast import Unavailable
from tests.fakes import ET0, NOW, RAIN_MM, open_meteo_body

HOUR = 3600


def dates(served) -> list[date]:
    return [day.date for day in served.days]


# ---- the grid: points in one 0.1 degree cell share a forecast


def test_the_answer_has_the_requested_days_starting_today(harness):
    h = harness()
    served = h.get(31.25, 34.79, days=3)
    assert dates(served) == [date(2026, 11, 17), date(2026, 11, 18), date(2026, 11, 19)]
    assert [day.et0_mm for day in served.days] == ET0[:3]
    assert [day.rain_mm for day in served.days] == RAIN_MM[:3]
    assert served.stale is False
    assert served.fetched_at == NOW


def test_two_points_in_the_same_cell_share_one_provider_call(harness):
    h = harness()
    first = h.get(31.31, 34.81, days=3)
    second = h.get(31.39, 34.89, days=7)
    assert h.fake.calls == 1
    assert (len(first.days), len(second.days)) == (3, 7)
    assert first.fetched_at == second.fetched_at


def test_points_in_different_cells_do_not_share(harness):
    h = harness()
    h.get(31.25, 34.79)
    h.get(31.35, 34.79)  # the next cell north
    h.get(31.25, 34.89)  # the next cell east
    assert h.fake.calls == 3


def test_the_provider_is_asked_about_the_center_of_the_cell(harness):
    h = harness()
    h.get(31.31, 34.81)
    assert h.fake.requests[0].url.params["latitude"] == "31.35"
    assert h.fake.requests[0].url.params["longitude"] == "34.85"


def test_the_center_is_clamped_at_the_poles_and_the_date_line(harness):
    h = harness()
    h.get(90, 180)
    assert h.fake.requests[0].url.params["latitude"] == "90.0"
    assert h.fake.requests[0].url.params["longitude"] == "180.0"


# ---- fresh for 3 hours


def test_a_fresh_forecast_is_served_without_a_provider_call(harness, clock):
    h = harness()
    h.get()
    clock.shift(3 * HOUR - 1)
    served = h.get()
    assert h.fake.calls == 1
    assert served.stale is False


def test_a_forecast_older_than_three_hours_is_fetched_again(harness, clock):
    h = harness()
    h.get()
    clock.shift(3 * HOUR + 1)
    served = h.get()
    assert h.fake.calls == 2
    assert served.stale is False
    assert served.fetched_at == datetime(2026, 11, 17, 11, 0, 1, tzinfo=UTC)


def test_the_first_day_is_today_at_the_point_even_if_the_forecast_was_fetched_yesterday(harness, clock):
    clock.move_to(datetime(2026, 11, 17, 21, 30, tzinfo=UTC))  # 23:30 in Israel (UTC+2)
    h = harness()
    assert h.get(days=7).days[0].date == date(2026, 11, 17)
    clock.shift(HOUR)  # 00:30 on the 18th in Israel: the forecast is 1 hour old, so still fresh
    served = h.get(days=7)
    assert h.fake.calls == 1
    assert served.stale is False
    assert dates(served) == [date(2026, 11, day) for day in range(18, 25)]


def test_today_is_the_local_date_at_the_point_not_the_utc_date(harness, clock):
    clock.move_to(datetime(2026, 11, 17, 3, 0, tzinfo=UTC))  # still the evening of the 16th at UTC-5
    h = harness()
    h.fake.default = lambda request: open_meteo_body(utc_offset_s=-5 * HOUR)
    served = h.get(40.7, -74.0, days=2)
    assert dates(served) == [date(2026, 11, 16), date(2026, 11, 17)]


def test_a_fresh_forecast_that_no_longer_covers_the_days_is_fetched_again(harness, clock):
    clock.move_to(datetime(2026, 11, 17, 21, 30, tzinfo=UTC))
    h = harness(forecast_fetch_days=7)  # 7 days from the 17th: after midnight only 6 are left from today
    h.get(days=7)
    clock.shift(HOUR)
    served = h.get(days=7)
    assert h.fake.calls == 2
    assert dates(served)[0] == date(2026, 11, 18)
    assert len(served.days) == 7


# ---- the provider fails: stale (FR-2.6) or 503 (FR-2.7)


def test_when_the_provider_fails_the_old_forecast_is_served_as_stale(harness, clock):
    h = harness()
    first = h.get()
    clock.shift(4 * HOUR)
    h.fake.default = httpx.Response(500)
    served = h.get()
    assert served.stale is True
    assert served.fetched_at == first.fetched_at  # the age stays visible
    assert served.days == first.days
    assert h.fake.calls == 1 + 3  # the first fetch, then the attempt and its two retries


def test_without_an_earlier_forecast_a_failing_provider_is_unavailable(harness):
    h = harness()
    h.fake.default = httpx.Response(500)
    with pytest.raises(Unavailable) as info:
        h.get()
    assert info.value.retry_after_s == 30
    assert h.fake.calls == 3


def test_a_forecast_of_24_hours_or_older_is_not_served_even_as_stale(harness, clock):
    h = harness()
    h.get()
    clock.shift(24 * HOUR)
    h.fake.default = httpx.Response(500)
    with pytest.raises(Unavailable):
        h.get()


def test_a_forecast_just_under_24_hours_old_is_still_served_as_stale(harness, clock):
    h = harness()
    h.get()
    clock.shift(24 * HOUR - 1)
    h.fake.default = httpx.Response(500)
    served = h.get()
    assert served.stale is True
    assert len(served.days) == 7
    assert served.days[0].date == date(2026, 11, 18)  # the next local day by now


def test_a_stale_forecast_that_does_not_cover_the_days_is_not_served(harness, clock):
    h = harness(forecast_fetch_days=7)
    h.get(days=7)  # 10:00 on the 17th in Israel: days 17..23
    clock.shift(20 * HOUR)  # 06:00 on the 18th: days 18..23 are left, six of them
    h.fake.default = httpx.Response(500)
    assert len(h.get(days=6).days) == 6
    with pytest.raises(Unavailable):
        h.get(days=7)


# ---- memory: the least recently requested cell goes first, expired cells are deleted

A, B, C = (10.05, 10.05), (20.05, 20.05), (30.05, 30.05)  # three different cells


def test_the_least_recently_requested_cell_is_evicted_when_the_cache_is_full(harness):
    h = harness(cache_max_cells=2)
    h.get(*A)
    h.get(*B)
    h.get(*A)  # a request moves A to the end, so B is now the least recently requested
    h.get(*C)  # the cache is full: B goes, not A (A is the oldest fetch, but it was requested last)
    assert h.fake.calls == 3
    h.get(*A)
    assert h.fake.calls == 3  # A is still cached
    h.get(*B)
    assert h.fake.calls == 4  # B was evicted


def test_the_cache_never_holds_more_cells_than_the_cap(harness):
    h = harness(cache_max_cells=3)
    for index in range(10):
        h.get(index * 5 + 0.05, 10.05)
    assert len(h.service._cache) == 3  # white box: the size is the point of this test


def test_cells_older_than_24_hours_are_deleted_when_a_new_forecast_is_stored(harness, clock):
    h = harness()
    h.get(*A)
    h.get(*B)
    clock.shift(24 * HOUR)
    h.get(*C)
    assert len(h.service._cache) == 1  # white box: A and B can never be served again


def test_an_expired_cell_is_deleted_when_it_is_requested(harness, clock):
    h = harness()
    h.get(*A)
    clock.shift(24 * HOUR)
    h.fake.default = httpx.Response(500)
    with pytest.raises(Unavailable):
        h.get(*A)
    assert len(h.service._cache) == 0


# ---- single-flight: concurrent requests for one cell share ONE provider call


async def until(condition) -> None:
    for _ in range(100):
        if condition():
            return
        await asyncio.sleep(0)
    raise AssertionError("the condition never became true")


def test_concurrent_requests_for_one_cell_share_one_provider_call(harness):
    h = harness()
    h.fake.gate = asyncio.Event()  # the provider answers only when the test says so

    def request(index: int):
        # Different points in one cell, different numbers of days.
        return asyncio.create_task(h.service.get(31.30 + index * 0.004, 34.85, days=1 + index % 7))

    async def scenario():
        first_wave = [request(index) for index in range(5)]
        await until(lambda: h.fake.calls == 1)  # the provider call is under way
        second_wave = [request(index) for index in range(5, 20)]  # these arrive while it is under way
        await asyncio.sleep(0)
        h.fake.gate.set()
        return await asyncio.gather(*first_wave, *second_wave)

    results = h.run(scenario())
    assert h.fake.calls == 1
    assert [len(served.days) for served in results] == [1 + index % 7 for index in range(20)]
    assert {served.fetched_at for served in results} == {NOW}
    assert not any(served.stale for served in results)


def test_requests_for_different_cells_each_get_their_own_call(harness):
    h = harness()

    async def scenario():
        points = [A] * 3 + [B] * 3
        return await asyncio.gather(*(h.service.get(lat, lon, days=7) for lat, lon in points))

    h.run(scenario())
    assert h.fake.calls == 2


def test_all_waiters_get_the_same_failure_and_none_retries_on_its_own(harness):
    h = harness()
    h.fake.default = httpx.Response(500)

    async def scenario():
        return await asyncio.gather(*(h.service.get(*A, days=7) for _ in range(20)), return_exceptions=True)

    results = h.run(scenario())
    assert h.fake.calls == 3  # one fetch with its two retries, not twenty of them
    assert all(isinstance(result, Unavailable) and result.retry_after_s == 30 for result in results)


def test_all_waiters_get_the_same_stale_answer(harness, clock):
    h = harness()
    h.get(*A)
    clock.shift(4 * HOUR)
    h.fake.default = httpx.Response(500)

    async def scenario():
        return await asyncio.gather(*(h.service.get(*A, days=7) for _ in range(20)))

    results = h.run(scenario())
    assert h.fake.calls == 1 + 3
    assert all(served.stale for served in results)
    assert len({served.fetched_at for served in results}) == 1


def test_a_request_that_gives_up_does_not_cancel_the_shared_provider_call(harness):
    h = harness()
    h.fake.gate = asyncio.Event()

    async def scenario():
        quitter = asyncio.create_task(h.service.get(*A, days=7))
        stayer = asyncio.create_task(h.service.get(*A, days=7))
        await until(lambda: h.fake.calls == 1)
        quitter.cancel()  # e.g. its client hung up
        await asyncio.sleep(0)
        h.fake.gate.set()
        return await stayer

    served = h.run(scenario())
    assert served.stale is False
    assert h.fake.calls == 1
    h.get(*A)
    assert h.fake.calls == 1  # the forecast was stored for the next request


# ---- after a cell failed, the provider is left alone for it for 30 seconds


def test_after_a_failure_the_provider_is_not_called_for_that_cell_for_30_seconds(harness, clock):
    h = harness()
    h.fake.default = httpx.Response(500)
    with pytest.raises(Unavailable):
        h.get()
    assert h.fake.calls == 3
    clock.shift(10)
    with pytest.raises(Unavailable) as info:
        h.get()
    assert h.fake.calls == 3  # answered at once, the provider was not called
    assert info.value.retry_after_s == 20  # what is left of the cooldown
    clock.shift(19)  # 29 s after the failure
    with pytest.raises(Unavailable) as info:
        h.get()
    assert (h.fake.calls, info.value.retry_after_s) == (3, 1)
    clock.shift(1)  # 30 s: the cooldown is over
    with pytest.raises(Unavailable):
        h.get()
    assert h.fake.calls == 6  # a new fetch, with its two retries


def test_the_cooldown_holds_even_if_the_provider_is_back(harness, clock):
    h = harness()
    h.fake.default = httpx.Response(500)
    with pytest.raises(Unavailable):
        h.get()
    h.fake.default = None  # the provider recovers
    clock.shift(5)
    with pytest.raises(Unavailable):
        h.get()
    assert h.fake.calls == 3


def test_during_the_cooldown_the_old_forecast_is_served_as_stale(harness, clock):
    h = harness()
    first = h.get()
    clock.shift(4 * HOUR)
    h.fake.default = httpx.Response(500)
    assert h.get().stale is True
    assert h.fake.calls == 1 + 3
    clock.shift(5)
    again = h.get()
    assert (again.stale, again.fetched_at) == (True, first.fetched_at)
    assert h.fake.calls == 1 + 3


def test_the_cooldown_is_per_cell(harness):
    h = harness()
    h.fake.default = httpx.Response(500)
    with pytest.raises(Unavailable):
        h.get(*A)
    h.fake.default = None  # the provider recovers
    assert h.get(*B).stale is False  # another cell is not held back
    assert h.fake.calls == 4
