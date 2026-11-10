import logging
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import Connection, Engine, create_engine, event, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, TimeoutError as PoolTimeoutError
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Root logs at WARNING by default, so without this the startup line would never show.
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.propagate = False  # own handler only: no duplicate line if the root logger is configured too

DEFAULT_SQLITE_PATH = Path(__file__).parent / "registry.db"


def database_url() -> str:
    # override=False: a real environment variable beats .env. Unset or empty -> the SQLite file.
    load_dotenv(find_dotenv(usecwd=True), override=False)
    return os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_SQLITE_PATH}"


def scheme_of(url: str) -> str:
    return make_url(url).get_backend_name()


def make_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        # mode=rw: a missing file raises instead of creating an empty DB. NullPool: one connection
        # per request. check_same_thread=False: FastAPI may use two threads in one request.
        parsed = parsed.set(
            database=f"file:{parsed.database}", query={"mode": "rw", "uri": "true"}
        )
        engine = create_engine(
            parsed,
            poolclass=NullPool,
            connect_args={"timeout": 5, "check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

        return engine
    return create_engine(parsed, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def log_database(url: str) -> None:
    # Scheme only: never the password or the full URL.
    logger.info("Using database: %s", scheme_of(url))


_url = database_url()
engine: Engine = make_engine(_url)
log_database(_url)


class UniqueViolation(Exception):
    pass


class ForeignKeyViolation(Exception):
    pass


def get_connection() -> Connection:
    # One connection per request (NullPool on SQLite); the caller closes it.
    return engine.connect()


# Can't open, or locked. Prefix match also covers extended codes (SQLITE_BUSY_TIMEOUT, ...).
RETRYABLE_SQLITE_ERRORS = ("SQLITE_CANTOPEN", "SQLITE_BUSY", "SQLITE_LOCKED")
# Postgres: 57P01/57P02 admin/crash shutdown, 57P03 cannot connect now, 53300 too many connections, 55P03 lock not available, 40P01 deadlock.
RETRYABLE_SQLSTATES = ("57P01", "57P02", "57P03", "53300", "55P03", "40P01")


def is_temporarily_unavailable(exc: DBAPIError | PoolTimeoutError) -> bool:
    # True: the DB may work again soon (503 + Retry-After). False: a bug, retrying will not help.
    if isinstance(exc, PoolTimeoutError):  # connection pool exhausted: not a DBAPIError
        return True
    if exc.connection_invalidated:
        return True
    orig = exc.orig
    sqlite_name = getattr(orig, "sqlite_errorname", None)
    if sqlite_name:
        return sqlite_name.startswith(RETRYABLE_SQLITE_ERRORS)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate:
        return sqlstate.startswith("08") or sqlstate in RETRYABLE_SQLSTATES
    # An OperationalError with no SQLSTATE is a client-side connect failure or timeout.
    return isinstance(exc, OperationalError)


def normalize_row(row) -> dict:
    # Same JSON-ready values on every backend: date -> "YYYY-MM-DD", Decimal -> float, UUID -> str.
    out = {}
    for key, value in dict(row).items():
        if isinstance(value, date):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, UUID):
            value = str(value)
        out[key] = value
    return out


# Postgres's default name for UNIQUE (farm_id, name) on plots.
PLOT_NAME_CONSTRAINT = "plots_farm_id_name_key"
SQLITE_PLOT_NAME_MESSAGE = "UNIQUE constraint failed: plots.farm_id, plots.name"


def _translate(exc: IntegrityError) -> Exception | None:
    # SQLite has no SQLSTATE, so match its message; Postgres gives 23505 / 23503.
    sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    message = str(exc.orig)
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if SQLITE_PLOT_NAME_MESSAGE in message or (
        sqlstate == "23505" and constraint == PLOT_NAME_CONSTRAINT
    ):
        return UniqueViolation(message)
    if sqlstate == "23503" or "FOREIGN KEY constraint failed" in message:
        return ForeignKeyViolation(message)
    return None


def _write(conn: Connection, sql: str, params: dict) -> None:
    try:
        conn.execute(text(sql), params)
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        translated = _translate(exc)
        if translated is None:
            raise
        raise translated from exc


# Table names come from main.py constants, never from request input.
def list_rows(conn: Connection, table: str) -> list[dict]:
    result = conn.execute(text(f"SELECT * FROM {table} ORDER BY id"))
    return [normalize_row(row) for row in result.mappings()]


def get_row(conn: Connection, table: str, row_id: str) -> dict | None:
    row = conn.execute(text(f"SELECT * FROM {table} WHERE id = :id"), {"id": row_id}).mappings().first()
    return normalize_row(row) if row else None


def farm_name_taken(conn: Connection, name: str, exclude_id: str | None = None) -> bool:
    row = conn.execute(
        text("SELECT 1 FROM farms WHERE name = :name AND id != :exclude_id"),
        {"name": name, "exclude_id": exclude_id or ""},
    ).first()
    return row is not None


def insert_farm(conn: Connection, farm_id: str, name: str) -> None:
    _write(conn, "INSERT INTO farms (id, name) VALUES (:id, :name)", {"id": farm_id, "name": name})


def update_farm_name(conn: Connection, farm_id: str, name: str) -> None:
    _write(conn, "UPDATE farms SET name = :name WHERE id = :id", {"id": farm_id, "name": name})


def count_plots(conn: Connection, farm_id: str) -> int:
    return conn.execute(
        text("SELECT COUNT(*) FROM plots WHERE farm_id = :farm_id"), {"farm_id": farm_id}
    ).scalar_one()


def delete_farm(conn: Connection, farm_id: str) -> None:
    _write(conn, "DELETE FROM farms WHERE id = :id", {"id": farm_id})


def select_plots(conn: Connection, farm_id: str | None) -> list[dict]:
    if farm_id is None:
        result = conn.execute(text("SELECT * FROM plots ORDER BY id"))
    else:
        result = conn.execute(
            text("SELECT * FROM plots WHERE farm_id = :farm_id ORDER BY id"), {"farm_id": farm_id}
        )
    return [normalize_row(row) for row in result.mappings()]


def plot_name_taken(
    conn: Connection, farm_id: str, name: str, exclude_id: str | None = None
) -> bool:
    row = conn.execute(
        text("SELECT 1 FROM plots WHERE farm_id = :farm_id AND name = :name AND id != :exclude_id"),
        {"farm_id": farm_id, "name": name, "exclude_id": exclude_id or ""},
    ).first()
    return row is not None


def insert_plot(conn: Connection, plot: dict) -> None:
    _write(
        conn,
        """
        INSERT INTO plots (
          id, farm_id, name, area_m2, crop_id, planting_date, soil_id,
          row_spacing_m, emitter_spacing_m, emitter_id, lat, lon
        ) VALUES (
          :id, :farm_id, :name, :area_m2, :crop_id, :planting_date, :soil_id,
          :row_spacing_m, :emitter_spacing_m, :emitter_id, :lat, :lon
        )
        """,
        plot,
    )


# Column names come from the Pydantic model fields, never from raw request keys.
def update_plot_fields(conn: Connection, plot_id: str, changes: dict) -> None:
    assignments = ", ".join(f"{column} = :{column}" for column in changes)
    _write(conn, f"UPDATE plots SET {assignments} WHERE id = :id", {**changes, "id": plot_id})


def delete_plot(conn: Connection, plot_id: str) -> None:
    _write(conn, "DELETE FROM plots WHERE id = :id", {"id": plot_id})
