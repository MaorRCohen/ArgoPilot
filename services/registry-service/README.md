# registry-service

The registry service is AgroPilot's source of farm and plot data. A farm has many plots, and each plot points to a crop, a soil and an emitter. Crops, soils and emitters are read-only catalogues, stored with the farms and plots in one database: a local SQLite file or PostgreSQL, chosen by the required `DATABASE_URL`.

## Prerequisites

Python 3.12 (from [`../../.python-version`](../../.python-version)), [uv](https://docs.astral.sh/uv/), the `sqlite3` CLI (used by `seed_registry.sh`), Docker for the optional PostgreSQL runs (the driver, `psycopg`, is installed by `uv sync`), and [k6](https://k6.io/) for the load test only.

## Run locally (from `services/registry-service`)

```bash
uv sync
bash seed_registry.sh
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

## Configuration (`DATABASE_URL`)

The settings are read in `config.py` (pydantic-settings), from the environment or from a `.env` file next to `config.py`. Copy the example to start: `cp .env.example .env`. A real environment variable beats `.env`. `DATABASE_URL` is required, with no default. If it is missing, or its scheme is not `sqlite` or `postgresql` (a `+driver` suffix is allowed), the service refuses to start and names the variable; it never prints the value. A relative SQLite path such as `sqlite:///registry.db` is taken from the `services/registry-service` folder, wherever you start the service. `DATABASE_OWNER_URL` is optional: the setup/seed command and Postgres tests use it, and the API never does. Examples:

```
DATABASE_URL=sqlite:///registry.db
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
```

At startup the service logs `Using database: <scheme>` (`sqlite` or `postgresql`) and never the URL or password. `.env` is for local use only; do not commit it.

## PostgreSQL for tests and local runs

Production uses an existing PostgreSQL database. For tests and local runs, start a throwaway one in Docker (bound to localhost only; the tests never start or stop it):

```bash
docker run -d --name registry-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=registry_test -p 127.0.0.1:5432:5432 postgres:16
```

Run the same test suite on it (without `TEST_DATABASE_URL`, `uv run pytest` runs on SQLite): `TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_test uv run pytest`. The tests drop and recreate the `public` schema before every test, so they refuse to run unless the host is `localhost` or `127.0.0.1` and the database name contains `test`.

`seed_registry_pg.sql` (schema plus seed rows) is for tests and local use only. The production database already exists and is never created or changed by this service.

To run the k6 load test (see Performance) against PostgreSQL, load the seed into a separate database whose name does not contain `test`:

```bash
docker exec registry-postgres psql -U postgres -c "CREATE DATABASE registry_perf"
docker exec -i registry-postgres psql -U postgres -d registry_perf -v ON_ERROR_STOP=1 < seed_registry_pg.sql
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_perf uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

## Endpoints

| Resource | Methods and paths |
|---|---|
| Farms | `GET, POST /v1/farms`; `GET, PATCH, DELETE /v1/farms/{farm_id}` |
| Plots | `GET, POST /v1/plots` (filter with `GET /v1/plots?farm_id=`); `GET, PATCH, DELETE /v1/plots/{plot_id}` |
| Crops, soils, emitters | `GET /v1/crops`, `/v1/soils`, `/v1/emitters`; `GET` each `/{id}` |
| Health | `GET /health` |

## Errors

All errors are `application/problem+json` (RFC 9457) with a `code` of VALIDATION, NOT_FOUND, CONFLICT or UNAVAILABLE; 503 responses include `Retry-After`.

## Tests

From `services/registry-service`: `uv run pytest` (SQLite: each test runs against a fresh copy of the database). Tests set their own `DATABASE_URL` (a temp SQLite copy) and ignore `.env`. With `TEST_DATABASE_URL` set they run on PostgreSQL instead (see above).

## Performance

Measured locally on 2026-11-10 at 10 rps per endpoint (40 rps total) with k6 `constant-arrival-rate`, farms list / farm by id / plots list / plot by id (NFR-1.1 target: p95 <= 100 ms, 0 dropped): SQLite 28.2 / 29.1 / 29.0 / 30.6 ms; PostgreSQL (Docker) 35.9 / 36.8 / 36.6 / 37.4 ms; the code before the `DATABASE_URL` change, on the same host, 32.2 / 32.9 / 33.1 / 35.6 ms. All thresholds passed. Host noise matters: on a busy machine the same code measured 2x slower (see `perf/results.txt`). The script uses fixed seed ids, so rerun it against a freshly seeded database, with the server running without `--reload`: `k6 run --quiet perf/registry_load.js`. For SQLite use a temp copy: `bash seed_registry.sh /tmp/perf-registry.db`, then start the server with `DATABASE_URL=sqlite:////tmp/perf-registry.db`. For PostgreSQL use the `registry_perf` database above.

Design decisions and their reasons: [../../docs/judgment-log.md](../../docs/judgment-log.md)
