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

- **Observer/notifications.** Notify the grower when a new forecast changes the plan (not needed now: everything is request/response).
- **Grower override of the daily recommendation.** The grower can change today's run time (for example, after a local rain the forecast missed). The override is stored and shown next to the calculated value, so the engine's numbers stay untouched and auditable. Needs: an overrides table, an endpoint in planner-service, and an edit control on the plot page.
- Add numeric constraints (ge/gt) to the Plot response model, matching PlotArea and the registry rule (docs/Swagger only — input is already validated by FR-1.3).
- Planner API: return morning depletion so the gauge can show before/after watering.
- **Daily irrigation mode (grower's choice).** Today the planner waits until 30% of the soil water is used, then refills it in one long run (for example in November: one 7 h run, then about a week with no water). Many drip growers prefer "daily replacement": every day, give back what the crop used, so runs are short and the soil stays near full. Both follow FAO-56. Needs: a per-plot setting and a second scheduling rule in the planner engine; the water balance stays the same.