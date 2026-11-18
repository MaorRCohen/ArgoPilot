import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class ForecastDay(BaseModel):
    date: dt.date
    et0_mm: float = Field(ge=0)
    rain_mm: float = Field(ge=0)
    wind_10m_ms: float = Field(ge=0)
    rh_min_pct: float = Field(ge=0, le=100)


class ForecastResponse(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    source: Literal["open-meteo"]
    fetched_at: dt.datetime
    stale: bool
    days: list[ForecastDay]
