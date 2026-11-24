from collections.abc import Callable, Iterator
from datetime import date, datetime
import math
import uuid
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI
from sqlalchemy import Connection
from timezonefinder import TimezoneFinder

from db import (
    ForeignKeyViolation,
    UniqueViolation,
    count_plots,
    delete_farm,
    delete_plot,
    farm_name_taken,
    get_connection,
    get_row,
    insert_farm,
    insert_plot,
    list_rows,
    plot_name_taken,
    select_plots,
    sum_plot_area,
    update_farm_name,
    SchemaMissing,
    check_farms_table,
    update_plot_fields,
)
from errors import RETRY_AFTER_SECONDS, ApiError, register_error_handlers
from models import (
    Crop,
    Emitter,
    Farm,
    FarmArea,
    FarmCreate,
    IrrigationVolume,
    IrrigationVolumeRequest,
    FarmPatch,
    Plot,
    PlotArea,
    PlotCreate,
    PlotPatch,
    Soil,
)

app = FastAPI(title="AgroPilot registry-service", version="0.1.0")
register_error_handlers(app)

timezone_finder = TimezoneFinder()
REFERENCE_TABLES = {
    "farm_id": "farms",
    "crop_id": "crops",
    "soil_id": "soils",
    "emitter_id": "emitters",
}
PLOT_NAME_CONFLICT = "plot name already exists in this farm"


