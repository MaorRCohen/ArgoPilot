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
