import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class ForecastDay(BaseModel):
    date: dt.date
    et0_mm: float = Field(ge=0)
    rain_mm: float = Field(ge=0)


class ForecastResponse(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    source: Literal["open-meteo"]
    fetched_at: dt.datetime
    stale: bool
    days: list[ForecastDay]
