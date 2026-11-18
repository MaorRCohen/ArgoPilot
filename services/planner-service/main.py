import asyncio
import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, FastAPI, Query, Request

import engine
from clients import PlotNotFound, RegistryClient, UpstreamError, WeatherClient
from config import Settings, get_settings
from errors import ApiError, register_error_handlers
from models import PlanResponse
from profiles import load_crop_profiles

router = APIRouter()


def get_state(request: Request):
    return request.app.state


@router.get("/health")
async def health() -> dict[str, str]:
    # Calls nothing: it says this service is up, not that its upstreams are.
    return {"status": "ok"}


def upstream_unavailable(exc: UpstreamError, settings: Settings) -> ApiError:
    return ApiError(
        503,
        "UPSTREAM_UNAVAILABLE",
        f"{exc.service} is unavailable: {exc.reason}",
        {"Retry-After": str(exc.retry_after_s or settings.retry_after_s)},
    )


@router.get("/v1/plots/{plot_id}/plan", response_model=PlanResponse)
async def get_plan(
    plot_id: str,
    soil_moisture: Annotated[int, Query(ge=0, le=10)],
    state: Annotated[object, Depends(get_state)],
    days: Annotated[int, Query(ge=1, le=7)] = 7,
) -> PlanResponse:
    settings: Settings = state.settings
    try:
        plot = await state.registry.get_plot(plot_id)
        crop = state.profiles.get(plot.crop_id)
        if crop is None:
            raise ApiError(409, "CONFLICT", f"No crop profile for crop '{plot.crop_id}': add it to crop_profiles.json")
        # In parallel; all three finish before we look at the results, and the registry error comes first.
        soil, emitter, forecast = await asyncio.gather(
            state.registry.get_soil(plot.soil_id),
            state.registry.get_emitter(plot.emitter_id),
            state.weather.get_forecast(plot.lat, plot.lon, days),
            return_exceptions=True,
        )
        for result in (soil, emitter, forecast):
            if isinstance(result, BaseException):
                raise result
    except PlotNotFound:
        raise ApiError(404, "NOT_FOUND", f"Plot '{plot_id}' not found") from None
    except UpstreamError as exc:
        raise upstream_unavailable(exc, settings) from None

    plan = engine.build_plan(
        engine.PlotInput(plot.area_m2, plot.row_spacing_m, plot.emitter_spacing_m, plot.planting_date),
        crop,
        soil.available_water_mm_per_m,
        emitter.flow_lph,
        [engine.WeatherDay(**d.model_dump(), stale=forecast.stale) for d in forecast.days],
        soil_moisture,
        settings.uniformity_factor,
        settings.max_run_minutes_per_day,
    )
    return PlanResponse(
        plot_id=plot.id,
        plot_name=plot.name,
        crop=plot.crop_id,
        soil_moisture_input=soil_moisture,
        generated_at=dt.datetime.now(dt.UTC),
        forecast_fetched_at=forecast.fetched_at,
        **asdict(plan),
    )


def create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Read at startup, not at import: a missing variable or a bad crop file stops the service here,
        # with a clear message, and not on the first request.
        s = settings or get_settings()
        app.state.settings = s
        app.state.profiles = load_crop_profiles(s.crop_profiles_path)
        async with httpx.AsyncClient(transport=transport) as http:
            app.state.registry = RegistryClient("registry-service", str(s.registry_url), s.registry_timeout_s, http)
            app.state.weather = WeatherClient("weather-service", str(s.weather_url), s.weather_timeout_s, http)
            yield

    app = FastAPI(title="AgroPilot planner-service", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
