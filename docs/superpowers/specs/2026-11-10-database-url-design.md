# registry-service: choose the database with DATABASE_URL (SQLite or PostgreSQL)

Status: draft for review. Not committed (CLAUDE.md: don't commit). Service: `services/registry-service`, branch `coding-agents`.

## Intent

Locally and in tests the service keeps using the SQLite file `registry.db`. In production it must work with an **existing** PostgreSQL database. The switch is one setting, `DATABASE_URL`, read from the environment or a `.env` file. The API must not change: same status codes, same `application/problem+json` bodies and `code` values, same `Retry-After` on 503 (course requirement 1).

The owner plans to move to MySQL later. That should need only a new `DATABASE_URL` and driver. No MySQL code is written now.

The grading is a live demo: the **same test suite** must pass on SQLite and then on PostgreSQL. That is the proof for requirement 1.

## Goals

- `DATABASE_URL` selects SQLite or PostgreSQL. All DB-specific code stays in `db.py`.
- Identical API behaviour on both databases, proven by the same tests.
- NFR-1.1 (p95 <= 100 ms) measured on both databases.
- Tests can never touch the real `registry.db` or a real Postgres database.

## Non-goals and anti-goals

- No MySQL code, no ORM, no query builder, no models, no migrations, no Alembic.
- No schema change to SQLite (`seed_registry.sh` stays as is). No schema creation in production.
- No new endpoints, no pagination, CORS, auth (CLAUDE.md "no extras"). The `.claude/rules` for new endpoints do not apply (none are added).
- Anti-goal: any change in a response body, status code or header on SQLite. Anti-goal: a test run that can wipe a real database.
- Tests never start or stop Docker.

## Decisions (made by the owner)

1. **SQLAlchemy Core, used only as a driver adapter.** Raw SQL via `text()` with named params. Engine built from `DATABASE_URL`. Everything stays in `db.py`. Reason: SQLAlchemy wraps both drivers' errors in the same `IntegrityError` / `OperationalError`, so errors are mapped once; and a later MySQL switch is a URL + driver change. Use portable SQL; avoid Postgres-only forms where a portable one exists.
2. **Connections.** SQLite: `NullPool` (a fresh connection per request, as today), `PRAGMA foreign_keys = ON` in a connect event, `mode=rw` (a missing file raises, never creates an empty DB), `timeout=5`, `check_same_thread=False`. PostgreSQL: default pool with `pool_pre_ping=True`.
3. **503 vs 500.** A temporary DB problem returns 503 UNAVAILABLE "Database unavailable" + `Retry-After: 30`. A bug returns 500 "Internal server error".
   - 503: cannot connect, timeout, disconnected mid-request, too many connections, row lock not available, deadlock; on SQLite the existing CANTOPEN / BUSY / LOCKED rule.
   - 500: everything else (missing table, bad SQL).
   - Each case is tested with a simulated error; no real Postgres needed.
4. **Configuration.** `python-dotenv` loads `.env` in `db.py` with `override=False` (a real environment variable wins). If `DATABASE_URL` is unset the default is `sqlite:///registry.db` (so the documented run commands and the k6 script keep working). At startup, log which database is used: the scheme only (`sqlite` / `postgresql`), never the password or full URL. `.env` is git-ignored; only `.env.example` is committed.
5. **Postgres tests.** The same test suite runs on Postgres only when `TEST_DATABASE_URL` is set. Skipped by default, so `uv run pytest` stays SQLite-only and fast. Postgres runs in a local Docker container the owner starts (one `docker run` command in the README). Production DB already exists, so the Postgres schema file is for tests and local use only, and the README says so.
6. **Clean state per Postgres test.** One file `seed_registry_pg.sql` (schema + seed rows, translated from `seed_registry.sh`). Before each test: `DROP SCHEMA public CASCADE`, recreate, run the file.
7. **Safety guard (must have).** Before any DROP the test setup refuses to run unless the `TEST_DATABASE_URL` host is `localhost` or `127.0.0.1` AND the database name contains `test`. The guard has its own test.
8. **How tests choose the DB.** `db.py` builds a module-level `engine` at import (reads `.env`/environment, logs the scheme). `conftest.py` sets `DATABASE_URL` to a temp SQLite file **before** `db.py` is imported, and tests patch `db.engine` with their own engine (the current `db.DB_PATH` patch pattern). A test proves the tests use the temp DB even when `.env` points elsewhere.
9. **Types.** Postgres returns `date` / `Decimal` where SQLite returns text / float. `db.py` normalizes every row it returns: `date` -> `"YYYY-MM-DD"`, `Decimal` -> `float`. `main.py` does not change for this. Reason: `update_plot` merges the stored row into the changes and `check_planting_date` calls `date.fromisoformat()`, which would raise `TypeError` (500) on a `date`. The Postgres test schema uses the "hard" types (`DATE` for `planting_date`, `NUMERIC` for `lat`/`lon`, `DOUBLE PRECISION` elsewhere) so the suite proves it. Includes a PATCH-without-`planting_date` test that returns 500 without the normalization.
10. **Constraint errors.** `db.py` raises its own `UniqueViolation` and `ForeignKeyViolation`, translated from SQLite messages or Postgres SQLSTATE 23505 / 23503. `main.py` catches only these. Today `write_plot` matches the SQLite message text; that goes away. Check the foreign-key cases too: delete a farm that has plots, and unknown catalogue ids, must give the same 409 / 422 as today on both databases, with tests on both. A future MySQL (SQLSTATE 23000) maps into the same two exceptions in `db.py`.
11. **Performance.** Same k6 script, same thresholds, unchanged. Run once on SQLite and once on the Docker Postgres. Record both p95 numbers in `perf/results.txt`, clearly labelled. If Postgres misses 100 ms, report it; do not tune the thresholds.

## Changes to files

- `db.py`: engine, connect event, `text()` queries with named params, row normalization, error translation. The `get_connection()` / `DB_PATH` / `sqlite3` code is replaced.
- `errors.py`: handle the SQLAlchemy `OperationalError` (and disconnects) with the 503/500 rule, instead of `sqlite3.OperationalError` + `sqlite_errorname`. Same response bodies.
- `main.py`: type hints (`Connection`) and the two catches (decision 10). Nothing else.
- `tests/conftest.py`, new Postgres-only tests and guard test, `seed_registry_pg.sql`, `.env.example`, README (run, Docker command, `DATABASE_URL`, results), `pyproject.toml` (SQLAlchemy, a Postgres driver, python-dotenv), `.gitignore` check for `.env`.
- `docs/judgment-log.md`: entries for these decisions.

## CLAUDE.md decisions that change (update CLAUDE.md after the build)

- "DB: SQLite file via stdlib `sqlite3`": now SQLAlchemy Core + `DATABASE_URL` (SQLite is the default).
- "`db.DB_PATH` is patched": now `db.engine` is patched.
- "503 ... `sqlite_errorname` starting with ...": now the engine-neutral rule in decision 3.
- "`get_connection` uses `check_same_thread=False`": kept, now an SQLite engine option.
- "DB opened with `mode=rw`, `timeout=5`" and "foreign_keys ON": kept, for SQLite.
- "Tests: fresh DB per test": kept for SQLite; Postgres uses decision 6.
- Startup logging is added at the owner's request (CLAUDE.md otherwise says no logging).

## Constraints

- Existing tests must keep passing on SQLite, unchanged in meaning.
- The thread regression test (240 requests, 20 threads) must still pass.
- The `/health` rule is unchanged: 200 on success, 503 on lock / missing file, 500 on a missing table.

## Left to the builder

- Exact SQLAlchemy URL form for SQLite (`mode=rw` with `uri=true`) and the choice of Postgres driver (psycopg 3 is assumed).
- How the simulated-error tests build each exception.
- Helper structure inside `db.py`.

## Assumptions from the conversation

- Production Postgres has the same tables and column names as `seed_registry.sh`. Column types are unknown (the spec does not say), which is why decision 9 normalizes values. Farm names stay unique in code only, with no DB backstop (existing CLAUDE.md decision); plot names keep the `UNIQUE(farm_id, name)` safety net.
- The demo Postgres is a local Docker container the owner starts. It is loaded from `seed_registry_pg.sql`. The test guard (decision 7) applies to tests only and can never target production.

## Builder's calls (mine, please check)

- Default URL when `DATABASE_URL` is unset: SQLite file `registry.db` next to `db.py` (same path as today, not the working directory). A missing file stays an error: 503 from `/health`, as today.
- Row normalization applies to every returned row, including catalogues. I also convert `UUID` -> `str`, in case production ids are uuid columns.
- Postgres 503 set: connection failures and disconnects (SQLSTATE class 08, 57P03), too many connections (53300), lock not available (55P03), deadlock (40P01), and connect timeout. Set `connect_timeout=5` to match SQLite's `timeout=5`. No statement timeout.
- Driver: `psycopg[binary]` (psycopg 3), Python 3.12.
- Perf on Postgres: README documents loading `seed_registry_pg.sql` into a non-test database in the container (k6 uses fixed seed ids); the tests' guard is not involved.
