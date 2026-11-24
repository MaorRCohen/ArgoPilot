# DATABASE_URL (SQLite / PostgreSQL) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `registry-service` runs on SQLite (default, tests) or PostgreSQL (production) chosen by `DATABASE_URL`, with identical API behaviour.

**Architecture:** `db.py` owns a SQLAlchemy Core engine (raw `text()` SQL, no ORM), translates driver errors into `UniqueViolation` / `ForeignKeyViolation` / a "temporarily unavailable" test, and normalizes returned rows. `errors.py` and `main.py` become driver-neutral. The same test suite runs on Postgres when `TEST_DATABASE_URL` is set.

**Tech Stack:** FastAPI, SQLAlchemy 2.x Core, `psycopg[binary]` (psycopg 3), `python-dotenv`, pytest, k6, Docker (started by the owner).

**Execution:** subagent-driven, one fresh reviewer per task; implementer subagents use a cheap model.

**Spec:** [docs/superpowers/specs/2026-11-10-database-url-design.md](../specs/2026-11-10-database-url-design.md). Read it first; decision numbers below ("D3") refer to it.

## Global Constraints

- Work from `services/registry-service`. Tests run with `uv run pytest`. **Do not commit or push** (CLAUDE.md), so no commit steps.
- **Never touch the real `registry.db`**: no task reads, reseeds or deletes it. Tests and the k6 run use temp copies only (`seed_registry.sh <temp path>`, `DATABASE_URL=sqlite:///<temp path>`).
- No MySQL code, ORM, query builder, models, migrations, new endpoints, pagination, CORS, auth. Keep files: `main.py`, `db.py`, `models.py`, `errors.py` (+ tests).
- All DB access and all DB-specific code stay in `db.py`. `main.py` changes only: type hints + catches of `UniqueViolation` / `ForeignKeyViolation`.
- Behaviour must not change on SQLite: same status codes, `application/problem+json` bodies, `code` values, `Retry-After: 30` on 503.
- SQLite: `NullPool`, `PRAGMA foreign_keys = ON` in a connect event, `mode=rw`, `timeout=5`, `check_same_thread=False`. Postgres: default pool, `pool_pre_ping=True`, `connect_timeout=5`.
- `load_dotenv(override=False)`: a real environment variable beats `.env`. Log the database **scheme only**, never the password or URL.
- Existing decisions in CLAUDE.md still apply (error codes, 409/422 rules, `extra="forbid"`).

## Review Focus

- `DATABASE_URL=""` (set but empty) is treated as unset -> default SQLite. Test in T2.
- A URL with a password never appears in logs or error responses. Test in T2.
- Guard bypass attempts: host `localhost.evil.com`, `user@evil/db_test`, no database name, db name without "test", a non-localhost host with "test" in the db name. Tests in T6.
- `.env` points at a real DB while tests run: tests still use the temp DB. Test in T2.
- A missing SQLite file stays 503 and is never created (existing test, must still pass in T3).

---

### Task 1: Dependencies and config files

**Files:**
- Modify: `pyproject.toml`; Create: `.env.example`; Check: `../../.gitignore` (already ignores `.env`, `!.env.example`)

**Interfaces:** Produces: `sqlalchemy`, `psycopg[binary]`, `python-dotenv` importable.

- [ ] **Step 1:** `uv add "sqlalchemy>=2.0" "psycopg[binary]>=3.2" python-dotenv`.
- [ ] **Step 2:** Create `.env.example` with `DATABASE_URL=sqlite:///registry.db` and a commented PostgreSQL example `# DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname`.
- [ ] **Step 3: Verify:** `uv run pytest` still passes (no behaviour change); `git check-ignore .env` prints `.env`; `git status` shows `.env.example` not ignored.

### Task 2: Engine, configuration, startup log, test seam (D1, D2, D4, D8)

**Files:** Modify `db.py`, `tests/conftest.py`; Create `tests/test_config.py`.

