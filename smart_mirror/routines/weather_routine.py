from __future__ import annotations

import logging

from smart_mirror.display.base import DisplayAdapter
from smart_mirror.routines.base import Routine
from smart_mirror.weather.fetcher import WeatherFetcher

logger = logging.getLogger(__name__)


class WeatherRoutine(Routine):
    def __init__(
        self,
        interval_seconds: int,
        fetcher: WeatherFetcher,
        display: DisplayAdapter,
    ) -> None:
        super().__init__(interval_seconds)
        self._fetcher = fetcher
        self._display = display

    def execute(self) -> None:
        try:
            data = self._fetcher.fetch()
            self._display.update_weather(data)
        except Exception:
            logger.exception("Failed to fetch weather")
