import httpx
import pytest

from tests.fakes import HANG, PLOT, forecast_body


def problem(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == code and body["status"] == status
    return body


def test_health_calls_nothing(api):
    a = api()
    assert a.client.get("/health").json() == {"status": "ok"}
    assert a.fake.calls == []


def test_plan_for_case_a(api):
    a = api()
    r = a.plan(days=3)
    assert r.status_code == 200
    body = r.json()
    assert {k: body[k] for k in ("plot_id", "plot_name", "crop", "soil_moisture_input", "generated_at",
                                 "forecast_fetched_at", "season_ended", "warnings")} == {
        "plot_id": "p1", "plot_name": "North block", "crop": "tomato", "soil_moisture_input": 6,
        "generated_at": "2026-11-18T06:00:00Z", "forecast_fetched_at": "2026-11-18T03:00:00Z",
        "season_ended": False, "warnings": []}
    assert body["today"] == {"date": "2026-11-18", "irrigate": True, "run_minutes": 832}
    assert body["totals"] == {"litres": 23100, "run_minutes": 832}
    assert body["assumptions"] == {
        "root_depth_m": 0.3, "soil_capacity_mm": 52.5, "irrigate_when_depleted_pct": 30, "uniformity_factor": 1.1,
        "emitters": 1666.67, "system_flow_lph": 1666.67, "application_rate_mm_per_h": 1.67,
        "climate_adjustment": {"wind_2m_ms": 2.0, "rh_min_pct": 45.0, "kc_change": 0.0}}
    assert [d["date"] for d in body["days"]] == ["2026-11-18", "2026-11-19", "2026-11-20"]
    assert set(body["days"][0]) == {"date", "stage", "et0_mm", "rain_mm", "kc", "need_mm", "irrigation_mm", "litres",
                                    "run_minutes", "soil_capacity_mm", "soil_water_end_mm", "soil_water_end_pct", "stale", "reason"}
    assert body["days"][0]["irrigation_mm"] == 21.0 and body["days"][2]["soil_water_end_mm"] == 35.25


def test_uniformity_factor_comes_from_settings(api):
    body = api(uniformity_factor=1.0).plan(days=1).json()
    assert body["totals"]["litres"] == 21000 and body["assumptions"]["uniformity_factor"] == 1.0


def test_default_days_is_7_and_weather_gets_the_plot_position(api):
    a = api()
    assert len(a.plan().json()["days"]) == 7
    (weather,) = a.fake.calls_to("weather.test")
    assert dict(weather.url.params) == {"lat": "31.25", "lon": "34.79", "days": "7"}


@pytest.mark.parametrize("params", [
    {"days": 0}, {"days": 8}, {"days": "x"}, {"days": 2.5},
    {"soil_moisture": None}, {"soil_moisture": -1}, {"soil_moisture": 11}, {"soil_moisture": "wet"},
    {"soil_moisture": 5.5},
])
def test_bad_query_is_422_validation_and_calls_nothing(api, params):
    a = api()
    body = problem(a.plan(**params), 422, "VALIDATION")
    assert next(iter(params)) in body["detail"]
    assert a.fake.calls == []


def test_unknown_plot_is_404(api):
    a = api()
    a.fake.plot = httpx.Response(404, json={"code": "NOT_FOUND"})
    problem(a.plan("nope"), 404, "NOT_FOUND")
    assert a.fake.calls_to("weather.test") == []


def test_plot_id_cannot_change_the_registry_request(api):
    a = api()
    a.plan("a%3Fb%23c")  # "a?b#c" must stay inside one path segment
    assert a.fake.calls[0].url.raw_path == b"/v1/plots/a%3Fb%23c"


@pytest.mark.parametrize("failure", [
    httpx.ConnectError("down"),
    httpx.ReadTimeout("slow"),
    httpx.Response(500, text="boom"),
    httpx.Response(503, text="db down"),
    httpx.Response(200, text="not json"),
    httpx.Response(200, json={"id": "p1"}),
    httpx.Response(200, json=[1]),
])
def test_registry_failure_is_503_naming_registry_service(api, failure):
    a = api()
    a.fake.plot = failure
    r = a.plan()
    body = problem(r, 503, "UPSTREAM_UNAVAILABLE")
    assert "registry-service" in body["detail"]
    assert r.headers["retry-after"] == "30"
    assert len(a.fake.calls_to("registry.test")) == 1
    assert a.fake.calls_to("weather.test") == []


@pytest.mark.parametrize("which", ["soil", "emitter"])
@pytest.mark.parametrize("failure", [httpx.Response(404), httpx.Response(500), httpx.ConnectError("x"),
                                     httpx.Response(200, json={"id": "x"})])
def test_soil_or_emitter_failure_is_503_registry(api, which, failure):
    a = api()
    setattr(a.fake, which, failure)
    body = problem(a.plan(), 503, "UPSTREAM_UNAVAILABLE")
    assert "registry-service" in body["detail"]


@pytest.mark.parametrize("failure", [
    httpx.ConnectError("down"),
    httpx.ReadTimeout("slow"),
    httpx.Response(500),
    httpx.Response(200, text="not json"),
    httpx.Response(422, json={"code": "VALIDATION"}),
    httpx.Response(200, json={"days": []}),
    httpx.Response(200, json=forecast_body(2)),  # asked for 7
])
def test_weather_failure_is_503_naming_weather_service(api, failure):
    a = api()
    a.fake.weather = failure
    r = a.plan()
    body = problem(r, 503, "UPSTREAM_UNAVAILABLE")
    assert "weather-service" in body["detail"] and "registry-service" not in body["detail"]
    assert r.headers["retry-after"] == "30"


def test_weather_retry_after_is_passed_on(api):
    a = api()
    a.fake.weather = httpx.Response(503, headers={"Retry-After": "17"}, json={"code": "UNAVAILABLE"})
    assert a.plan().headers["retry-after"] == "17"


def test_weather_day_missing_a_field_is_not_filled_with_zeros(api):
    a = api()
    body = forecast_body(7)
    del body["days"][3]["et0_mm"]
    a.fake.weather = httpx.Response(200, json=body)
    problem(a.plan(), 503, "UPSTREAM_UNAVAILABLE")


def test_stale_forecast_gives_a_plan_with_stale_days_and_warning(api):
    a = api()
    a.fake.weather = httpx.Response(200, json=forecast_body(3, stale=True) | {"fetched_at": "2026-11-17T20:00:00Z"})
    body = a.plan(days=3).json()
    assert all(d["stale"] for d in body["days"])
    assert [w["code"] for w in body["warnings"]] == ["STALE_FORECAST"]
    assert body["forecast_fetched_at"] == "2026-11-17T20:00:00Z"


def test_exactly_one_call_per_upstream_even_when_they_fail(api):
    a = api()
    a.plan()
    assert [c.url.path for c in a.fake.calls_to("registry.test")].count("/v1/plots/p1") == 1
    assert len(a.fake.calls_to("registry.test")) == 3  # plot, soil, emitter
    assert len(a.fake.calls_to("weather.test")) == 1
    b = api()
    b.fake.weather = httpx.Response(500)
    b.plan()
    assert len(b.fake.calls_to("weather.test")) == 1


def test_crop_without_profile_is_409_and_weather_is_not_called(api):
    a = api()
    a.fake.plot = httpx.Response(200, json=PLOT | {"crop_id": "cucumber"})
    body = problem(a.plan(), 409, "CONFLICT")
    assert "cucumber" in body["detail"]
    assert a.fake.calls_to("weather.test") == []


def test_season_ended_warning_through_the_api(api):
    a = api()
    a.fake.plot = httpx.Response(200, json=PLOT | {"planting_date": "2026-01-01"})
    body = a.plan(days=1).json()
    assert body["season_ended"] and [w["code"] for w in body["warnings"]] == ["SEASON_ENDED"]


@pytest.mark.parametrize("service, setting", [("plot", "registry_timeout_s"), ("weather", "weather_timeout_s")])
def test_a_hung_upstream_is_cut_by_the_timeout(api, service, setting):
    a = api(**{setting: 0.05})
    setattr(a.fake, service, HANG)
    body = problem(a.plan(), 503, "UPSTREAM_UNAVAILABLE")
    assert ("registry-service" if service == "plot" else "weather-service") in body["detail"]


def test_dry_soil_is_capped_through_the_api(api):
    body = api().plan(days=2, soil_moisture=0).json()
    assert [w["code"] for w in body["warnings"]] == ["IRRIGATION_CAPPED"]
    assert body["days"][0]["run_minutes"] == 1440 and body["days"][1]["irrigation_mm"] == 21.89


def test_the_cap_is_a_setting(api):
    body = api(max_run_minutes_per_day=600).plan(days=1, soil_moisture=0).json()
    assert body["days"][0]["run_minutes"] <= 600
