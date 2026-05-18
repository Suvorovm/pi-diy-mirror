from __future__ import annotations

from abc import ABC, abstractmethod

from smart_mirror.data.alarm import AlarmData
from smart_mirror.data.location import LocationData
from smart_mirror.data.weather import WeatherData


class DisplayAdapter(ABC):
    @abstractmethod
    def update_time(self, time_str: str) -> None: ...

    @abstractmethod
    def update_weather(self, data: WeatherData) -> None: ...

    @abstractmethod
    def update_phrase(self, phrase: str) -> None: ...

    @abstractmethod
    def update_alarm(self, alarm: AlarmData | None) -> None: ...

    @abstractmethod
    def update_location(self, location: LocationData | None) -> None: ...

    @abstractmethod
    def show_alarm_triggered(self) -> None: ...

    @abstractmethod
    def dismiss_alarm_triggered(self) -> None:
        """Убрать баннер будильника (вызывается после нажатия кнопки)."""
        ...

    @abstractmethod
    def render(self) -> None: ...
