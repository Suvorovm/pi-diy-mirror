from __future__ import annotations

import logging

from smart_mirror.core.config import WeatherConfig
from smart_mirror.core.settings import SettingsManager
from smart_mirror.data.location import LocationData
from smart_mirror.display.display_adapter import DisplayAdapter
from smart_mirror.routines.routine import Routine
from smart_mirror.weather.fetcher import WeatherFetcher

logger = logging.getLogger(__name__)


class WeatherRoutine(Routine):
    def __init__(
        self,
        interval_seconds: int,
        fetcher: WeatherFetcher,
        settings: SettingsManager,
        display: DisplayAdapter,
        default_location: WeatherConfig,
    ) -> None:
        super().__init__(interval_seconds)
        self._fetcher = fetcher
        self._settings = settings
        self._display = display
        self._default_location = default_location

    def execute(self) -> None:
        location = self._resolve_location()
        try:
            data = self._fetcher.fetch(location)
            self._display.update_weather(data)
        except Exception:
            logger.exception("Failed to fetch weather for %s", location)

    def _resolve_location(self) -> LocationData:
        """User-set location takes priority; fall back to config defaults."""
        saved = self._settings.get_location()
        if saved is not None:
            return saved
        return LocationData(
            latitude=self._default_location.latitude,
            longitude=self._default_location.longitude,
        )
