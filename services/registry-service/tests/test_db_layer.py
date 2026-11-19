from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

import db


@pytest.fixture
def conn(db_path):
    connection = db.get_connection()
    yield connection
    connection.close()


def first_plot(conn) -> dict:
    return db.select_plots(conn, None)[0]


def test_normalize_row_converts_date_decimal_uuid():
    uid = UUID("12345678-1234-5678-1234-567812345678")
    row = {"d": date(2026, 3, 1), "n": Decimal("31.25"), "u": uid, "s": "x", "i": 3, "f": 1.5, "none": None}
    out = db.normalize_row(row)
    assert out == {"d": "2026-03-01", "n": 31.25, "u": str(uid), "s": "x", "i": 3, "f": 1.5, "none": None}
    assert isinstance(out["n"], float)


def test_delete_farm_with_plots_raises_foreign_key_violation(conn):
    plot = first_plot(conn)
    with pytest.raises(db.ForeignKeyViolation):
        db.delete_farm(conn, plot["farm_id"])


def test_insert_plot_with_unknown_crop_raises_foreign_key_violation(conn):
    plot = {**first_plot(conn), "id": "new-plot", "name": "brand new", "crop_id": "no-such-crop"}
    with pytest.raises(db.ForeignKeyViolation):
        db.insert_plot(conn, plot)


def test_duplicate_plot_name_raises_unique_violation(conn):
    plot = {**first_plot(conn), "id": "new-plot"}
    with pytest.raises(db.UniqueViolation):
        db.insert_plot(conn, plot)


def test_other_integrity_error_is_not_translated(conn):
    with pytest.raises(IntegrityError):
        db.insert_farm(conn, "farm-x", None)


def test_duplicate_plot_id_is_not_translated(conn):
    plot = {**first_plot(conn), "name": "another name"}
    with pytest.raises(IntegrityError) as info:
        db.insert_plot(conn, plot)
    assert not isinstance(info.value, db.UniqueViolation)


def test_duplicate_farm_id_is_not_translated(conn):
    farm_id = first_plot(conn)["farm_id"]
    with pytest.raises(IntegrityError) as info:
        db.insert_farm(conn, farm_id, "some new name")
    assert not isinstance(info.value, db.UniqueViolation)


def fake_pg_error(sqlstate: str, constraint_name: str):
    orig = SimpleNamespace(sqlstate=sqlstate, diag=SimpleNamespace(constraint_name=constraint_name))
    return SimpleNamespace(orig=orig)


def test_translate_postgres_plot_name_constraint_is_unique_violation():
    assert isinstance(db._translate(fake_pg_error("23505", "plots_farm_id_name_key")), db.UniqueViolation)


def test_translate_postgres_other_unique_constraint_is_not_translated():
    assert db._translate(fake_pg_error("23505", "plots_pkey")) is None
