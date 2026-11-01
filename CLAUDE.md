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