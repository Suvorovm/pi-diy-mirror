from __future__ import annotations

from dataclasses import dataclass, field

from smart_mirror.data.alarm import AlarmData
from smart_mirror.data.location import LocationData
from smart_mirror.data.weather import WeatherData


@dataclass
class ScreenState:
    current_time: str = ""
    weather: WeatherData | None = None
    phrase: str = ""
    alarm: AlarmData | None = None
    alarm_triggered: bool = False
    location: LocationData | None = None
