---
name: registry-api
description: Conventions for every endpoint in services/registry-service (FastAPI registry API: farms, plots, crops, soils, emitters). Use whenever you add, change, test or review a route, an error response, a PATCH, or a list endpoint there, even for a "small" tweak.
---

# registry-api conventions

Work from services/registry-service. Each rule has a **Why** so you can judge edge cases instead of guessing.

## 1. All routes live under `/v1`; lists are JSON arrays, empty is `200 []`
Mount every new route under `/v1`. Return lists as a bare array, never `{"items": [...]}`, and never 404 for an empty result. **Why:** clients pin a version, and an unversioned route can never be changed without breaking them. An empty collection is a valid answer, and a bare array is what the spec's clients parse; 404 is only for an unknown id.

## 2. Return only the fields the spec lists
Response models contain exactly the spec's fields. No `created_at`, no extra ids, no convenience fields. **Why:** every extra field becomes a contract clients depend on, and the project owner decides the contract.

## 3. PATCH changes only the fields sent
Use `model_dump(exclude_unset=True)`; leave other columns untouched. **Why:** otherwise a client sending `{"name": "x"}` silently resets every field it omitted.

## 4. Every error is `application/problem+json` (RFC 9457) with a stable `code`
| Status | `code` | When |
|---|---|---|
| 422 | `VALIDATION` | bad body, unknown field, bad reference id |
| 404 | `NOT_FOUND` | unknown resource id |
| 409 | `CONFLICT` | duplicate name, delete blocked by children |
| 503 | `UNAVAILABLE` | temporary DB problem; **must** send `Retry-After` |

Raise `ApiError` / use `problem()` from `errors.py`. Never return FastAPI's default `{"detail": [...]}` body, and check new failure paths (405, bad JSON, etc.) still go through the handlers. **Why:** clients branch on `code`, not on message text, so codes must never change; the default body has a different shape and breaks them.

Example (409):
```
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{"type": "about:blank", "title": "Conflict", "status": 409,
 "detail": "Farm name already exists", "code": "CONFLICT"}
```
Example (503) adds the header `Retry-After: 30`. **Why:** without it clients retry immediately and hammer a struggling DB.

## 5. Tests: success and every failure the endpoint can return
For each endpoint, one test for the success case and one per reachable error (422, 404, 409, 503 as applicable). Assert status, `Content-Type: application/problem+json`, and `code`. **Why:** untested error paths are where the default FastAPI body sneaks back in.

## 6. Verify before saying "done"
Run `uv run pytest`. If `uv` is not on PATH, use `.venv/bin/python -m pytest`. Report the actual result. **Why:** "done" without a green run is a guess.

## 7. If the spec is silent, ask
Spec: https://github.com/alonitac/OzVeruach26/blob/main/tasks/p1_registry_api.md. Do not invent status codes, fields or behavior; ask, and note the answer as a decision. **Why:** invented behavior is invisible until a client depends on it.

## 8. Never touch `registry.db`
Do not edit, delete, reseed or open it for writes; tests use temp copies. **Why:** it is the owner's real data and git-ignored, so it cannot be restored.
