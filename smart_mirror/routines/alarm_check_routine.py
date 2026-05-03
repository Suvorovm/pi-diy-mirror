from __future__ import annotations

from datetime import date, datetime

from smart_mirror.core.settings import SettingsManager
from smart_mirror.display.base import DisplayAdapter
from smart_mirror.routines.base import Routine


class AlarmCheckRoutine(Routine):
    def __init__(
        self,
        interval_seconds: int,
        settings: SettingsManager,
        display: DisplayAdapter,
    ) -> None:
        super().__init__(interval_seconds)
        self._settings = settings
        self._display = display
        self._last_triggered: date | None = None

    def execute(self) -> None:
        alarm = self._settings.get_alarm()
        if alarm is None:
            return

        now = datetime.now()
        today = now.date()

        already_triggered_today = self._last_triggered == today
        if already_triggered_today:
            return

        if now.hour == alarm.hour and now.minute == alarm.minute:
            self._last_triggered = today
            self._display.show_alarm_triggered()
