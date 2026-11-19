"""Response of GET /v1/plots/{id}/plan, and the parts of the upstream answers we rely on."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Upstream(BaseModel):
    """Only the fields we use. Anything missing or of the wrong type makes the whole answer unusable."""

    model_config = ConfigDict(extra="ignore")


class RegistryPlot(Upstream):
    id: str
    name: str
    area_m2: float = Field(gt=0)
    crop_id: str
    planting_date: dt.date
    soil_id: str
    row_spacing_m: float = Field(gt=0)
    emitter_spacing_m: float = Field(gt=0)
    emitter_id: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class RegistrySoil(Upstream):
    available_water_mm_per_m: float = Field(gt=0)


class RegistryEmitter(Upstream):
    flow_lph: float = Field(gt=0)


class WeatherDay(Upstream):
    date: dt.date
    et0_mm: float = Field(ge=0)
    rain_mm: float = Field(ge=0)
    wind_10m_ms: float = Field(ge=0)
    rh_min_pct: float = Field(ge=0, le=100)


class WeatherForecast(Upstream):
    fetched_at: dt.datetime
    stale: bool
    days: list[WeatherDay]


class Warning(BaseModel):
    code: Literal["SEASON_ENDED", "IRRIGATION_CAPPED", "STALE_FORECAST"]
    message: str


class Today(BaseModel):
    date: dt.date
    irrigate: bool
    run_minutes: int


class ClimateAdjustment(BaseModel):
    wind_2m_ms: float
    rh_min_pct: float
    kc_change: float


class Assumptions(BaseModel):
    root_depth_m: float
    soil_capacity_mm: float
    irrigate_when_depleted_pct: int
    uniformity_factor: float
    emitters: float
    system_flow_lph: float
    application_rate_mm_per_h: float
    climate_adjustment: ClimateAdjustment


class Day(BaseModel):
    date: dt.date
    stage: Literal["init", "dev", "mid", "late", "ended"]
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


class Totals(BaseModel):
    litres: int
    run_minutes: int


class PlanResponse(BaseModel):
    plot_id: str
    plot_name: str
    crop: str
    soil_moisture_input: int
    generated_at: dt.datetime
    forecast_fetched_at: dt.datetime
    season_ended: bool
    warnings: list[Warning]
    today: Today
    assumptions: Assumptions
    days: list[Day]
    totals: Totals
