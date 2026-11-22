# registry-service

The registry service is AgroPilot's source of farm and plot data. A farm has many plots, and each plot points to a crop, a soil and an emitter. Crops, soils and emitters are read-only catalogues, stored with the farms and plots in a local SQLite file, `registry.db`.

## Prerequisites

Python 3.12 (from [`../../.python-version`](../../.python-version)), [uv](https://docs.astral.sh/uv/), the `sqlite3` CLI (used by `seed_registry.sh`), and [k6](https://k6.io/) for the load test only.

## Run locally (from `services/registry-service`)

```bash
uv sync
bash seed_registry.sh
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

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

From `services/registry-service`: `uv run pytest`. Each test runs against a fresh copy of the database.

## Performance

Measured locally on 2026-11-03 at 10 rps per endpoint (40 rps total) with k6 `constant-arrival-rate`: p95 is 25.0 ms for farms list, 25.1 ms for farm by id, 27.3 ms for plots list and 25.9 ms for plot by id (NFR-1.1 target: p95 <= 100 ms). Rerun after a fresh `bash seed_registry.sh`, with the server running without `--reload` (the script uses fixed seed ids): `k6 run --quiet perf/registry_load.js`

Design decisions and their reasons: [../../docs/judgment-log.md](../../docs/judgment-log.md)
