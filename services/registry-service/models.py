from pydantic import BaseModel, Field


class Farm(BaseModel):
    id: str
    name: str


class FarmCreate(BaseModel):
    name: str = Field(min_length=1)


class FarmPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)


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
