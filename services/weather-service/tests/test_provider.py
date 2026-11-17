"""The Open-Meteo client, one attempt at a time (retries: test_provider_retries.py)."""

import json
import traceback
from datetime import date

import httpx
import pytest

from provider import ProviderError
from tests.fakes import BASE_URL, ET0, NOW, RAIN_MM, fetch, open_meteo_body

VARIABLES = ("et0_fao_evapotranspiration", "rain_sum", "showers_sum")
SECRET_KEY = "k3y-s3cret"  # a constant, so no traceback source line shows the value


def answers(body):
    # Raw content, not json=: httpx refuses to encode NaN, and a provider could still send it.
    return lambda request: httpx.Response(
        200, content=json.dumps(body), headers={"content-type": "application/json"}
    )


def no_retries(handler, **settings):
    return fetch(handler, provider_retries=0, **settings)


# ---- a good response


def test_a_good_response_becomes_eight_days_with_rain_and_showers_added():
    forecast = no_retries(answers(open_meteo_body()))
    assert [day.date for day in forecast.days][:2] == [date(2026, 11, 17), date(2026, 11, 18)]
    assert [day.et0_mm for day in forecast.days] == ET0
    assert [day.rain_mm for day in forecast.days] == RAIN_MM  # 0.2 + 0.1 is 0.3, not 0.30000000000000004
    assert len(forecast.days) == 8
    assert forecast.utc_offset_s == 7200
    assert forecast.fetched_at == NOW


def test_rain_is_liquid_only_so_precipitation_sum_with_snow_is_ignored():
    body = open_meteo_body()
    body["daily"]["precipitation_sum"] = [99.0] * 8
    body["daily"]["snowfall_sum"] = [50.0] * 8
    assert [day.rain_mm for day in no_retries(answers(body)).days] == RAIN_MM


def test_et0_is_passed_through_as_the_provider_gave_it():
    body = open_meteo_body()
    body["daily"]["et0_fao_evapotranspiration"][0] = 3.14
    assert no_retries(answers(body)).days[0].et0_mm == 3.14


def test_a_zero_is_a_real_value():
    body = open_meteo_body()
    body["daily"]["et0_fao_evapotranspiration"][0] = 0
    body["daily"]["rain_sum"][0] = 0
    body["daily"]["showers_sum"][0] = 0.0
    day = no_retries(answers(body)).days[0]
    assert (day.et0_mm, day.rain_mm) == (0.0, 0.0)


# ---- what is sent


def test_the_request_asks_for_the_decided_parameters_and_sends_no_key_when_it_is_empty():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=open_meteo_body())

    no_retries(handler, lat=31.25, lon=34.75)
    assert str(seen[0].url).split("?")[0] == BASE_URL
    assert dict(seen[0].url.params) == {
        "latitude": "31.25",
        "longitude": "34.75",
        "daily": "et0_fao_evapotranspiration,rain_sum,showers_sum",
        "timezone": "auto",
        "precipitation_unit": "mm",
        "forecast_days": "8",
    }


def test_a_key_is_sent_as_apikey():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=open_meteo_body())

    no_retries(handler, open_meteo_api_key="k3y")
    assert seen[0].url.params["apikey"] == "k3y"


def test_forecast_days_comes_from_the_settings():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=open_meteo_body(days=10))

    assert len(no_retries(handler, forecast_fetch_days=10).days) == 10
    assert seen[0].url.params["forecast_days"] == "10"


# ---- anything wrong is a failure, never a number the provider did not give


def delete(*path):
    def mutate(body):
        target = body
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return mutate


def put(value, *path):
    def mutate(body):
        target = body
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def drop_last(*path):
    return lambda body: _walk(body, path).pop()


def add_one(*path, value):
    return lambda body: _walk(body, path).append(value)


def _walk(body, path):
    for key in path:
        body = body[key]
    return body


