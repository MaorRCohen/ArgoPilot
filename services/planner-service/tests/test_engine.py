"""The engine alone: no HTTP, no clock. Expected values are the hand-calculated cases in
.claude/skills/irrigation-calc-reference/references/decisions.md, not the code's own output."""

import dataclasses
import datetime as dt
import math
from pathlib import Path

import pytest

import engine
import profiles

PROFILES = profiles.load_crop_profiles(Path(__file__).resolve().parent.parent / "crop_profiles.json")
TOMATO = PROFILES["tomato"]
PEPPER = PROFILES["bell-pepper"]
D0 = dt.date(2026, 11, 18)
U10 = 2.67  # u2 about 2.0 m/s
RH = 45.0


def days(n=3, et0=5.0, rain=(), wind=U10, rh=RH, stale=False, start=D0):
    return [
        engine.WeatherDay(
            date=start + dt.timedelta(days=i),
            et0_mm=et0,
            rain_mm=rain[i] if i < len(rain) else 0.0,
            wind_10m_ms=wind,
            rh_min_pct=rh,
            stale=stale,
        )
        for i in range(n)
    ]


NORTH = engine.PlotInput(area_m2=1000, row_spacing_m=1.5, emitter_spacing_m=0.4, planting_date=dt.date(2026, 8, 30))
GREENHOUSE = engine.PlotInput(area_m2=400, row_spacing_m=1.2, emitter_spacing_m=0.3, planting_date=D0)


def plan(plot=NORTH, crop=TOMATO, soil=175, flow=1.0, forecast=None, moisture=6, uf=1.1, cap=1440):
    return engine.build_plan(plot, crop, soil, flow, forecast or days(), moisture, uf, cap)


def day_row(d):
    return (d.date.isoformat(), d.stage, d.et0_mm, d.rain_mm, d.kc, d.need_mm, d.irrigation_mm,
            d.litres, d.run_minutes, d.soil_water_end_mm, d.soil_water_end_pct, d.stale, d.reason)


IRRIGATE = "Irrigate: depletion reached 30% of soil capacity"
BELOW = "No irrigation: depletion below 30% of soil capacity"
RAIN_COUNTED = "No irrigation: rain counted, depletion below 30% of soil capacity"
RAIN_IGNORED = "No irrigation: rain ignored (under 0.2 x ET0), depletion below 30% of soil capacity"


def test_case_a_tomato_mid_season():
    p = plan()
    assert [day_row(d) for d in p.days] == [
        ("2026-11-18", "mid", 5.0, 0.0, 1.15, 5.75, 21.00, 23100, 832, 46.75, 89.05, False, IRRIGATE),
        ("2026-11-19", "mid", 5.0, 0.0, 1.15, 5.75, 0.0, 0, 0, 41.00, 78.10, False, BELOW),
        ("2026-11-20", "mid", 5.0, 0.0, 1.15, 5.75, 0.0, 0, 0, 35.25, 67.14, False, BELOW),
    ]
    assert (p.totals.litres, p.totals.run_minutes) == (23100, 832)
    assert p.today == engine.Today(date=D0, irrigate=True, run_minutes=832)
    a = p.assumptions
    assert (a.root_depth_m, a.soil_capacity_mm, a.irrigate_when_depleted_pct) == (0.3, 52.5, 30)
    assert (a.uniformity_factor, a.emitters, a.system_flow_lph) == (1.1, 1666.67, 1666.67)
    assert a.application_rate_mm_per_h == 1.67
    assert a.climate_adjustment == engine.ClimateAdjustment(wind_2m_ms=2.0, rh_min_pct=45.0, kc_change=0.0)
    assert not p.season_ended and p.warnings == []


