from __future__ import annotations

import os
import sys
import threading

from smart_mirror.data.alarm import AlarmData
from smart_mirror.data.weather import WeatherData
from smart_mirror.display.base import DisplayAdapter
from smart_mirror.display.screen_state import ScreenState

_SEPARATOR = "-" * 40


class ConsoleDisplay(DisplayAdapter):
    def __init__(self) -> None:
        self._state = ScreenState()
        self._lock = threading.Lock()

    def update_time(self, time_str: str) -> None:
        with self._lock:
            self._state.current_time = time_str
            self._state.alarm_triggered = False
        self.render()

    def update_weather(self, data: WeatherData) -> None:
        with self._lock:
            self._state.weather = data
        self.render()

    def update_phrase(self, phrase: str) -> None:
        with self._lock:
            self._state.phrase = phrase
        self.render()

    def update_alarm(self, alarm: AlarmData | None) -> None:
        with self._lock:
            self._state.alarm = alarm
        self.render()

    def show_alarm_triggered(self) -> None:
        with self._lock:
            self._state.alarm_triggered = True
        self.render()

    def render(self) -> None:
        with self._lock:
            state = self._state

        _clear()
        lines = [
            _SEPARATOR,
            f"  Время:    {state.current_time or '—'}",
        ]

        if state.weather:
            w = state.weather
            lines += [
                _SEPARATOR,
                f"  Погода:   {w.description}",
                f"  Темп:     {w.temperature_celsius:.1f}°C",
                f"  Ветер:    {w.wind_speed_kmh:.1f} км/ч",
            ]

        if state.phrase:
            lines += [
                _SEPARATOR,
                f"  >> {state.phrase}",
            ]

        if state.alarm:
            lines += [
                _SEPARATOR,
                f"  Будильник: {state.alarm}",
            ]

        if state.alarm_triggered:
            lines += [
                _SEPARATOR,
                "  *** БУДИЛЬНИК! ПРОСЫПАЙСЯ! ***",
            ]

        lines.append(_SEPARATOR)
        output = "\n".join(lines) + "\n"
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.flush()


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")