BAD_BODIES = {
    "no daily": delete("daily"),
    "no daily_units": delete("daily_units"),
    "no time": delete("daily", "time"),
    "no utc offset": delete("utc_offset_seconds"),
    "utc offset null": put(None, "utc_offset_seconds"),
    "utc offset as text": put("7200", "utc_offset_seconds"),
    "date null": put(None, "daily", "time", 2),
    "date not a date": put("17/11/2026", "daily", "time", 2),
    "date not text": put(20261119, "daily", "time", 2),
    "a day skipped": put("2026-11-23", "daily", "time", 4),
    "a date twice": put("2026-11-20", "daily", "time", 4),
    "dates backwards": lambda body: body["daily"]["time"].reverse(),
    "every list one day short": lambda body: [drop_last("daily", name)(body) for name in ("time", *VARIABLES)],
    "every list one day extra": lambda body: [
        add_one("daily", "time", value="2026-11-25")(body),
        *[add_one("daily", name, value=1.0)(body) for name in VARIABLES],
    ],
    "time one day short": drop_last("daily", "time"),
    "time one day extra": add_one("daily", "time", value="2026-11-25"),
}
for _name in VARIABLES:
    BAD_BODIES |= {
        f"{_name} missing": delete("daily", _name),
        f"{_name} not a list": put(3.1, "daily", _name),
        f"{_name} first day null": put(None, "daily", _name, 0),
        f"{_name} last day null": put(None, "daily", _name, 7),
        f"{_name} negative": put(-0.1, "daily", _name, 3),
        f"{_name} text": put("3.1", "daily", _name, 3),
        f"{_name} true": put(True, "daily", _name, 3),
        f"{_name} list": put([1.0], "daily", _name, 3),
        f"{_name} NaN": put(float("nan"), "daily", _name, 3),
        f"{_name} infinity": put(float("inf"), "daily", _name, 3),
        f"{_name} unit missing": delete("daily_units", _name),
        f"{_name} unit inch": put("inch", "daily_units", _name),
        f"{_name} unit upper case": put("MM", "daily_units", _name),
        f"{_name} one day short": drop_last("daily", _name),
        f"{_name} one day extra": add_one("daily", _name, value=1.0),
    }


@pytest.mark.parametrize("mutate", BAD_BODIES.values(), ids=BAD_BODIES.keys())
def test_a_body_with_anything_wrong_is_a_provider_failure(mutate):
    body = open_meteo_body()
    mutate(body)
    with pytest.raises(ProviderError):
        no_retries(answers(body))


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(503, text="busy"),
        httpx.Response(404, json={"error": True, "reason": "not found"}),
        httpx.Response(429),
        httpx.Response(301, headers={"location": "https://elsewhere.test/v1/forecast"}),
        httpx.Response(200, json={"error": True, "reason": "Cannot initialize WeatherVariable"}),
        httpx.Response(200, text="<html>maintenance</html>"),
        httpx.Response(200, content=b""),
        httpx.Response(200, content=b"\xff\xfe\x00"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json=None),
        httpx.Response(200, json="ok"),
    ],
    ids=[
        "500",
        "503",
        "404",
        "429",
        "redirect",
        "error body",
        "html",
        "empty",
        "not utf-8",
        "list",
        "null",
        "string",
    ],
)
def test_a_bad_response_is_a_provider_failure(response):
    with pytest.raises(ProviderError):
        no_retries(lambda request: response)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("slow"),
        httpx.ConnectTimeout("slow"),
        httpx.PoolTimeout("busy"),
        httpx.ConnectError("refused"),
        httpx.ReadError("reset"),
        httpx.RemoteProtocolError("bad framing"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_a_network_error_is_a_provider_failure(error):
    def handler(request):
        raise error

    with pytest.raises(ProviderError):
        no_retries(handler)


def test_the_failure_never_shows_the_url_or_the_key():
    # httpx puts the full URL, with ?apikey=..., into many error messages. It must not travel on.
    def handler(request):
        raise httpx.ConnectError(f"cannot reach {request.url}")

    with pytest.raises(ProviderError) as info:
        no_retries(handler, open_meteo_api_key=SECRET_KEY)
    shown = str(info.value) + "".join(traceback.format_exception(info.value))
    assert SECRET_KEY not in shown
    assert "open-meteo.test" not in shown
