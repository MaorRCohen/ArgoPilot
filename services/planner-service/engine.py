"""The irrigation engine: pure functions, no HTTP, no clock, no files.

Every rule is from .claude/skills/irrigation-calc-reference (formulas.md). Dates come in with the
forecast; crop values come in as a CropProfile read from crop_profiles.json.
"""

import math
from dataclasses import dataclass
from datetime import date

TRIGGER_FRACTION = 0.30      # irrigate when depletion >= 30 % of TAW
RAIN_THRESHOLD = 0.2         # rain under 0.2 x ET0 is ignored
ROOT_START_M = 0.10          # drip root depth at planting
ROOT_FULL_M = 0.30           # ... at the end of the development stage and after
U2_RANGE = (1.0, 6.0)        # m/s, limits of FAO Eq. 62/65
RH_RANGE = (20.0, 80.0)      # %
KC_END_ADJUST_MIN = 0.45     # Eq. 65 applies only when Kc end >= 0.45
U2_FROM_U10 = 4.87 / math.log(67.8 * 10 - 5.42)  # Eq. 47, wind at 10 m -> 2 m

REASON_IRRIGATE = "Irrigate: depletion reached 30% of soil capacity"
REASON_BELOW = "No irrigation: depletion below 30% of soil capacity"
REASON_RAIN_COUNTED = "No irrigation: rain counted, depletion below 30% of soil capacity"
REASON_RAIN_IGNORED = "No irrigation: rain ignored (under 0.2 x ET0), depletion below 30% of soil capacity"


@dataclass(frozen=True)
class CropProfile:
    kc_ini: float
    kc_mid: float
    kc_end: float
    height_m: float
    init_days: int
    dev_days: int
    mid_days: int
    late_days: int

    @property
    def total_days(self) -> int:
        return self.init_days + self.dev_days + self.mid_days + self.late_days


@dataclass(frozen=True)
class PlotInput:
    area_m2: float
    row_spacing_m: float
    emitter_spacing_m: float
    planting_date: date


@dataclass(frozen=True)
class WeatherDay:
    date: date
    et0_mm: float
    rain_mm: float
    wind_10m_ms: float
    rh_min_pct: float
    stale: bool


@dataclass(frozen=True)
class DayPlan:
    date: date
    stage: str
    et0_mm: float
    rain_mm: float
    kc: float
    need_mm: float
    irrigation_mm: float
    litres: int
    run_minutes: int
    soil_capacity_mm: float
    soil_water_end_mm: float
    soil_water_end_pct: float
    stale: bool
    reason: str


@dataclass(frozen=True)
class Warning:
    code: str
    message: str


@dataclass(frozen=True)
class Today:
    date: date
    irrigate: bool
    run_minutes: int


@dataclass(frozen=True)
class ClimateAdjustment:
    wind_2m_ms: float
    rh_min_pct: float
    kc_change: float


@dataclass(frozen=True)
class Assumptions:
    root_depth_m: float
    soil_capacity_mm: float
    irrigate_when_depleted_pct: int
    uniformity_factor: float
    emitters: float
    system_flow_lph: float
    climate_adjustment: ClimateAdjustment


@dataclass(frozen=True)
class Totals:
    litres: int
    run_minutes: int


@dataclass(frozen=True)
class Plan:
    season_ended: bool
    warnings: list[Warning]
    today: Today
    assumptions: Assumptions
    days: list[DayPlan]
    totals: Totals


def _r2(value: float) -> float:
    return round(value, 2) + 0.0  # + 0.0 turns -0.0 into 0.0


def _clamp(value: float, low_high: tuple[float, float]) -> float:
    return min(max(value, low_high[0]), low_high[1])


def _root_depth_m(d: int, crop: CropProfile) -> float:
    dev_end = crop.init_days + crop.dev_days
    return ROOT_START_M + (ROOT_FULL_M - ROOT_START_M) * min(d, dev_end) / dev_end


def _stage_and_kc(d: int, crop: CropProfile, kc_mid: float, kc_end: float) -> tuple[str, float]:
    """Stage and Kc of day d after planting (Eq. 66). kc_mid and kc_end are climate adjusted."""
    dev_start = crop.init_days
    mid_start = dev_start + crop.dev_days
    late_start = mid_start + crop.mid_days
    if d < dev_start:
        return "init", crop.kc_ini
    if d < mid_start:
        return "dev", crop.kc_ini + (d - dev_start) / crop.dev_days * (kc_mid - crop.kc_ini)
    if d < late_start:
        return "mid", kc_mid
    if d < crop.total_days:
        return "late", kc_mid + (d - late_start) / crop.late_days * (kc_end - kc_mid)
    return "ended", kc_end


def _climate_adjustment(crop: CropProfile, forecast: list[WeatherDay]) -> tuple[float, float, float]:
    """Eq. 62 / 65 term from the plan-day averages: returns (u2, RHmin, adjustment)."""
    u2 = _clamp(sum(f.wind_10m_ms for f in forecast) / len(forecast) * U2_FROM_U10, U2_RANGE)
    rh = _clamp(sum(f.rh_min_pct for f in forecast) / len(forecast), RH_RANGE)
    adjustment = (0.04 * (u2 - 2) - 0.004 * (rh - 45)) * (crop.height_m / 3) ** 0.3
    return u2, rh, adjustment