def test_case_b_rain_counted_ignored_and_lost():
    p = plan(forecast=days(rain=(10.0, 0.8, 20.0)), moisture=4)
    assert [day_row(d) for d in p.days] == [
        ("2026-11-18", "mid", 5.0, 10.0, 1.15, 5.75, 21.50, 23650, 852, 46.75, 89.05, False, IRRIGATE),
        ("2026-11-19", "mid", 5.0, 0.8, 1.15, 5.75, 0.0, 0, 0, 41.00, 78.10, False, RAIN_IGNORED),
        ("2026-11-20", "mid", 5.0, 20.0, 1.15, 5.75, 0.0, 0, 0, 46.75, 89.05, False, RAIN_COUNTED),
    ]
    assert (p.totals.litres, p.totals.run_minutes) == (23650, 852)


def test_case_c_pepper_first_planting():
    p = plan(plot=GREENHOUSE, crop=PEPPER, soil=175, flow=2.0, moisture=0)
    assert [day_row(d) for d in p.days] == [
        ("2026-11-18", "init", 5.0, 0.0, 0.6, 3.00, 17.50, 7700, 208, 14.50, 82.86, False, IRRIGATE),
        ("2026-11-19", "init", 5.0, 0.0, 0.6, 3.00, 0.0, 0, 0, 12.04, 66.74, False, BELOW),
        ("2026-11-20", "init", 5.0, 0.0, 0.6, 3.00, 6.00, 2640, 72, 15.58, 83.85, False, IRRIGATE),
    ]
    assert (p.totals.litres, p.totals.run_minutes) == (10340, 280)
    a = p.assumptions
    assert (a.root_depth_m, a.soil_capacity_mm, a.emitters, a.system_flow_lph) == (0.1, 17.5, 1111.11, 2222.22)


# --- stage boundaries and Kc interpolation -------------------------------------------------------

def stage_kc(crop, d, **kw):
    """Stage and Kc of day d after planting, one-day plan, climate adjustment neutral (u2 2, RH 45)."""
    plot = dataclasses.replace(NORTH, planting_date=D0 - dt.timedelta(days=d))
    p = plan(plot=plot, crop=crop, forecast=days(1, **kw))
    return p.days[0].stage, p.days[0].kc


def test_stage_boundaries():
    t = TOMATO
    ends = [t.init_days, t.init_days + t.dev_days, t.init_days + t.dev_days + t.mid_days, t.total_days]
    cases = [(0, "init"), (ends[0] - 1, "init"), (ends[0], "dev"), (ends[1] - 1, "dev"), (ends[1], "mid"),
             (ends[2] - 1, "mid"), (ends[2], "late"), (ends[3] - 1, "late"), (ends[3], "ended")]
    assert [stage_kc(t, d)[0] for d, _ in cases] == [s for _, s in cases]


def test_kc_is_constant_in_init_and_interpolated_in_dev_and_late():
    t = TOMATO
    assert stage_kc(t, 5)[1] == t.kc_ini
    half_dev = t.init_days + t.dev_days // 2
    assert stage_kc(t, half_dev)[1] == pytest.approx(t.kc_ini + 0.5 * (t.kc_mid - t.kc_ini), abs=0.01)
    assert stage_kc(t, t.init_days)[1] == t.kc_ini  # first dev day starts at Kc ini
    late_start = t.init_days + t.dev_days + t.mid_days
    half_late = late_start + t.late_days // 2
    assert stage_kc(t, half_late)[1] == pytest.approx(t.kc_mid + 0.5 * (t.kc_end - t.kc_mid), abs=0.01)
    assert stage_kc(t, late_start)[1] == t.kc_mid


def test_planting_day_is_day_zero():
    assert stage_kc(TOMATO, 0) == ("init", TOMATO.kc_ini)


# --- climate adjustment --------------------------------------------------------------------------

def adj_for(crop, wind, rh):
    return plan(crop=crop, forecast=days(3, wind=wind, rh=rh)).assumptions.climate_adjustment


def test_wind_is_converted_from_10m_to_2m_with_eq47():
    factor = 4.87 / math.log(67.8 * 10 - 5.42)
    assert adj_for(TOMATO, 4.0, 45).wind_2m_ms == pytest.approx(4.0 * factor, abs=0.005)


