import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "registry.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Table names come from main.py constants, never from request input.
def list_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")]


def get_row(conn: sqlite3.Connection, table: str, row_id: str) -> dict | None:
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    return dict(row) if row else None


def farm_name_taken(conn: sqlite3.Connection, name: str, exclude_id: str | None = None) -> bool:
    row = conn.execute(
        "SELECT 1 FROM farms WHERE name = ? AND id != ?", (name, exclude_id or "")
    ).fetchone()
    return row is not None


def insert_farm(conn: sqlite3.Connection, farm_id: str, name: str) -> None:
    conn.execute("INSERT INTO farms (id, name) VALUES (?, ?)", (farm_id, name))
    conn.commit()


def update_farm_name(conn: sqlite3.Connection, farm_id: str, name: str) -> None:
    conn.execute("UPDATE farms SET name = ? WHERE id = ?", (name, farm_id))
    conn.commit()


def count_plots(conn: sqlite3.Connection, farm_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM plots WHERE farm_id = ?", (farm_id,)).fetchone()[0]


def delete_farm(conn: sqlite3.Connection, farm_id: str) -> None:
    conn.execute("DELETE FROM farms WHERE id = ?", (farm_id,))
    conn.commit()


def select_plots(conn: sqlite3.Connection, farm_id: str | None) -> list[dict]:
    if farm_id is None:
        rows = conn.execute("SELECT * FROM plots ORDER BY id")
    else:
        rows = conn.execute("SELECT * FROM plots WHERE farm_id = ? ORDER BY id", (farm_id,))
    return [dict(row) for row in rows]


def plot_name_taken(
    conn: sqlite3.Connection, farm_id: str, name: str, exclude_id: str | None = None
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM plots WHERE farm_id = ? AND name = ? AND id != ?",
        (farm_id, name, exclude_id or ""),
    ).fetchone()
    return row is not None


def insert_plot(conn: sqlite3.Connection, plot: dict) -> None:
    conn.execute(
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
    conn.commit()


# Column names come from the Pydantic model fields, never from raw request keys.
def update_plot_fields(conn: sqlite3.Connection, plot_id: str, changes: dict) -> None:
    assignments = ", ".join(f"{column} = :{column}" for column in changes)
    conn.execute(f"UPDATE plots SET {assignments} WHERE id = :id", {**changes, "id": plot_id})
    conn.commit()


def delete_plot(conn: sqlite3.Connection, plot_id: str) -> None:
    conn.execute("DELETE FROM plots WHERE id = ?", (plot_id,))
    conn.commit()