def get_db() -> Iterator[Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_farm_or_404(conn: Connection, farm_id: str) -> dict:
    row = get_row(conn, "farms", farm_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Farm not found")
    return row


def get_plot_or_404(conn: Connection, plot_id: str) -> dict:
    row = get_row(conn, "plots", plot_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Plot not found")
    return row


def check_references(conn: Connection, values: dict) -> None:
    for field, table in REFERENCE_TABLES.items():
        if get_row(conn, table, values[field]) is None:
            raise ApiError(422, "VALIDATION", f"{field}: not found")


def check_planting_date(planting_date: str, lat: float, lon: float) -> None:
    # Compare against the local date at the plot, so a plot east of UTC can plant "today" early.
    tz_name = timezone_finder.timezone_at(lat=lat, lng=lon) or "UTC"
    if date.fromisoformat(planting_date) > datetime.now(ZoneInfo(tz_name)).date():
        raise ApiError(422, "VALIDATION", "planting_date is in the future")


def write_plot(write: Callable[..., None], *args) -> None:
    # Safety net for the UNIQUE(farm_id, name) constraint, in case two requests race past the check.
    try:
        write(*args)
    except UniqueViolation:
        raise ApiError(409, "CONFLICT", PLOT_NAME_CONFLICT)
    except ForeignKeyViolation:
        raise ApiError(422, "VALIDATION", "referenced id: not found")


@app.get("/health")
def health(conn: Connection = Depends(get_db)) -> dict[str, str]:
    try:
        check_farms_table(conn)
    except SchemaMissing:
        # Reachable, but the schema is not set up: not ready yet, so retry later.
        raise ApiError(
            503,
            "UNAVAILABLE",
            "Database schema is missing: no farms table",
            {"Retry-After": str(RETRY_AFTER_SECONDS)},
        )
    return {"status": "ok"}


@app.post("/v1/farms", status_code=201, response_model=Farm)
def create_farm(body: FarmCreate, conn: Connection = Depends(get_db)) -> dict:
    if farm_name_taken(conn, body.name):
        raise ApiError(409, "CONFLICT", "farm name already exists")
    farm = {"id": str(uuid.uuid4()), "name": body.name}
    insert_farm(conn, farm["id"], farm["name"])
    return farm


@app.get("/v1/farms", response_model=list[Farm])
def list_farms(conn: Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "farms")


@app.get("/v1/farms/{farm_id}", response_model=Farm)
def get_farm(farm_id: str, conn: Connection = Depends(get_db)) -> dict:
    return get_farm_or_404(conn, farm_id)


@app.get("/v1/farms/{farm_id}/area", response_model=FarmArea)
def get_farm_area(farm_id: str, conn: Connection = Depends(get_db)) -> dict:
    get_farm_or_404(conn, farm_id)
    return {"farm_id": farm_id, "total_area_m2": sum_plot_area(conn, farm_id)}


@app.patch("/v1/farms/{farm_id}", response_model=Farm)
def update_farm(farm_id: str, body: FarmPatch, conn: Connection = Depends(get_db)) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise ApiError(422, "VALIDATION", "no fields to update")
    if "name" in changes and changes["name"] is None:
        raise ApiError(422, "VALIDATION", "name: must not be null")
    get_farm_or_404(conn, farm_id)
    if farm_name_taken(conn, body.name, exclude_id=farm_id):
        raise ApiError(409, "CONFLICT", "farm name already exists")
    update_farm_name(conn, farm_id, body.name)
    return {"id": farm_id, "name": body.name}


@app.delete("/v1/farms/{farm_id}", status_code=204)
def remove_farm(farm_id: str, conn: Connection = Depends(get_db)) -> None:
    get_farm_or_404(conn, farm_id)
    plots = count_plots(conn, farm_id)
    if plots > 0:
        raise ApiError(409, "CONFLICT", f"farm has {plots} plots")
    try:
        delete_farm(conn, farm_id)
    except ForeignKeyViolation:
        raise ApiError(409, "CONFLICT", "farm has plots")


@app.post("/v1/plots", status_code=201, response_model=Plot)
def create_plot(body: PlotCreate, conn: Connection = Depends(get_db)) -> dict:
    plot = {"id": str(uuid.uuid4()), **body.model_dump(mode="json")}
    check_references(conn, plot)
    check_planting_date(plot["planting_date"], plot["lat"], plot["lon"])
    if plot_name_taken(conn, plot["farm_id"], plot["name"]):
        raise ApiError(409, "CONFLICT", PLOT_NAME_CONFLICT)
    write_plot(insert_plot, conn, plot)
    return plot


@app.get("/v1/plots", response_model=list[Plot])
def list_plots(
    farm_id: str | None = None, conn: Connection = Depends(get_db)
) -> list[dict]:
    if farm_id is not None:
        get_farm_or_404(conn, farm_id)
    return select_plots(conn, farm_id)


@app.get("/v1/plots/{plot_id}", response_model=Plot)
def get_plot(plot_id: str, conn: Connection = Depends(get_db)) -> dict:
    return get_plot_or_404(conn, plot_id)


@app.get("/v1/plots/{plot_id}/area", response_model=PlotArea)
def get_plot_area(plot_id: str, conn: Connection = Depends(get_db)) -> dict:
    plot = get_plot_or_404(conn, plot_id)
    return {
        "plot_id": plot["id"],
        "area_m2": plot["area_m2"],
        "area_dunam": plot["area_m2"] / 1000,  # 1 dunam = 1000 m2; no rounding, per the spec
    }


@app.patch("/v1/plots/{plot_id}", response_model=Plot)
def update_plot(plot_id: str, body: PlotPatch, conn: Connection = Depends(get_db)) -> dict:
    stored = get_plot_or_404(conn, plot_id)
    changes = body.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise ApiError(422, "VALIDATION", "no fields to update")
    nulls = [field for field, value in changes.items() if value is None]
    if nulls:
        raise ApiError(422, "VALIDATION", f"{nulls[0]}: must not be null")
    merged = {**stored, **changes}
    check_references(conn, merged)
    check_planting_date(merged["planting_date"], merged["lat"], merged["lon"])
    if plot_name_taken(conn, merged["farm_id"], merged["name"], exclude_id=plot_id):
        raise ApiError(409, "CONFLICT", PLOT_NAME_CONFLICT)
    write_plot(update_plot_fields, conn, plot_id, changes)
    return merged


@app.delete("/v1/plots/{plot_id}", status_code=204)
def remove_plot(plot_id: str, conn: Connection = Depends(get_db)) -> None:
    get_plot_or_404(conn, plot_id)
    delete_plot(conn, plot_id)


@app.get("/v1/crops", response_model=list[Crop])
def list_crops(conn: Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "crops")


@app.get("/v1/crops/{crop_id}", response_model=Crop)
def get_crop(crop_id: str, conn: Connection = Depends(get_db)) -> dict:
    row = get_row(conn, "crops", crop_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Crop not found")
    return row


@app.get("/v1/soils", response_model=list[Soil])
def list_soils(conn: Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "soils")


@app.get("/v1/soils/{soil_id}", response_model=Soil)
def get_soil(soil_id: str, conn: Connection = Depends(get_db)) -> dict:
    row = get_row(conn, "soils", soil_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Soil not found")
    return row


@app.get("/v1/emitters", response_model=list[Emitter])
def list_emitters(conn: Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "emitters")


@app.get("/v1/emitters/{emitter_id}", response_model=Emitter)
def get_emitter(emitter_id: str, conn: Connection = Depends(get_db)) -> dict:
    row = get_row(conn, "emitters", emitter_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Emitter not found")
    return row


@app.post("/v1/irrigation/volume", response_model=IrrigationVolume)
def irrigation_volume(body: IrrigationVolumeRequest) -> dict:
    # 1 mm of water over 1 m² is 1 litre (1 m² x 0.001 m = 0.001 m³ = 1 L).
    volume_l = body.area_m2 * body.depth_mm
    if not math.isfinite(volume_l):
        raise ApiError(422, "VALIDATION", "volume_l: result is too large")
    return {"volume_l": volume_l}
