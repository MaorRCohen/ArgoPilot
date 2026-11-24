from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, FastAPI, Query, Request

from config import Settings, get_settings
from errors import ApiError, register_error_handlers
from forecast import ForecastService, Unavailable
from models import ForecastResponse
from provider import OpenMeteoClient

router = APIRouter()


def get_forecasts(request: Request) -> ForecastService:
    return request.app.state.forecasts


@router.get("/health")
async def health() -> dict[str, str]:
    # Never calls the provider: it says the service is up, not that Open-Meteo is.
    return {"status": "ok"}


@router.get("/v1/forecast", response_model=ForecastResponse)
async def get_forecast(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    days: Annotated[int, Query(ge=1, le=7)],
    forecasts: ForecastService = Depends(get_forecasts),
) -> ForecastResponse:
    try:
        served = await forecasts.get(lat, lon, days)
    except Unavailable as exc:
        raise ApiError(
            503,
            "UNAVAILABLE",
            "No forecast available: the weather provider is not answering",
            {"Retry-After": str(exc.retry_after_s)},
        ) from None
    return ForecastResponse(
        lat=lat,
        lon=lon,
        source="open-meteo",
        fetched_at=served.fetched_at,
        stale=served.stale,
        days=served.days,
    )


def create_app(
    settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Read at startup, not at import: a missing variable stops the service here, with a clear
        # message, and not on the first request.
        service_settings = settings or get_settings()
        async with httpx.AsyncClient(transport=transport) as http:
            app.state.forecasts = ForecastService(service_settings, OpenMeteoClient(service_settings, http))
            yield

    app = FastAPI(title="AgroPilot weather-service", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
