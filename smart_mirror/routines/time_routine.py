from __future__ import annotations

from datetime import datetime

from smart_mirror.display.base import DisplayAdapter
from smart_mirror.routines.base import Routine


class TimeRoutine(Routine):
    def __init__(self, interval_seconds: int, display: DisplayAdapter) -> None:
        super().__init__(interval_seconds)
        self._display = display

    def execute(self) -> None:
        time_str = datetime.now().strftime("%H:%M")
        self._display.update_time(time_str)
