"""The HTTP contract: FR-2.3, FR-2.4, FR-2.6, FR-2.7 and the error format."""

import logging
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

import config
import main
from tests.fakes import ET0, RAIN_MM

HOUR = 3600
PROBLEM_JSON = "application/problem+json"


def assert_problem(response, status: int, code: str) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["code"] == code
    assert body["status"] == status
    assert set(body) == {"type", "title", "status", "detail", "code"}
    return body


# ---- GET /v1/forecast (FR-2.3)


def test_the_response_is_the_one_in_the_spec(api):
    a = api()
    response = a.forecast(lat=31.25, lon=34.79, days=7)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert list(response.json()) == ["lat", "lon", "source", "fetched_at", "stale", "days"]
    assert response.json() == {
        "lat": 31.25,
        "lon": 34.79,
        "source": "open-meteo",
        "fetched_at": "2026-11-17T08:00:00Z",
        "stale": False,
        "days": [
            {"date": f"2026-11-{17 + index}", "et0_mm": ET0[index], "rain_mm": RAIN_MM[index]}
            for index in range(7)
        ],
    }
    assert a.fake.calls == 1


def test_lat_and_lon_are_answered_as_requested_not_as_the_cell_center(api):
    body = api().forecast(lat=31.3123, lon=34.8987, days=1).json()
    assert (body["lat"], body["lon"]) == (31.3123, 34.8987)
    assert len(body["days"]) == 1


def test_the_days_parameter_sets_the_number_of_days(api):
    a = api()
    assert [len(a.forecast(days=days).json()["days"]) for days in (1, 2, 7)] == [1, 2, 7]
    assert a.fake.calls == 1  # one cell, one forecast


@pytest.mark.parametrize(("lat", "lon", "days"), [(90, 180, 1), (-90, -180, 7), (0, 0, 3)])
def test_the_limits_are_valid(api, lat, lon, days):
    assert api().forecast(lat=lat, lon=lon, days=days).status_code == 200


# ---- FR-2.4: a bad lat, lon or days is a 422 and never reaches the provider


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"lat": 90.01}, "lat"),
        ({"lat": -90.01}, "lat"),
        ({"lat": 1000}, "lat"),
        ({"lat": "abc"}, "lat"),
        ({"lat": "nan"}, "lat"),
        ({"lat": "inf"}, "lat"),
        ({"lat": ""}, "lat"),
        ({"lon": 180.01}, "lon"),
        ({"lon": -180.01}, "lon"),
        ({"lon": "abc"}, "lon"),
        ({"lon": "nan"}, "lon"),
        ({"lon": "-inf"}, "lon"),
        ({"days": 0}, "days"),
        ({"days": 8}, "days"),
        ({"days": -1}, "days"),
        ({"days": 1.5}, "days"),
        ({"days": "abc"}, "days"),
        ({"days": ""}, "days"),
    ],
)
def test_an_out_of_range_or_invalid_value_is_a_422_validation(api, params, field):
    a = api()
    query = {"lat": 31.25, "lon": 34.79, "days": 7, **params}
    response = a.client.get("/v1/forecast", params=query)
    body = assert_problem(response, 422, "VALIDATION")
    assert body["detail"].startswith(f"{field}:")
    assert a.fake.calls == 0


@pytest.mark.parametrize("missing", ["lat", "lon", "days"])
def test_a_missing_parameter_is_a_422_validation(api, missing):
    a = api()
    query = {"lat": 31.25, "lon": 34.79, "days": 7}
    del query[missing]
    body = assert_problem(a.client.get("/v1/forecast", params=query), 422, "VALIDATION")
    assert body["detail"] == f"{missing}: Field required"
    assert a.fake.calls == 0


# ---- FR-2.6: the provider fails, an old forecast answers with stale: true


def test_a_failing_provider_is_answered_with_the_old_forecast_marked_stale(api, clock):
    a = api()
    first = a.forecast().json()
    clock.shift(4 * HOUR)
    a.fake.default = httpx.Response(500)
    response = a.forecast()
    assert response.status_code == 200
    body = response.json()
    assert body["stale"] is True
    assert body["fetched_at"] == first["fetched_at"]  # the age stays visible
    assert body["days"] == first["days"]
    assert a.fake.calls == 1 + 3