def test_adjustment_uses_average_of_the_plan_days():
    f = days(2)
    f[0] = dataclasses.replace(f[0], wind_10m_ms=2.0, rh_min_pct=30.0)
    f[1] = dataclasses.replace(f[1], wind_10m_ms=4.0, rh_min_pct=50.0)
    a = plan(forecast=f).assumptions.climate_adjustment
    assert a.rh_min_pct == 40.0
    assert a.wind_2m_ms == pytest.approx(3.0 * 4.87 / math.log(67.8 * 10 - 5.42), abs=0.005)


def test_wind_and_humidity_are_clamped():
    low = adj_for(TOMATO, 0.0, 95.0)
    assert (low.wind_2m_ms, low.rh_min_pct) == (1.0, 80.0)
    high = adj_for(TOMATO, 50.0, 5.0)
    assert (high.wind_2m_ms, high.rh_min_pct) == (6.0, 20.0)


def test_kc_mid_adjustment_is_eq62_and_applies_to_the_day_kc():
    # u2 clamped to 6, RHmin clamped to 20: adj = [0.04 (6-2) - 0.004 (20-45)] x (h/3)^0.3
    expected = (0.04 * 4 - 0.004 * -25) * (TOMATO.height_m / 3) ** 0.3
    p = plan(forecast=days(1, wind=50.0, rh=5.0))
    assert p.assumptions.climate_adjustment.kc_change == pytest.approx(expected, abs=0.005)
    assert p.days[0].kc == pytest.approx(TOMATO.kc_mid + expected, abs=0.005)


def test_kc_end_adjustment_applies_when_kc_end_is_at_least_045():
    late = TOMATO.init_days + TOMATO.dev_days + TOMATO.mid_days + TOMATO.late_days
    plot = dataclasses.replace(NORTH, planting_date=D0 - dt.timedelta(days=late + 10))
    expected = (0.04 * 4 - 0.004 * -25) * (TOMATO.height_m / 3) ** 0.3
    p = plan(plot=plot, forecast=days(1, wind=50.0, rh=5.0))
    assert p.days[0].kc == pytest.approx(TOMATO.kc_end + expected, abs=0.005)


def test_kc_end_is_not_adjusted_below_045():
    low_end = dataclasses.replace(TOMATO, kc_end=0.40)
    late = low_end.total_days
    plot = dataclasses.replace(NORTH, planting_date=D0 - dt.timedelta(days=late + 10))
    p = plan(plot=plot, crop=low_end, forecast=days(1, wind=50.0, rh=5.0))
    assert p.days[0].kc == 0.40


# --- season ended, roots, rain, uniformity, minutes ----------------------------------------------

def test_season_ended_still_gives_a_plan_with_warning_and_kc_end():
    plot = dataclasses.replace(NORTH, planting_date=D0 - dt.timedelta(days=TOMATO.total_days + 5))
    p = plan(plot=plot)
    assert p.season_ended
    assert [w.code for w in p.warnings] == ["SEASON_ENDED"]
    assert {d.stage for d in p.days} == {"ended"}
    assert {d.kc for d in p.days} == {TOMATO.kc_end}
    assert len(p.days) == 3


