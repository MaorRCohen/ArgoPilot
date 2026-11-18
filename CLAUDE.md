# AgroPilot – notes for Claude Code

## Rules
- Keep answers short. Show diffs, not whole files. Don't commit or push.
- Implement ONLY what the task spec lists. No extras (no pagination, created_at, CORS, logging, auth, Factory/Repository layers).
- Explain each change in 2-3 lines so I can present it.
- If you suggest something non-obvious, say so: I log decisions in docs/judgment-log.md.
- Node/npm: always use the WSL nvm Node (export PATH=/home/maorc/.nvm/versions/node/v26.13.1/bin:$PATH); never the Windows npm under /mnt/c.
- Settings live only in `services/registry-service/config.py` (pydantic-settings). Never read or create a `.env` file.

## Current task: P1 Registry API
Spec: https://github.com/alonitac/OzVeruach26/blob/main/tasks/p1_registry_api.md
Service: services/registry-service (FastAPI, main.py at service root, run: `uv run uvicorn main:app --host 127.0.0.1 --port 8000`).

## Decisions (already made)
- DB: SQLAlchemy Core (raw `text()` SQL, driver adapter only) chosen by the required `DATABASE_URL`: SQLite (`sqlite:///...`) or PostgreSQL (`postgresql+psycopg://`). All API DB access lives in `db.py`. `setup_db.py` is the only other DB code (create and seed).
- PostgreSQL is created and seeded only by `setup_db.py` (`uv run python setup_db.py`, connects with `DATABASE_OWNER_URL` as `registry_owner`). Never run it against the real DB from an agent.
- Settings are read only in `config.py` at startup: a real env var first, then `.env` next to `config.py`. `DATABASE_URL` is required; optional `DATABASE_OWNER_URL` is never used by the API. Both are `SecretStr`; `db.py` reads `DATABASE_URL`, `setup_db.py` reads `DATABASE_OWNER_URL`, and the tests read `TEST_DATABASE_URL`. Settings load on first use (`get_settings()`), not at import, so conftest can read the real values before it overrides `DATABASE_URL`. Only `.env.example` is committed. Startup logs the scheme only (`sqlite` / `postgresql`), never the URL or password (logging added at the owner's request).
- Every SQLite connection runs `PRAGMA foreign_keys = ON`.
- Schema comes from `seed_registry.sh` (do not change it). Reset data: `bash seed_registry.sh`.
- `registry.db` is git-ignored.
- Few files: main.py, db.py, models.py, errors.py (+ tests), setup_db.py (P2 setup and seed command).
- Farm ids are server-generated with `str(uuid.uuid4())`; the client sends only `name`.
- Farm names are unique in code (`farm_name_taken`), not via a DB constraint, because the schema cannot change. PATCH renaming a farm to its own name is allowed.
- PATCH uses `model_dump(exclude_unset=True)`: `{}` -> 422 "no fields to update"; `name` null or "" -> 422.
- DELETE farm: 409 if it still has plots (count first); unknown id -> 404.
- Request models (`RequestModel`) use `extra="forbid"`: unknown fields -> 422.
- Plot `planting_date` must not be after the local date at the plot's lat/lon (`TimezoneFinder`, UTC fallback) -> 422.
- Plot name is unique per farm: checked in code, plus a `UNIQUE(farm_id, name)` safety net that maps to 409.
- Plot referenced ids (farm/crop/soil/emitter) that don't exist -> 422, not 404.
- SQLite is opened with `mode=rw` (missing registry.db raises, never creates an empty DB), `timeout=5` (lock wait) and `NullPool`. PostgreSQL uses the default pool with `pool_pre_ping=True` and `connect_timeout=5`.
- 503 UNAVAILABLE "Database unavailable" + `Retry-After: 30` for a temporary DB problem, decided in `db.is_temporarily_unavailable`: SQLite `sqlite_errorname` starting with SQLITE_CANTOPEN / SQLITE_BUSY / SQLITE_LOCKED; Postgres connection failure/disconnect (SQLSTATE class 08, 57P01/57P02/57P03), too many connections (53300), lock not available (55P03), deadlock (40P01), connect timeout; connection pool exhausted (SQLAlchemy TimeoutError). Anything else -> 500 "Internal server error" (a bug, not retried).
- `/health` checks the farms table (`check_farms_table` in `db.py`) through `get_db`: 200 on success; DB failure -> 503 (lock/missing file); missing table (schema not set up) -> 503 "Database schema is missing" + `Retry-After: 30`.
- Tests: `uv run pytest` (from services/registry-service), SQLite by default. `conftest.py` sets `DATABASE_URL` to a temp SQLite file before `db` is imported, so tests ignore `.env`. Each test gets a fresh DB copied from a template built by running a copy of `seed_registry.sh` in a temp dir; `db.engine` is patched, `get_db` is not overridden. Clock frozen at 2026-11-03 22:00 UTC (time-machine, tick=True). Skipped: locked-DB test (needs a real 5s wait).
- Postgres tests: set `TEST_DATABASE_URL` in `.env` (a separate `registry_test` database, see README); the same suite runs on it, SQLite-only tests are skipped. Before each test the `public` schema is dropped and `setup_db.run_setup` recreates the tables and seed rows. Guard (`tests/pg_guard.py`, run in `pytest_configure` before any DB is touched): `TEST_DATABASE_URL`'s database name must end with `_test` and differ from `DATABASE_URL`'s (exit 2 otherwise; no URL printed). The wipe also needs host `localhost`/`127.0.0.1`, no query string, and PGHOST/PGHOSTADDR/PGSERVICE/PGDATABASE are unset (they can redirect the connection). PostgreSQL tables are created only by `setup_db.py`.
- Threads: the SQLite engine uses `check_same_thread=False`. FastAPI can run the dependency and the endpoint on different threads of one request; a connection is still never shared between requests (decision 3). Regression test: `tests/test_concurrency.py` (240 requests, 20 threads, one long-lived `TestClient` via a `with` block).

## Performance (NFR-1.1)
- Script: `perf/registry_load.js` (k6, open model: constant-arrival-rate). Thresholds: p95 <= 100 ms, 0 failed, 0 dropped iterations per measured scenario.
- Run from services/registry-service:
  1. `bash seed_registry.sh /tmp/perf-registry.db` (temp copy: never reseed the real `registry.db`)
  2. Start the server without `--reload`: `DATABASE_URL=sqlite:////tmp/perf-registry.db uv run uvicorn main:app --host 127.0.0.1 --port 8000`
  3. `k6 run --quiet perf/registry_load.js 2>&1 | tee perf/results.txt`
- Postgres run: seed the `registry_perf` database with `setup_db.py` (README commands), then start the server with `DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_perf` and run the same k6 command.
- Result 2026-11-10 (p95 farms list / by id / plots list / plot by id, all passed, 0 dropped): SQLite 28.2 / 29.1 / 29.0 / 30.6 ms; PostgreSQL 35.9 / 36.8 / 36.6 / 37.4 ms; old code 32.2 / 32.9 / 33.1 / 35.6 ms. The machine drifts (WSL, VS Code): compare runs only back-to-back, close other work first.
- `results.txt` is committed as evidence for the PR. `tee` hides k6's exit code, so read pass/fail from the ✓/✗ marks in the summary.
## P2 weather-service (services/weather-service)
Spec: `~/course/OzVeruach26/tasks/p2.md`, section "The weather-service" (FR-2.3..FR-2.8, NFR-2.3). FastAPI on port 8001, `main.py` at the service root, run: `uv run uvicorn main:app --host 127.0.0.1 --port 8001`. Same rules as above: settings only in its `config.py` (never read or create `.env`), services never import each other's code, no extras.
- This service is the ONLY retry point in the chain (3 attempts, jittered backoff, 4 s budget). Callers must not retry it: planner-service calls it once, no retries, with a timeout a bit above 4 s (for example 5 s).
- Open-Meteo's field names, units and request live in `provider.py` only. Anything wrong in an answer is a provider failure: never zeros, never defaults (FR-2.8). `rain_mm = rain_sum + showers_sum` (liquid water only, no snow).
- Cache: memory only, one LRU dict per grid cell (`fetched_at` decides freshness, request order decides eviction). Fresh 3 h, max stale 24 h, single-flight per cell, 30 s cooldown after a failed cell. Reasons: service README and judgment log entries 91-102.
- Frontend (later): show the forecast age from `fetched_at`, and a stronger warning when it is older than 6 h.
- Tests: `uv run pytest` from `services/weather-service`. No internet: the provider is an `httpx.MockTransport`, time is frozen with time-machine. The dev dependency `httpx2` is only for Starlette's TestClient.