# ---- FR-2.7: the provider fails and nothing earlier exists: 503 with Retry-After


def test_a_failing_provider_and_no_earlier_forecast_is_a_503_with_retry_after(api):
    a = api()
    a.fake.default = httpx.Response(500)
    response = a.forecast()
    body = assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["retry-after"] == "30"
    assert "provider" in body["detail"]
    assert a.fake.calls == 3


def test_retry_after_is_what_is_left_of_the_cooldown(api, clock):
    a = api()
    a.fake.default = httpx.Response(500)
    assert a.forecast().headers["retry-after"] == "30"
    clock.shift(12)
    response = a.forecast()
    assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["retry-after"] == "18"
    assert a.fake.calls == 3  # the cooldown: no new provider call


def test_a_forecast_older_than_24_hours_is_a_503_not_a_stale_answer(api, clock):
    a = api()
    a.forecast()
    clock.shift(24 * HOUR)
    a.fake.default = httpx.Response(500)
    assert_problem(a.forecast(), 503, "UNAVAILABLE")


def test_a_bad_provider_answer_is_a_503_never_a_forecast_of_zeros(api):
    a = api()
    body = {"daily": None, "daily_units": None}  # nothing usable
    a.fake.default = body
    assert_problem(a.forecast(), 503, "UNAVAILABLE")


def test_the_api_key_never_reaches_a_response(api):
    a = api(open_meteo_api_key="k3y-s3cret")
    a.fake.default = httpx.Response(500)
    response = a.forecast()
    assert "k3y-s3cret" not in response.text
    assert "k3y-s3cret" not in str(response.headers)


# ---- concurrent callers share one provider call, end to end


def test_many_concurrent_requests_make_one_provider_call(api):
    a = api()
    a.fake.delay_s = 0.3  # long enough for every request to arrive while the call is under way
    with ThreadPoolExecutor(20) as pool:
        responses = list(pool.map(lambda _: a.forecast(), range(20)))
    assert a.fake.calls == 1
    assert {response.status_code for response in responses} == {200}
    assert len({response.text for response in responses}) == 1


def test_many_concurrent_requests_all_get_the_same_503_after_one_round_of_retries(api):
    a = api()
    a.fake.default = httpx.Response(500)
    a.fake.delay_s = 0.1
    with ThreadPoolExecutor(20) as pool:
        responses = list(pool.map(lambda _: a.forecast(), range(20)))
    assert a.fake.calls == 3  # one fetch with its two retries, not twenty
    assert {response.status_code for response in responses} == {503}
    assert {response.headers["retry-after"] for response in responses} == {"30"}


# ---- GET /health


def test_health_is_ok_and_never_calls_the_provider(api):
    a = api()
    a.fake.default = httpx.Response(500)  # even if the provider is down
    response = a.client.get("/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})
    assert a.fake.calls == 0


# ---- errors and startup


def test_an_unknown_path_is_a_404_problem(api):
    assert_problem(api().client.get("/v1/nope"), 404, "NOT_FOUND")


def test_a_wrong_method_is_a_405_problem(api):
    assert_problem(api().client.post("/v1/forecast"), 405, "VALIDATION")


def test_an_unexpected_error_is_a_generic_500_and_the_traceback_goes_to_the_log(api, caplog):
    a = api(raise_server_exceptions=False)
    a.fake.default = RuntimeError("a bug, not a provider failure")
    with caplog.at_level(logging.ERROR):
        response = a.forecast()
    body = assert_problem(response, 500, "UNAVAILABLE")
    assert body["detail"] == "Internal server error"
    assert "a bug, not a provider failure" in caplog.text
    assert "a bug" not in response.text


def test_a_missing_base_url_stops_the_start_with_a_clear_message(monkeypatch, tmp_path):
    monkeypatch.delenv("OPEN_METEO_BASE_URL", raising=False)
    monkeypatch.setattr(main, "get_settings", lambda: config.load_settings(env_file=tmp_path / "none.env"))
    with pytest.raises(config.SettingsError, match="OPEN_METEO_BASE_URL: missing"):
        with TestClient(main.create_app()):
            pass


def test_uvicorn_finds_the_app_without_any_settings_at_import():
    # `uvicorn main:app` imports this. Settings are read at startup, not here.
    assert set(main.app.openapi()["paths"]) == {"/health", "/v1/forecast"}
