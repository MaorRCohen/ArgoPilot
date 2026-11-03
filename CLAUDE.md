# AgroPilot – notes for Claude Code

## Rules
- Keep answers short. Show diffs, not whole files. Don't commit or push.
- Implement ONLY what the task spec lists. No extras (no pagination, created_at, CORS, logging, auth, Factory/Repository layers).
- Explain each change in 2-3 lines so I can present it.
- If you suggest something non-obvious, say so: I log decisions in docs/judgment-log.md.

## Current task: P1 Registry API
Spec: https://github.com/alonitac/OzVeruach26/blob/main/tasks/p1_registry_api.md
Service: services/registry-service (FastAPI, main.py at service root, run: `uv run uvicorn main:app --host 127.0.0.1 --port 8000`).

## Decisions (already made)
- DB: SQLite file `registry.db` via stdlib `sqlite3`. All DB access lives in `db.py` only.
- Every connection runs `PRAGMA foreign_keys = ON`.
- Schema comes from `seed_registry.sh` (do not change it). Reset data: `bash seed_registry.sh`.
- `registry.db` is git-ignored.
- Few files: main.py, db.py, models.py, errors.py (+ tests).
- Farm ids are server-generated with `str(uuid.uuid4())`; the client sends only `name`.
- Farm names are unique in code (`farm_name_taken`), not via a DB constraint, because the schema cannot change. PATCH renaming a farm to its own name is allowed.
- PATCH uses `model_dump(exclude_unset=True)`: `{}` -> 422 "no fields to update"; `name` null or "" -> 422.
- DELETE farm: 409 if it still has plots (count first); unknown id -> 404.
- Request models (`RequestModel`) use `extra="forbid"`: unknown fields -> 422.
- Plot `planting_date` must not be after the local date at the plot's lat/lon (`TimezoneFinder`, UTC fallback) -> 422.
- Plot name is unique per farm: checked in code, plus a `UNIQUE(farm_id, name)` safety net that maps to 409.
- Plot referenced ids (farm/crop/soil/emitter) that don't exist -> 422, not 404.
- DB opened with `mode=rw` (missing registry.db raises, never creates an empty DB) and `timeout=5` (lock wait).
- 503 UNAVAILABLE "Database unavailable" + `Retry-After: 30` for `sqlite3.OperationalError` with `sqlite_errorname` starting with SQLITE_CANTOPEN / SQLITE_BUSY / SQLITE_LOCKED. Any other OperationalError -> 500 "Internal server error" (a bug, not retried).
- `/health` runs `SELECT 1 FROM farms LIMIT 1` through `get_db`: 200 on success; DB failure -> 503 (lock/missing file), missing table -> 500.
- Tests: `uv run pytest` (from services/registry-service). Each test gets a fresh DB copied from a template built by running a copy of `seed_registry.sh` in a temp dir; `db.DB_PATH` is patched, `get_db` is not overridden. Clock frozen at 2026-11-03 22:00 UTC (time-machine, tick=True). Skipped: locked-DB test (needs a real 5s wait).