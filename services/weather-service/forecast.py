"""Serves forecasts from memory, and fetches from the provider when a cell has no fresh one (FR-2.5 to FR-2.7)."""

import asyncio
import logging
import math
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from config import Settings
from grid import Cell, cell_center, cell_key
from models import ForecastDay
from provider import Forecast, OpenMeteoClient, ProviderError


logger = logging.getLogger(__name__)


class Unavailable(Exception):
    """The provider failed and no earlier forecast can answer. The caller may try again after `retry_after_s`."""

    def __init__(self, retry_after_s: int) -> None:
        super().__init__(f"no forecast available, retry after {retry_after_s} s")
        self.retry_after_s = retry_after_s


@dataclass(frozen=True)
class Served:
    days: list[ForecastDay]
    fetched_at: datetime
    stale: bool


class ForecastService:
    def __init__(self, settings: Settings, provider: OpenMeteoClient) -> None:
        self._settings = settings
        self._provider = provider
        # One forecast per grid cell, least recently requested first. Two clocks: fetched_at decides
        # if a forecast is fresh, this order decides which cell goes when the cache is full.
        self._cache: OrderedDict[Cell, Forecast] = OrderedDict()
        # Single-flight: one provider call per cell at a time. Everybody who needs the cell awaits it.
        self._fetching: dict[Cell, asyncio.Task[Forecast]] = {}
        # A cell that failed (all retries) is left alone until this moment.
        self._failed_until: dict[Cell, datetime] = {}

    async def get(self, lat: float, lon: float, days: int) -> Served:
        cell = cell_key(lat, lon)
        now = datetime.now(UTC)
        cached = self._lookup(cell, now)
        if cached is not None and _age_s(cached, now) < self._settings.fresh_for_s:
            served = _serve(cached, days, now, stale=False)
            if served is not None:
                return served
        if self._cooling_down(cell, now):  # it failed a moment ago: do not call the provider again yet
            return self._stale_or_unavailable(cell, days)
        try:
            fetched = await self._fetch_shared(cell)
        except ProviderError:
            return self._stale_or_unavailable(cell, days)
        now = datetime.now(UTC)
        served = _serve(fetched, days, now, stale=False)
        if served is None:  # the provider answered, but not with the days that were asked for
            raise Unavailable(self._retry_after_s(cell, now))
        return served

    async def _fetch_shared(self, cell: Cell) -> Forecast:
        """Everybody who needs this cell at the same time waits for one provider call and gets its outcome."""
        task = self._fetching.get(cell)
        if task is None:
            task = asyncio.create_task(self._fetch(cell))
            self._fetching[cell] = task
            task.add_done_callback(lambda finished: self._fetch_finished(cell, finished))
        # shield: a caller that gives up (is cancelled) must not cancel the call the others wait for.
        return await asyncio.shield(task)

    def _fetch_finished(self, cell: Cell, task: asyncio.Task[Forecast]) -> None:
        if self._fetching.get(cell) is task:
            del self._fetching[cell]
        if not task.cancelled():
            task.exception()  # every caller gets the outcome from its await; this only marks it as read

    async def _fetch(self, cell: Cell) -> Forecast:
        lat, lon = cell_center(cell)
        try:
            forecast = await self._provider.fetch(lat, lon)
        except ProviderError as exc:
            self._start_cooldown(cell, exc.retry_after_s)
            raise
        self._store(cell, forecast)
        return forecast

    def _cooling_down(self, cell: Cell, now: datetime) -> bool:
        until = self._failed_until.get(cell)
        return until is not None and now < until

    def _start_cooldown(self, cell: Cell, provider_retry_after_s: float | None) -> None:
        """Our cooldown, or what the provider asked for if that is longer, but never longer than max stale."""
        now = datetime.now(UTC)
        self._forget_finished_cooldowns(now)
        seconds = max(self._settings.failure_cooldown_s, provider_retry_after_s or 0)
        self._failed_until[cell] = now + timedelta(seconds=min(seconds, self._settings.max_stale_s))

    def _forget_finished_cooldowns(self, now: datetime) -> None:
        self._failed_until = {cell: until for cell, until in self._failed_until.items() if until > now}

    def _lookup(self, cell: Cell, now: datetime) -> Forecast | None:
        """The cell's forecast, or None. Every request moves its cell to the end: most recently requested."""
        cached = self._cache.get(cell)
        if cached is None:
            return None
        if _age_s(cached, now) >= self._settings.max_stale_s:
            del self._cache[cell]  # too old to be served, even as stale
            return None
        self._cache.move_to_end(cell)
        return cached

    def _store(self, cell: Cell, forecast: Forecast) -> None:
        now = datetime.now(UTC)
        self._forget_finished_cooldowns(now)
        # Cells older than max stale can never be served again: delete them while we are here.
        cutoff = now - timedelta(seconds=self._settings.max_stale_s)
        for expired in [key for key, cached in self._cache.items() if cached.fetched_at <= cutoff]:
            del self._cache[expired]
        self._cache[cell] = forecast
        self._cache.move_to_end(cell)
        while len(self._cache) > self._settings.cache_max_cells:
            self._cache.popitem(last=False)  # the least recently requested

    def _stale_or_unavailable(self, cell: Cell, days: int) -> Served:
        now = datetime.now(UTC)
        cached = self._lookup(cell, now)
        if cached is not None:
            served = _serve(cached, days, now, stale=True)
            if served is not None:
                logger.warning("served stale cell=%s age=%d s", cell, _age_s(cached, now))
                return served
        logger.error("no forecast available, answering 503 cell=%s", cell)
        raise Unavailable(self._retry_after_s(cell, now))

    def _retry_after_s(self, cell: Cell, now: datetime) -> int:
        """What is left of the cell's cooldown, or a whole cooldown if it has none."""
        until = self._failed_until.get(cell)
        if until is not None and now < until:
            return max(1, math.ceil((until - now).total_seconds()))
        return max(1, math.ceil(self._settings.failure_cooldown_s))


def _age_s(forecast: Forecast, now: datetime) -> float:
    return (now - forecast.fetched_at).total_seconds()


def _serve(forecast: Forecast, days: int, now: datetime, *, stale: bool) -> Served | None:
    """The `days` days from today at the point, or None if the forecast does not reach that far."""
    today = (now + timedelta(seconds=forecast.utc_offset_s)).date()
    first = (today - forecast.days[0].date).days
    if first < 0 or first + days > len(forecast.days):
        return None
    return Served(list(forecast.days[first : first + days]), forecast.fetched_at, stale)