**Interfaces:**
- Produces in `db.py`: `DEFAULT_SQLITE_PATH: Path` (next to `db.py`); `database_url() -> str` (reads env after `load_dotenv(override=False)`; unset or empty -> `sqlite:///<DEFAULT_SQLITE_PATH>`); `scheme_of(url: str) -> str` (`"sqlite"` / `"postgresql"`, driver suffix dropped); `make_engine(url: str) -> Engine` (applies the D2 options per scheme; SQLite must open with `mode=rw`); module-level `engine: Engine = make_engine(database_url())`, which logs `Using database: <scheme>` once at import.
- `conftest.py`: sets `os.environ["DATABASE_URL"]` to a temp SQLite file path **before** `import db` / `import main`.

- [ ] **Step 1: Failing tests** in `tests/test_config.py` (use `monkeypatch`, `caplog`, `tmp_path`):
  `test_unset_or_empty_url_uses_default_sqlite` (both cases -> `sqlite:///.../registry.db` next to `db.py`); `test_real_env_var_beats_dotenv` (`.env` in `tmp_path` with another URL, `database_url()` returns the env var; run with `monkeypatch.chdir`); `test_log_has_scheme_only` (URL `postgresql+psycopg://u:secret@h/db`, `make_engine` + log helper: `"secret"` and `"u:secret"` not in `caplog.text`, `"postgresql"` is); `test_tests_use_temp_db_even_if_dotenv_points_elsewhere` (spawn `python -I -c` is not needed: assert `db.engine.url.database` is under pytest's temp dir and not `DEFAULT_SQLITE_PATH`).
- [ ] **Step 2:** Run `uv run pytest tests/test_config.py -v`. Expected: FAIL (names missing).
- [ ] **Step 3:** Implement the interfaces above in `db.py` (keep `get_connection` and the `sqlite3` queries working for now). Update `conftest.py` ordering.
- [ ] **Step 4:** `uv run pytest -v`. Expected: all PASS, including the old suite.

### Task 3: Move all queries to the engine; error translation; row normalization (D1, D9, D10)

**Files:** Modify `db.py`, `main.py` (hints + catches), `tests/conftest.py`; Create `tests/test_db_layer.py`.

**Interfaces:**
- `db.py` produces: `get_connection() -> sqlalchemy.engine.Connection` (from `engine`); `class UniqueViolation(Exception)`, `class ForeignKeyViolation(Exception)`; every query function keeps its current name and signature but takes the SQLAlchemy `Connection`, uses `text()` with named params, and returns normalized rows (`date` -> `"YYYY-MM-DD"`, `Decimal` -> `float`, `UUID` -> `str`). Write functions (`insert_*`, `update_*`, `delete_*`) translate `IntegrityError` into the two exceptions: SQLite by message text (`UNIQUE constraint failed`, `FOREIGN KEY constraint failed`), Postgres by SQLSTATE `23505` / `23503`. Any other integrity error is re-raised unchanged.
- `main.py`: type hints become `Connection`; `write_plot` catches `UniqueViolation` (409, existing message) and `ForeignKeyViolation` (422 `VALIDATION`, detail `"referenced id: not found"`); `remove_farm` catches `ForeignKeyViolation` from `delete_farm` (409 `CONFLICT`, detail `"farm has plots"`). Remove the `sqlite3` import.
- `conftest.py`: the `db_path` fixture now patches `db.engine` with `db.make_engine("sqlite:///<temp copy>")` instead of `db.DB_PATH`.

- [ ] **Step 1: Failing tests** in `tests/test_db_layer.py` (SQLite temp DB via fixtures):
  `test_normalize_row_converts_date_decimal_uuid` (pure unit test on the normalizer: `date(2026,3,1)` -> `"2026-03-01"`, `Decimal("31.25")` -> `31.25` float, `UUID` -> `str`, other values untouched); `test_delete_farm_with_plots_raises_foreign_key_violation` (call `db.delete_farm` directly on a farm with plots, **no precheck**); `test_insert_plot_with_unknown_crop_raises_foreign_key_violation`; `test_duplicate_plot_name_raises_unique_violation`; `test_other_integrity_error_is_not_translated` (NOT NULL violation raises the SQLAlchemy `IntegrityError`).
- [ ] **Step 2:** Run it. Expected: FAIL.
- [ ] **Step 3:** Convert `db.py` and `main.py` as specified. Remove `DB_PATH` and `sqlite3` row code. Update `conftest.py`.
- [ ] **Step 4:** `uv run pytest -v`. Expected: the whole old suite passes unchanged in meaning (if `test_unavailable.py` fails, that is T4's work; leave those two tests failing only until T4 and note it).

### Task 4: 503 / 500 rule, driver-neutral (D3)

**Files:** Modify `errors.py`, `db.py`; Modify `tests/test_unavailable.py`; Create `tests/test_db_errors.py`.

**Interfaces:** `db.py` produces `is_temporarily_unavailable(exc: DBAPIError) -> bool`: True for SQLite `sqlite_errorname` starting `SQLITE_CANTOPEN` / `SQLITE_BUSY` / `SQLITE_LOCKED`; for Postgres: SQLSTATE class `08`, `57P03`, `53300`, `55P03`, `40P01`, connect/timeout failures, and any `exc.connection_invalidated`. `errors.py` registers one handler for `sqlalchemy.exc.DBAPIError`: 503 UNAVAILABLE "Database unavailable" + `Retry-After: 30` if true, else 500 UNAVAILABLE "Internal server error". Response bodies identical to today.

- [ ] **Step 1: Failing tests** in `tests/test_db_errors.py`, driven by building a fake `OperationalError` (`orig` = an object with `sqlstate` / `sqlite_errorname`) and making an endpoint raise it (monkeypatch `db.get_row` or `get_connection`): one parametrized test with a case per row of D3's 503 list (refused: `08006`, timeout, disconnect with `connection_invalidated=True`, too many connections `53300`, lock not available `55P03`, deadlock `40P01`, plus the three SQLite names) asserting 503 + `Retry-After: 30` + problem+json `code == "UNAVAILABLE"`; and 500 cases (`42P01` missing table, `42601` bad SQL, SQLite "no such table"), asserting 500, body `"Internal server error"`, and no driver text in the response.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Existing `test_unavailable.py` tests (missing file -> 503 and not created; empty DB -> 500 without "sqlite" text) must pass as they are; mark them `sqlite_only` (helper added in T5).
- [ ] **Step 4:** `uv run pytest -v`. Expected: all PASS.

### Task 5: Postgres mode in the test fixtures, plus the guard (D5, D6, D7)

**Files:** Create `seed_registry_pg.sql`, `tests/pg_guard.py`, `tests/test_pg_guard.py`; Modify `tests/conftest.py`, `pyproject.toml` (register `sqlite_only` marker).

**Interfaces:** `tests/pg_guard.py`: `assert_safe_to_wipe(url: str) -> None` raises `RuntimeError` unless the host is exactly `localhost` or `127.0.0.1` AND the database name contains `test`. `conftest.py`: if `TEST_DATABASE_URL` is set, an engine fixture runs the guard, then `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` and executes `seed_registry_pg.sql` before every test, then patches `db.engine`; if not set, current SQLite behaviour. `sqlite_only` tests are skipped in Postgres mode; Postgres-only tests are skipped without `TEST_DATABASE_URL`.

- [ ] **Step 1: Failing tests** in `tests/test_pg_guard.py` (pure string tests, no DB): accepted: `postgresql+psycopg://u:p@localhost:5432/registry_test`, `.../127.0.0.1/test`. Rejected (each asserts `RuntimeError`): host `db.prod.example.com`, host `localhost.evil.com`, `postgresql://u:p@evil.com@localhost/x` style tricks resolved by URL parsing (`user@evil/db_test`), no database name, db name `registry` (no "test"), non-localhost host with "test" db name, and a `sqlite:///...` URL.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write `pg_guard.py` using SQLAlchemy's `make_url` (never string splitting). Write `seed_registry_pg.sql`: same tables, rows and `UNIQUE (farm_id, name)` as `seed_registry.sh`, with the "hard" types: `planting_date DATE`, `lat`/`lon NUMERIC`, other floats `DOUBLE PRECISION`, ids `TEXT`. Add the fixture wiring.
- [ ] **Step 4:** `uv run pytest -v` (SQLite mode). Expected: guard tests PASS, Postgres-only tests skipped.

### Task 6: Run the suite on Postgres; add the Postgres-proof tests (D9, D10, D7)

**Files:** Modify `tests/test_plots.py`, `tests/test_farms.py` (add cases), possibly small fixes in `db.py`.

- [ ] **Step 1:** Owner starts Postgres (command from T7 README), creates database `registry_test`. Run `TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_test uv run pytest -v`. Expected: first run shows real failures; fix them in `db.py` only, until the same suite is green on both databases.
- [ ] **Step 2: Add tests** that run on both databases: `test_patch_plot_without_planting_date_returns_200` (PATCH only `name`; on Postgres this returns 500 if normalization is missing; verify by temporarily disabling the date conversion once, then restore); `test_delete_farm_with_plots_is_409_not_500`; `test_plot_with_unknown_crop_soil_emitter_farm_is_422` (current behaviour is 422, not 404/409); `test_duplicate_plot_name_is_409`; `test_plot_response_has_iso_date_and_float_lat_lon` (JSON types identical to SQLite).
- [ ] **Step 3:** Both runs green: `uv run pytest` and the `TEST_DATABASE_URL=...` run. Concurrency test: run on Postgres too if it passes; otherwise mark it `sqlite_only` with a reason.

### Task 7: README, Docker command, CLAUDE.md update

**Files:** Modify `README.md`, `../../CLAUDE.md`.

- [ ] **Step 1:** README: how `DATABASE_URL` / `.env` work (copy `.env.example`, env var wins); one `docker run` for Postgres (image `postgres:16`, port `5432` bound to `127.0.0.1`, env `POSTGRES_PASSWORD`, database `registry_test`); how to load `seed_registry_pg.sql` into a separate non-test database for k6 (`docker exec -i ... psql`); how to run tests on Postgres; the note that `seed_registry_pg.sql` is for tests/local only and production already exists.
- [ ] **Step 2:** Update the "CLAUDE.md decisions that change" list from the spec (DB, `DB_PATH` -> `db.engine`, 503 rule, tests). Show a diff, not the full file.
- [ ] **Step 3: Verify:** a reader can follow the README from a clean clone to both test runs. Check each command in it actually runs.

### Task 8: Performance on both databases (D11)

**Files:** Modify `perf/results.txt` (script `perf/registry_load.js` and its thresholds unchanged).

- [ ] **Step 1 (SQLite):** `bash seed_registry.sh /tmp/perf-registry.db` (temp copy, never the real file), start `DATABASE_URL=sqlite:////tmp/perf-registry.db uv run uvicorn main:app --host 127.0.0.1 --port 8000` without `--reload` (confirm the startup log says `sqlite`), then `k6 run --quiet perf/registry_load.js 2>&1 | tee /tmp/perf-sqlite.txt`. Read pass/fail from the ✓/✗ marks.
- [ ] **Step 2 (Postgres):** load `seed_registry_pg.sql` into a fresh non-test database in the container, start the server with `DATABASE_URL=postgresql+psycopg://...` (confirm the startup log says `postgresql`), run the same k6 command to `/tmp/perf-postgres.txt`.
- [ ] **Step 3:** Put both outputs in `perf/results.txt` under clear headings `## SQLite` and `## PostgreSQL`, with the date. If Postgres misses p95 <= 100 ms, record it and report it; do not change thresholds.
- [ ] **Step 4: Final check:** `uv run pytest` (SQLite) green, `TEST_DATABASE_URL` run green, `registry.db` is unchanged (`ls -l` / checksum before and after the whole plan) and no commit was made.
