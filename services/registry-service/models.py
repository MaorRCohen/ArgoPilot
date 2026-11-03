from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Farm(BaseModel):
    id: str
    name: str


class FarmCreate(RequestModel):
    name: str = Field(min_length=1)


class FarmPatch(RequestModel):
    name: str | None = Field(default=None, min_length=1)


class Plot(BaseModel):
    id: str
    farm_id: str
    name: str
    area_m2: float
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: float
    emitter_spacing_m: float
    emitter_id: str
    lat: float
    lon: float


class PlotCreate(RequestModel):
    name: str = Field(min_length=1)
    farm_id: str
    area_m2: float = Field(gt=0)
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: float = Field(gt=0)
    emitter_spacing_m: float = Field(gt=0)
    emitter_id: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class PlotPatch(RequestModel):
    name: str | None = Field(default=None, min_length=1)
    farm_id: str | None = None
    area_m2: float | None = Field(default=None, gt=0)
    crop_id: str | None = None
    planting_date: date | None = None
    soil_id: str | None = None
    row_spacing_m: float | None = Field(default=None, gt=0)
    emitter_spacing_m: float | None = Field(default=None, gt=0)
    emitter_id: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class Crop(BaseModel):
    id: str
    name: str


class Soil(BaseModel):
    id: str
    name: str
    available_water_mm_per_m: int


class Emitter(BaseModel):
    id: str
    name: str
    flow_lph: float
