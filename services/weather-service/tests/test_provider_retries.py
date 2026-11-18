"""Retries, backoff and the total time budget of one provider fetch (FR-2.6, FR-2.7)."""

import asyncio
import time
from datetime import UTC, datetime

import httpx
import pytest

import provider
from provider import ProviderError
from tests.fakes import FakeProvider, fetch, open_meteo_body


@pytest.fixture
def fake() -> FakeProvider:
    return FakeProvider()


def timing_out(clock, seen: list, seconds: float = 1.5):
    """An attempt that takes `seconds` of fake time, or the timeout it was given if that is shorter,
    and then times out. Records the timeout."""

    def handler(request):
        timeout = request.extensions["timeout"]["read"]
        seen.append(timeout)
        clock.shift(min(seconds, timeout))
        return httpx.ReadTimeout("slow")  # an outcome that is an exception is raised by FakeProvider

    return handler


def elapsed_since(start: datetime) -> float:
    return (datetime.now(UTC) - start).total_seconds()


# ---- how many attempts


def test_a_provider_that_keeps_failing_is_tried_three_times(fake, waits):
    fake.default = httpx.Response(500)
    with pytest.raises(ProviderError):
        fetch(fake)
    assert fake.calls == 3  # the first attempt and two retries


def test_a_retry_that_works_gives_the_forecast(fake, waits):
    fake.script = [httpx.Response(500), httpx.ReadTimeout("slow")]  # the third call gets a good body
    forecast = fetch(fake)
    assert fake.calls == 3
    assert len(forecast.days) == 8


def test_the_first_retry_can_be_the_one_that_works(fake, waits):
    fake.script = [httpx.Response(503)]
    fetch(fake)
    assert fake.calls == 2


def test_a_good_first_attempt_has_no_retry_and_no_wait(fake, waits):
    fetch(fake)
    assert fake.calls == 1
    assert waits == []


def test_a_body_with_anything_wrong_is_retried_like_any_failure(fake, waits):
    body = open_meteo_body()
    body["daily"]["rain_sum"][2] = None
    fake.script = [body, httpx.Response(200, text="<html>oops</html>")]  # a null, then not even JSON
    forecast = fetch(fake)
    assert fake.calls == 3
    assert forecast.days[2].rain_mm == 0.0


@pytest.mark.parametrize(("retries", "calls"), [(0, 1), (1, 2), (2, 3), (5, 6)])
def test_the_number_of_retries_comes_from_the_settings(fake, waits, retries, calls):
    fake.default = httpx.Response(500)
    with pytest.raises(ProviderError):
        fetch(fake, provider_retries=retries, provider_total_budget_s=60)
    assert fake.calls == calls


# ---- the wait between attempts: full jitter, random(0, base * 2**n)


def test_each_wait_is_jittered_up_to_the_base_times_two_to_the_n(fake, waits, monkeypatch):
    uppers = []
    monkeypatch.setattr(provider, "jitter", lambda upper: uppers.append(upper) or upper / 2)
    fake.default = httpx.Response(500)
    with pytest.raises(ProviderError):
        fetch(fake)
    assert uppers == [0.2, 0.4]
    assert waits == [0.1, 0.2]


def test_the_base_of_the_wait_comes_from_the_settings(fake, waits, monkeypatch):
    uppers = []
    monkeypatch.setattr(provider, "jitter", lambda upper: uppers.append(upper) or 0)
    fake.default = httpx.Response(500)
    with pytest.raises(ProviderError):
        fetch(fake, backoff_base_s=1.0, provider_retries=3, provider_total_budget_s=60)
    assert uppers == [1.0, 2.0, 4.0]


def test_the_jitter_is_random_between_zero_and_the_upper_bound():
    samples = [provider.jitter(0.4) for _ in range(500)]
    assert all(0 <= sample <= 0.4 for sample in samples)
    assert min(samples) < 0.1 < 0.3 < max(samples)  # spread over the range, not a constant


# ---- how long one attempt may take


def test_each_attempt_is_given_the_per_attempt_timeout(fake, waits):
    seen = []

    def handler(request):
        seen.append(request.extensions["timeout"])
        return httpx.Response(500)

    fake.default = handler
    with pytest.raises(ProviderError):
        fetch(fake)
    assert seen == [{"connect": 1.5, "read": 1.5, "write": 1.5, "pool": 1.5}] * 3


def test_an_attempt_is_cut_off_at_the_timeout_however_slowly_the_provider_answers():
    # httpx's own timeouts are per step. A provider that trickles bytes must still be cut off in total.
    async def trickling(request):
        await asyncio.sleep(5)
        return httpx.Response(200, json=open_meteo_body())

    started = time.perf_counter()  # not frozen by time-machine
    with pytest.raises(ProviderError):
        fetch(trickling, provider_timeout_s=0.05, provider_retries=0)
    assert time.perf_counter() - started < 2


# ---- the total budget


def test_the_budget_stops_the_retries(fake, waits, clock, monkeypatch):
    monkeypatch.setattr(provider, "jitter", lambda upper: upper)  # the longest waits
    seen = []
    fake.default = timing_out(clock, seen)
    started = datetime.now(UTC)
    with pytest.raises(ProviderError):
        fetch(fake)
    # 1.5 s + 0.2 s wait + 1.5 s = 3.2 s. A third attempt would get 0.8 s - 0.4 s of wait = 0.4 s:
    # not a meaningful timeout, so it is not started, and its wait is not taken either.
    assert fake.calls == 2
    assert waits == [0.2]
    assert elapsed_since(started) == pytest.approx(3.2)