def build_plan(
    plot: PlotInput,
    crop: CropProfile,
    available_water_mm_per_m: float,
    flow_lph: float,
    forecast: list[WeatherDay],
    soil_moisture: int,
    uniformity_factor: float,
) -> Plan:
    if not forecast:
        raise ValueError("forecast has no days")
    if not 0 <= soil_moisture <= 10:
        raise ValueError("soil_moisture must be from 0 to 10")
    for name, value in [("area_m2", plot.area_m2), ("row_spacing_m", plot.row_spacing_m),
                        ("emitter_spacing_m", plot.emitter_spacing_m), ("flow_lph", flow_lph),
                        ("available_water_mm_per_m", available_water_mm_per_m),
                        ("uniformity_factor", uniformity_factor)]:
        if not value > 0:
            raise ValueError(f"{name} must be greater than 0")

    u2, rh, adjustment = _climate_adjustment(crop, forecast)
    kc_mid = crop.kc_mid + adjustment
    kc_end = crop.kc_end + adjustment if crop.kc_end >= KC_END_ADJUST_MIN else crop.kc_end

    emitters = plot.area_m2 / (plot.row_spacing_m * plot.emitter_spacing_m)
    system_flow_lph = _r2(emitters * flow_lph)  # the shown value: minutes are computed from it

    def day_index(day: WeatherDay) -> int:
        # A date before planting (time-zone edge) counts as the planting day.
        return max((day.date - plot.planting_date).days, 0)

    def taw(d: int) -> float:
        # The shown capacity: mm per m x root depth of that day, rounded to 0.01 mm.
        return _r2(available_water_mm_per_m * _root_depth_m(d, crop))

    # From here on every step starts from the rounded numbers that the response shows, so each shown
    # number can be reproduced by hand from the other shown numbers (see SKILL.md, rounding).
    depletion = _r2(taw(day_index(forecast[0])) * (1 - soil_moisture / 10))
    days: list[DayPlan] = []
    for day in forecast:
        d = day_index(day)
        capacity = taw(d)
        stage, kc_full = _stage_and_kc(d, crop, kc_mid, kc_end)
        kc, et0, rain = _r2(kc_full), _r2(day.et0_mm), _r2(day.rain_mm)

        rain_counted = rain >= RAIN_THRESHOLD * et0
        if rain_counted:
            depletion = _r2(max(depletion - rain, 0.0))
        irrigation_mm = 0.0
        # round(.., 9): float noise must not decide an exact 30 % (5.25 vs 0.3 x 17.5).
        if round(depletion - TRIGGER_FRACTION * capacity, 9) >= 0:
            irrigation_mm, depletion = depletion, 0.0
        need_mm = _r2(kc * et0)
        depletion = _r2(min(depletion + need_mm, capacity))
        end_mm = _r2(capacity - depletion)

        litres = round(irrigation_mm * plot.area_m2 * uniformity_factor)
        # round(.., 9) keeps float noise (120.00000000001) from adding a minute.
        run_minutes = math.ceil(round(litres / system_flow_lph * 60, 9)) if litres > 0 else 0
        if irrigation_mm > 0:
            reason = REASON_IRRIGATE
        elif rain > 0:
            reason = REASON_RAIN_COUNTED if rain_counted else REASON_RAIN_IGNORED
        else:
            reason = REASON_BELOW
        days.append(DayPlan(
            date=day.date, stage=stage, et0_mm=et0, rain_mm=rain, kc=kc, need_mm=need_mm,
            irrigation_mm=irrigation_mm, litres=litres, run_minutes=run_minutes, soil_capacity_mm=capacity,
            soil_water_end_mm=end_mm, soil_water_end_pct=_r2(end_mm / capacity * 100), stale=day.stale,
            reason=reason,
        ))

    first_d = day_index(forecast[0])
    season_ended = days[0].stage == "ended"
    warnings: list[Warning] = []
    if season_ended:
        warnings.append(Warning("SEASON_ENDED", (
            f"The usual season length ({crop.total_days} days) has passed; the plan uses the end-of-season "
            f"Kc {_r2(kc_end)}. Check whether the crop is still in the field.")))
    if any(d.stale for d in days):
        warnings.append(Warning("STALE_FORECAST", "The forecast is not fresh: the weather provider did not answer, "
                                                  "so the last known forecast was used."))
    return Plan(
        season_ended=season_ended,
        warnings=warnings,
        today=Today(date=days[0].date, irrigate=days[0].irrigation_mm > 0, run_minutes=days[0].run_minutes),
        assumptions=Assumptions(
            root_depth_m=round(_root_depth_m(first_d, crop), 3),
            soil_capacity_mm=taw(first_d),
            irrigate_when_depleted_pct=round(TRIGGER_FRACTION * 100),
            uniformity_factor=uniformity_factor,
            emitters=_r2(emitters),
            system_flow_lph=system_flow_lph,
            climate_adjustment=ClimateAdjustment(wind_2m_ms=_r2(u2), rh_min_pct=_r2(rh), kc_change=_r2(adjustment)),
        ),
        days=days,
        totals=Totals(litres=sum(d.litres for d in days), run_minutes=sum(d.run_minutes for d in days)),
    )