def test_root_depth_grows_linearly_to_30cm_then_stays():
    dev_end = TOMATO.init_days + TOMATO.dev_days

    def zr(d):
        plot = dataclasses.replace(NORTH, planting_date=D0 - dt.timedelta(days=d))
        return plan(plot=plot).assumptions.root_depth_m

    assert zr(0) == 0.1
    assert zr(dev_end // 2) == pytest.approx(0.2, abs=0.005)
    assert zr(dev_end) == 0.3
    assert zr(dev_end + 30) == 0.3


def test_rain_threshold_is_02_et0():
    # moisture 5: depletion 26.25 (trigger 15.75). Rain 0.99 < 1.0 is ignored; 1.0 counts.
    ignored = plan(forecast=days(1, rain=(0.99,)), moisture=9).days[0]
    counted = plan(forecast=days(1, rain=(1.0,)), moisture=9).days[0]
    assert ignored.reason == RAIN_IGNORED and counted.reason == RAIN_COUNTED
    assert counted.soil_water_end_mm == pytest.approx(ignored.soil_water_end_mm + 1.0, abs=0.01)


def test_uniformity_factor_applies_only_to_irrigation():
    p1 = plan(uf=1.0)
    p2 = plan(uf=1.2)
    assert p1.days[0].irrigation_mm == p2.days[0].irrigation_mm == 21.0
    assert p1.days[0].litres == 21000 and p2.days[0].litres == 25200
    assert p1.days[0].soil_water_end_mm == p2.days[0].soil_water_end_mm
    assert p1.days[1].litres == p2.days[1].litres == 0


def test_minutes_are_rounded_up():
    # 21000 L at 1666.67 L/h = 756.0 min exactly; 23100 L = 831.6 -> 832.
    assert plan(uf=1.0).days[0].run_minutes == 756
    assert plan().days[0].run_minutes == 832


def test_totals_are_sums_of_the_daily_rounded_values():
    p = plan(plot=GREENHOUSE, crop=PEPPER, flow=2.0, moisture=0)
    assert p.totals.litres == sum(d.litres for d in p.days)
    assert p.totals.run_minutes == sum(d.run_minutes for d in p.days)


def test_stale_days_and_warning():
    p = plan(forecast=days(stale=True))
    assert all(d.stale for d in p.days)
    assert [w.code for w in p.warnings] == ["STALE_FORECAST"]


def test_fresh_forecast_has_no_stale_flag():
    assert not any(d.stale for d in plan().days)


def test_depletion_is_capped_at_capacity():
    # Moisture 0 and a huge ET0: the bucket cannot be more than empty.
    p = plan(forecast=days(2, et0=500.0), moisture=0, cap=10**6)
    assert p.days[0].soil_water_end_mm == 0.0
    assert p.days[1].irrigation_mm == pytest.approx(p.assumptions.soil_capacity_mm, abs=0.1)


@pytest.mark.parametrize("moisture", [-1, 11])
def test_soil_moisture_out_of_range_is_an_error(moisture):
    with pytest.raises(ValueError, match="soil_moisture"):
        plan(moisture=moisture)


def test_empty_forecast_is_an_error():
    with pytest.raises(ValueError, match="forecast"):
        engine.build_plan(NORTH, TOMATO, 175, 1.0, [], 5, 1.1, 1440)


# --- auditability: every number can be reproduced from the numbers shown ---------------------------

def audit_plans():
    def planted(days_ago):
        return dataclasses.replace(NORTH, planting_date=D0 - dt.timedelta(days=days_ago))

    dev_mid = TOMATO.init_days + TOMATO.dev_days // 3
    late = TOMATO.init_days + TOMATO.dev_days + TOMATO.mid_days + 4
    return {
        "mid season": plan(),
        "rain": plan(forecast=days(7, rain=(10.0, 0.8, 20.0, 1.0, 0, 3.3, 0)), moisture=4),
        "season ended": plan(plot=planted(TOMATO.total_days + 5), forecast=days(7, et0=3.37)),
        "capped": plan(moisture=0, forecast=days(4, et0=2.76, wind=5.1, rh=31.0)),
        "capped, small cap": plan(moisture=2, cap=300, forecast=days(5)),
        "first planting": plan(plot=GREENHOUSE, crop=PEPPER, flow=2.0, moisture=0, forecast=days(7, et0=2.76)),
        "climate adjustment": plan(plot=planted(dev_mid), forecast=days(7, et0=2.76, wind=5.1, rh=31.0)),
        "late stage, odd numbers": plan(plot=planted(late), forecast=days(7, et0=4.37, wind=3.3, rh=61.0), moisture=3),
        "dev stage, odd soil": plan(plot=planted(dev_mid), forecast=days(7, et0=3.13, wind=1.7, rh=38.0), soil=163, moisture=7),
    }


@pytest.mark.parametrize("name", list(audit_plans()))
def test_every_number_is_reproducible_from_the_shown_numbers(name):
    p = audit_plans()[name]
    flow = p.assumptions.system_flow_lph
    for d in p.days:
        assert d.need_mm == round(d.kc * d.et0_mm, 2)
        assert d.litres == round(d.irrigation_mm * NORTH_OR(p, name).area_m2 * p.assumptions.uniformity_factor)
        expected_minutes = math.ceil(round(d.litres / flow * 60, 9)) if d.litres else 0
        assert d.run_minutes == expected_minutes
        assert d.soil_water_end_pct == round(d.soil_water_end_mm / d.soil_capacity_mm * 100, 2)
    assert p.days[0].soil_capacity_mm == p.assumptions.soil_capacity_mm
    assert all(d.run_minutes <= (300 if name == "capped, small cap" else 1440) for d in p.days)
    assert p.assumptions.application_rate_mm_per_h == round(flow / NORTH_OR(p, name).area_m2, 2)


def NORTH_OR(p, name):
    return GREENHOUSE if name == "first planting" else NORTH


def test_the_water_balance_adds_up_in_the_shown_numbers():
    # Depletion is in whole hundredths of mm: capacity - end is what was shown the day before, plus need.
    p = plan(forecast=days(7, et0=2.76, wind=5.1, rh=31.0))
    for before, after in zip(p.days, p.days[1:]):
        if after.irrigation_mm == 0 and after.rain_mm < 0.2 * after.et0_mm:
            shown_depletion = before.soil_capacity_mm - before.soil_water_end_mm
            assert after.soil_capacity_mm - after.soil_water_end_mm == pytest.approx(
                shown_depletion + after.need_mm, abs=0.0051)


# --- daily cap on the run time -------------------------------------------------------------------

CAPPED = "Irrigate, capped at 24 h a day: the rest of the refill carries to the next day"


def test_north_block_dry_soil_is_capped_at_24h_and_the_rest_carries_over():
    # Hand calculation: TAW 52.5, depletion 52.5. 1440 min at 1666.67 L/h = 40000.08 L; / (1000 m2 x 1.1)
    # = 36.36 mm (36.37 mm = 40007 L = 1441 min). Left 16.14, + need 5.75 = 21.89 -> irrigated next morning.
    p = plan(moisture=0, forecast=days(2))
    assert [day_row(d) for d in p.days] == [
        ("2026-11-18", "mid", 5.0, 0.0, 1.15, 5.75, 36.36, 39996, 1440, 30.61, 58.30, False, CAPPED),
        ("2026-11-19", "mid", 5.0, 0.0, 1.15, 5.75, 21.89, 24079, 867, 46.75, 89.05, False, IRRIGATE),
    ]
    assert p.today == engine.Today(date=D0, irrigate=True, run_minutes=1440)
    assert [w.code for w in p.warnings] == ["IRRIGATION_CAPPED"]
    assert p.assumptions.application_rate_mm_per_h == 1.67


def test_capped_warning_says_need_rate_hours_and_that_speed_changes_only_time():
    (w,) = plan(moisture=0, forecast=days(2)).warnings
    assert "52.5 mm" in w.message and "1.67 mm/h" in w.message and "35 h" in w.message
    assert "time" in w.message and "several days" in w.message


def test_capped_warning_appears_once_even_if_several_days_are_capped():
    p = plan(moisture=2, cap=300, forecast=days(5))
    assert sum(d.run_minutes == 300 or d.reason.startswith("Irrigate, capped") for d in p.days) >= 2
    assert [w.code for w in p.warnings] == ["IRRIGATION_CAPPED"]


def test_the_cap_comes_from_the_argument():
    reason = plan(moisture=0, forecast=days(1), cap=720).days[0]
    assert reason.run_minutes <= 720 and reason.reason == "Irrigate, capped at 12 h a day: the rest of the refill carries to the next day"


def test_below_the_cap_nothing_changes():
    p = plan(forecast=days(2))
    assert p.days[0].irrigation_mm == 21.0 and p.days[0].reason == IRRIGATE
    assert p.warnings == []