def test_the_last_attempt_gets_only_the_time_that_is_left(fake, waits, clock, monkeypatch):
    monkeypatch.setattr(provider, "jitter", lambda upper: 0)
    seen = []
    fake.default = timing_out(clock, seen)
    started = datetime.now(UTC)
    with pytest.raises(ProviderError):
        fetch(fake)
    assert seen == [1.5, 1.5, 1.0]  # 4 s budget: 1.5 + 1.5, and 1.0 s left for the third
    assert elapsed_since(started) == pytest.approx(4.0)


def test_a_budget_shorter_than_one_timeout_cuts_the_first_attempt(fake, waits, clock):
    seen = []
    fake.default = timing_out(clock, seen, seconds=1.0)
    with pytest.raises(ProviderError):
        fetch(fake, provider_total_budget_s=1.0)
    assert seen == [1.0]  # min(1.5, 1.0)
    assert fake.calls == 1
    assert waits == []


def test_a_wait_that_does_not_fit_in_the_budget_is_not_taken(fake, waits, monkeypatch):
    monkeypatch.setattr(provider, "jitter", lambda upper: upper)
    fake.default = httpx.Response(500)  # fails at once
    with pytest.raises(ProviderError):
        fetch(fake, backoff_base_s=10)  # a first wait of up to 10 s, budget 4 s
    assert fake.calls == 1
    assert waits == []


# ---- only transient failures are retried


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_other_statuses_are_not_retried(fake, waits, status):
    fake.default = httpx.Response(status)
    with pytest.raises(ProviderError):
        fetch(fake)
    assert fake.calls == 1
    assert waits == []


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_statuses_are_retried(fake, waits, status):
    fake.default = httpx.Response(status)
    with pytest.raises(ProviderError):
        fetch(fake)
    assert fake.calls == 3


@pytest.mark.parametrize("error", [httpx.ReadTimeout("slow"), httpx.ConnectError("refused")], ids=type)
def test_timeouts_and_connection_errors_are_retried(fake, waits, error):
    fake.default = error
    with pytest.raises(ProviderError):
        fetch(fake)
    assert fake.calls == 3


@pytest.mark.parametrize("body", [
    httpx.Response(200, text="<html>"),
    {"daily": None, "daily_units": None},
], ids=["not json", "missing fields"])
def test_an_invalid_200_body_is_retried(fake, waits, body):
    fake.default = body
    with pytest.raises(ProviderError):
        fetch(fake)
    assert fake.calls == 3


# ---- the provider's Retry-After


def rate_limited(value, status=429):
    return httpx.Response(status, headers={"Retry-After": value})


def test_a_retry_after_longer_than_the_budget_means_no_wait_and_no_retry(fake, waits):
    fake.default = rate_limited("120")
    with pytest.raises(ProviderError) as info:
        fetch(fake)
    assert fake.calls == 1
    assert waits == []
    assert info.value.retry_after_s == 120


def test_a_retry_after_that_fits_in_the_budget_is_waited(fake, waits):
    fake.script = [rate_limited("1", 503)]
    fetch(fake)
    assert waits == [1.0]
    assert fake.calls == 2


def test_retry_after_as_an_http_date_is_parsed(fake, waits):
    from email.utils import format_datetime

    from tests.fakes import NOW
    from datetime import timedelta

    fake.default = rate_limited(format_datetime(NOW + timedelta(seconds=90), usegmt=True))
    with pytest.raises(ProviderError) as info:
        fetch(fake)
    assert info.value.retry_after_s == pytest.approx(90)


@pytest.mark.parametrize("value", ["soon", "", "-5x"])
def test_an_unreadable_retry_after_is_ignored(fake, waits, value):
    fake.default = rate_limited(value)
    with pytest.raises(ProviderError) as info:
        fetch(fake)
    assert info.value.retry_after_s is None
    assert fake.calls == 3


# ---- logs


def test_each_failed_attempt_is_logged_with_cell_and_reason_and_never_the_key(fake, waits, caplog):
    import logging

    fake.default = httpx.Response(500)
    with caplog.at_level(logging.INFO):
        with pytest.raises(ProviderError):
            fetch(fake, open_meteo_api_key="k3y-s3cret")
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 3
    assert "cell=(312, 347)" in warnings[0].getMessage()
    assert "attempt 1/3" in warnings[0].getMessage()
    assert "HTTP status 500" in warnings[0].getMessage()
    assert "attempt 3/3" in warnings[2].getMessage()
    assert "k3y-s3cret" not in caplog.text
    assert "open-meteo.test" not in caplog.text
    assert "apikey" not in caplog.text


def test_a_validation_failure_is_logged_with_which_check_failed(fake, waits, caplog):
    import logging

    body = open_meteo_body()
    body["daily_units"]["rain_sum"] = "inch"
    fake.default = body
    with caplog.at_level(logging.INFO):
        with pytest.raises(ProviderError):
            fetch(fake)
    assert "daily_units.rain_sum" in caplog.text
