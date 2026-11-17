"""Create the registry tables and load the 15 seed rows. Safe to run again.

Run from services/registry-service (DATABASE_URL and DATABASE_OWNER_URL come from .env or the environment):
    uv run python setup_db.py

Nothing is deleted or overwritten. Missing tables are created, missing seed rows are inserted,
and everything happens in one transaction: if anything fails, nothing is saved.
"""

import sys

from sqlalchemy import (
    REAL,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Connection, Engine

# Same logical types as seed_registry.sh: SQLite REAL, PostgreSQL double precision.
Real = Float().with_variant(REAL(), "sqlite")

metadata = MetaData()

Table("farms", metadata,
      Column("id", Text, primary_key=True),
      Column("name", Text, nullable=False))

Table("crops", metadata,
      Column("id", Text, primary_key=True),
      Column("name", Text, nullable=False))

Table("soils", metadata,
      Column("id", Text, primary_key=True),
      Column("name", Text, nullable=False),
      Column("available_water_mm_per_m", Integer, nullable=False))

Table("emitters", metadata,
      Column("id", Text, primary_key=True),
      Column("name", Text, nullable=False),
      Column("flow_lph", Real, nullable=False))

Table("plots", metadata,
      Column("id", Text, primary_key=True),
      Column("farm_id", Text, ForeignKey("farms.id"), nullable=False),
      Column("name", Text, nullable=False),
      Column("area_m2", Real, nullable=False),
      Column("crop_id", Text, ForeignKey("crops.id"), nullable=False),
      Column("planting_date", Text, nullable=False),
      Column("soil_id", Text, ForeignKey("soils.id"), nullable=False),
      Column("row_spacing_m", Real, nullable=False),
      Column("emitter_spacing_m", Real, nullable=False),
      Column("emitter_id", Text, ForeignKey("emitters.id"), nullable=False),
      Column("lat", Real, nullable=False),
      Column("lon", Real, nullable=False),
      UniqueConstraint("farm_id", "name"))

# The same 15 rows as seed_registry.sh, in foreign-key order.
SEED_ROWS: dict[str, list[dict]] = {
    "crops": [
        {"id": "tomato", "name": "Tomato"},
        {"id": "bell-pepper", "name": "Bell pepper"},
    ],
    "soils": [
        {"id": "sand", "name": "Sand", "available_water_mm_per_m": 83},
        {"id": "loam", "name": "Loam", "available_water_mm_per_m": 175},
        {"id": "clay-loam", "name": "Clay loam", "available_water_mm_per_m": 200},
    ],
    "emitters": [
        {"id": "dripnet-pc-0.6", "name": "DripNet PC", "flow_lph": 0.6},
        {"id": "dripnet-pc-1.0", "name": "DripNet PC", "flow_lph": 1.0},
        {"id": "dripnet-pc-1.6", "name": "DripNet PC", "flow_lph": 1.6},
        {"id": "dripnet-pc-2.0", "name": "DripNet PC", "flow_lph": 2.0},
    ],
    "farms": [
        {"id": "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001", "name": "Demo cooperative"},
        {"id": "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004", "name": "East farm"},
    ],
    "plots": [
        {
            "id": "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002",
            "farm_id": "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001",
            "name": "North block", "area_m2": 1000, "crop_id": "tomato",
            "planting_date": "2026-03-01", "soil_id": "loam",
            "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-1.0",
            "lat": 31.25, "lon": 34.79,
        },
        {
            "id": "d9a4e2c1-5e3f-4b6a-9c33-2e7f4a803003",
            "farm_id": "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001",
            "name": "East block", "area_m2": 800, "crop_id": "bell-pepper",
            "planting_date": "2026-04-12", "soil_id": "clay-loam",
            "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-1.6",
            "lat": 31.26, "lon": 34.80,
        },
        {
            "id": "e0b5f3d2-6f40-4c7b-8d44-3f8a5b914004",
            "farm_id": "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004",
            "name": "West block", "area_m2": 1500, "crop_id": "tomato",
            "planting_date": "2026-02-15", "soil_id": "sand",
            "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-0.6",
            "lat": 31.40, "lon": 34.60,
        },
        {
            "id": "f1c6a4e3-7051-4d8c-9e55-4a9b6c025005",
            "farm_id": "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004",
            "name": "Greenhouse", "area_m2": 400, "crop_id": "bell-pepper",
            "planting_date": "2026-05-01", "soil_id": "loam",
            "row_spacing_m": 1.2, "emitter_spacing_m": 0.3, "emitter_id": "dripnet-pc-2.0",
            "lat": 31.41, "lon": 34.61,
        },
    ],
}


def make_engine(url: str) -> Engine:
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _connect(dbapi_conn, _record):
            # sqlite3 would commit CREATE TABLE at once; with this, SQLAlchemy's BEGIN covers the DDL too.
            dbapi_conn.isolation_level = None
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

        @event.listens_for(engine, "begin")
        def _begin(conn):
            conn.exec_driver_sql("BEGIN")
    return engine


def _insert_missing(conn: Connection, table: Table, rows: list[dict]) -> None:
    # Keyed on id: a row with the same id is left as it is; a name clash with another id fails loudly.
    insert = postgresql.insert if conn.dialect.name == "postgresql" else sqlite.insert
    conn.execute(insert(table).on_conflict_do_nothing(index_elements=["id"]), rows)


def run_setup(url: str) -> dict[str, int]:
    """Create missing tables and insert missing seed rows in one transaction. Returns row counts."""
    engine = make_engine(url)
    try:
        with engine.begin() as conn:
            metadata.create_all(conn, checkfirst=True)
            for name, rows in SEED_ROWS.items():
                _insert_missing(conn, metadata.tables[name], rows)
            return {
                name: conn.execute(select(func.count()).select_from(table)).scalar_one()
                for name, table in metadata.tables.items()
            }
    finally:
        engine.dispose()


def main() -> int:
    try:
        from config import settings  # also checks DATABASE_URL, which config requires
    except Exception as exc:  # config's SettingsError: it names the variable and never prints values
        print(exc, file=sys.stderr)
        return 1
    if settings.database_owner_url is None:
        print("DATABASE_OWNER_URL is not set. Add it to .env or the environment (see .env.example).",
              file=sys.stderr)
        return 1
    try:
        counts = run_setup(settings.database_owner_url.get_secret_value())
    except Exception as exc:
        print(f"Setup failed, nothing was saved: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    for name, count in counts.items():
        print(f"{name}: {count}")
    print(f"total: {sum(counts.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
