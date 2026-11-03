from collections.abc import Iterator
import sqlite3
import uuid

from fastapi import Depends, FastAPI

from db import (
    count_plots,
    delete_farm,
    farm_name_taken,
    get_connection,
    get_row,
    insert_farm,
    list_rows,
    update_farm_name,
)
from errors import ApiError, register_error_handlers
from models import Crop, Emitter, Farm, FarmCreate, FarmPatch, Soil

app = FastAPI(title="AgroPilot registry-service", version="0.1.0")
register_error_handlers(app)


def get_db() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_farm_or_404(conn: sqlite3.Connection, farm_id: str) -> dict:
    row = get_row(conn, "farms", farm_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Farm not found")
    return row


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/farms", status_code=201, response_model=Farm)
def create_farm(body: FarmCreate, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if farm_name_taken(conn, body.name):
        raise ApiError(409, "CONFLICT", "farm name already exists")
    farm = {"id": str(uuid.uuid4()), "name": body.name}
    insert_farm(conn, farm["id"], farm["name"])
    return farm


@app.get("/v1/farms", response_model=list[Farm])
def list_farms(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "farms")


@app.get("/v1/farms/{farm_id}", response_model=Farm)
def get_farm(farm_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return get_farm_or_404(conn, farm_id)


@app.patch("/v1/farms/{farm_id}", response_model=Farm)
def update_farm(farm_id: str, body: FarmPatch, conn: sqlite3.Connection = Depends(get_db)) -> dict:
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
def remove_farm(farm_id: str, conn: sqlite3.Connection = Depends(get_db)) -> None:
    get_farm_or_404(conn, farm_id)
    plots = count_plots(conn, farm_id)
    if plots > 0:
        raise ApiError(409, "CONFLICT", f"farm has {plots} plots")
    delete_farm(conn, farm_id)


@app.get("/v1/crops", response_model=list[Crop])
def list_crops(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "crops")


@app.get("/v1/crops/{crop_id}", response_model=Crop)
def get_crop(crop_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    row = get_row(conn, "crops", crop_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Crop not found")
    return row


@app.get("/v1/soils", response_model=list[Soil])
def list_soils(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "soils")


@app.get("/v1/soils/{soil_id}", response_model=Soil)
def get_soil(soil_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    row = get_row(conn, "soils", soil_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Soil not found")
    return row


@app.get("/v1/emitters", response_model=list[Emitter])
def list_emitters(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return list_rows(conn, "emitters")


@app.get("/v1/emitters/{emitter_id}", response_model=Emitter)
def get_emitter(emitter_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    row = get_row(conn, "emitters", emitter_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Emitter not found")
    return row
