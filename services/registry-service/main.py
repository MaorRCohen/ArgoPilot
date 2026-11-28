import logging
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from datetime import date, datetime
import math
import uuid
from zoneinfo import ZoneInfo

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, Response, UploadFile
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError
from timezonefinder import TimezoneFinder

from config import get_settings, is_account_id

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
    get_plot_photo,
    has_plot_photos_table,
    update_plot_fields,
    upsert_plot_photo,
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
    PlotPhoto,
    Soil,
)

logger = logging.getLogger(__name__)


def check_plot_photos_table() -> None:
    # Startup check. Logged, never fatal: the service still starts, so /health can report the state.
    try:
        with get_connection() as conn:
            exists = has_plot_photos_table(conn)
    except DBAPIError:
        logger.warning("could not check plot_photos table at startup: database unavailable")
        return
    if not exists:
        logger.error("plot_photos table missing - run migrations/001_plot_photos.sql")


def check_bucket_owner_setting() -> None:
    # A malformed owner is logged, never printed, and treated as missing: the service still starts.
    owner = get_settings().aws_s3_bucket_owner
    if owner and not is_account_id(owner):
        logger.error(
            "AWS_S3_BUCKET_OWNER must be exactly 12 digits; photo endpoints answer 503 until it is fixed"
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    check_plot_photos_table()
    check_bucket_owner_setting()
    yield


app = FastAPI(title="AgroPilot registry-service", version="0.1.0", lifespan=lifespan)
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


# Plot photos: the limits, the accepted types and the S3 settings live here, in one place.
MAX_PHOTO_BYTES = 5 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
RETRY_HEADERS = {"Retry-After": str(RETRY_AFTER_SECONDS)}
# Timeouts: a slow S3 answers 503 in seconds instead of holding the request for minutes.
S3_CONFIG = Config(connect_timeout=5, read_timeout=10)


def get_s3() -> BaseClient:
    # Built per request, on first use (not at import), so the service starts without AWS settings.
    return boto3.client("s3", region_name=get_settings().aws_region, config=S3_CONFIG)


def sniff_photo_type(data: bytes) -> str | None:
    # The bytes decide the type, not the Content-Type header: a client can send any header (OWASP).
    if data.startswith(JPEG_MAGIC):
        return "image/jpeg"
    if data.startswith(PNG_MAGIC):
        return "image/png"
    if data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def check_photo(data: bytes, declared: str | None) -> str:
    if not data:
        raise ApiError(422, "VALIDATION", "file: empty")
    if len(data) > MAX_PHOTO_BYTES:
        raise ApiError(422, "VALIDATION", "file: larger than 5 MB")
    detected = sniff_photo_type(data)
    if detected is None:
        raise ApiError(422, "VALIDATION", "file: content is not JPEG, PNG or WEBP")
    if declared != detected:
        raise ApiError(422, "VALIDATION", "file: declared type does not match content")
    return detected


def bucket_owner() -> str | None:
    owner = get_settings().aws_s3_bucket_owner
    return owner if owner and is_account_id(owner) else None


def s3_scope() -> dict[str, str]:
    # The one place S3 calls get their bucket. ExpectedBucketOwner makes S3 refuse a bucket that
    # someone else created with the same name: bucket names are global.
    bucket = get_settings().aws_s3_bucket
    owner = bucket_owner()
    if not bucket or owner is None:
        raise ApiError(503, "UNAVAILABLE", "Photo storage is not configured", RETRY_HEADERS)
    return {"Bucket": bucket, "ExpectedBucketOwner": owner}


def photo_unavailable(exc: BotoCoreError | ClientError, action: str, plot_id: str) -> ApiError:
    # Only validated values and the exception class reach the log. Never the request, and never the
    # exception message, which can repeat request data.
    if isinstance(exc, ClientError) and exc.response["Error"]["Code"] == "AccessDenied":
        logger.error(
            "S3 %s refused with AccessDenied for plot %s: bucket owner mismatch or missing permission (%s)",
            action, plot_id, type(exc).__name__,
        )
    else:
        logger.error("S3 %s failed for plot %s (%s)", action, plot_id, type(exc).__name__)
    return ApiError(503, "UNAVAILABLE", "Photo storage unavailable", RETRY_HEADERS)


def put_photo(
    s3: BaseClient, scope: dict[str, str], plot_id: str, key: str, data: bytes, content_type: str
) -> None:
    try:
        s3.put_object(**scope, Key=key, Body=data, ContentType=content_type)
    except (BotoCoreError, ClientError) as exc:
        raise photo_unavailable(exc, "put_object", plot_id)


def fetch_photo(s3: BaseClient, scope: dict[str, str], plot_id: str, key: str) -> bytes:
    try:
        return s3.get_object(**scope, Key=key)["Body"].read()
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchKey":
            raise ApiError(404, "NOT_FOUND", "Photo not found")
        raise photo_unavailable(exc, "get_object", plot_id)
    except BotoCoreError as exc:
        raise photo_unavailable(exc, "get_object", plot_id)


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


@app.get("/v1/plots/{plot_id}/photo")
def read_plot_photo(
    plot_id: uuid.UUID, conn: Connection = Depends(get_db), s3: BaseClient = Depends(get_s3)
) -> Response:
    # plot_id is a UUID, so FastAPI rejects anything else with a 422 before this code runs.
    pid = str(plot_id)
    get_plot_or_404(conn, pid)
    photo = get_plot_photo(conn, pid)
    if photo is None:
        raise ApiError(404, "NOT_FOUND", "Photo not found")
    data = fetch_photo(s3, s3_scope(), pid, photo["key"])
    # The type is the one stored in our DB, never the one S3 returns. nosniff stops browsers guessing.
    return Response(
        content=data, media_type=photo["content_type"], headers={"X-Content-Type-Options": "nosniff"}
    )


@app.post("/v1/plots/{plot_id}/photo", status_code=201, response_model=PlotPhoto)
def upload_plot_photo(
    plot_id: uuid.UUID,
    file: UploadFile,
    conn: Connection = Depends(get_db),
    s3: BaseClient = Depends(get_s3),
) -> dict:
    pid = str(plot_id)  # a UUID: FastAPI rejects anything else with a 422 first
    plot = get_plot_or_404(conn, pid)
    # One byte past the limit is enough to know the file is too large; never read more than that.
    data = file.file.read(MAX_PHOTO_BYTES + 1)
    content_type = check_photo(data, file.content_type)
    scope = s3_scope()
    key = f"{plot['farm_id']}/{pid}/photo"
    put_photo(s3, scope, pid, key, data, content_type)  # S3 first: if it fails, the DB row is not touched
    upsert_plot_photo(conn, pid, key, content_type)
    return {"plot_id": pid, "key": key, "content_type": content_type}


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
