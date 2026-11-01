from collections.abc import Iterator
import sqlite3

from fastapi import Depends, FastAPI

from db import get_connection, get_row, list_rows
from errors import ApiError, register_error_handlers
from models import Crop, Emitter, Soil

app = FastAPI(title="AgroPilot registry-service", version="0.1.0")
register_error_handlers(app)


def get_db() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
