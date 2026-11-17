# AgroPilot

AgroPilot helps a grower manage agricultural crops with modern AI. 


## Where to start

Services live under `services/`. The service in the repository today is `registry-service`, a FastAPI application. 

```bash
cd services/registry-service
uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/health. A running service returns `{"status": "ok"}`.

## Backlog

Feature ideas outside the task spec. Per the instructor's rule, every such idea goes here, not into the code.

- **Grower override of the daily recommendation.** The grower can change today's run time (for example, after a local rain the forecast missed). The override is stored and shown next to the calculated value, so the engine's numbers stay untouched and auditable. Needs: an overrides table, an endpoint in planner-service, and an edit control on the plot page.
