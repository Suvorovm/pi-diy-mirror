from __future__ import annotations

from datetime import date, datetime

from smart_mirror.alarm.handler import AlarmHandler
from smart_mirror.core.settings import SettingsManager
from smart_mirror.routines.routine import Routine


class AlarmCheckRoutine(Routine):
    """
    Каждые interval_seconds проверяет, пришло ли время будильника.
    При совпадении — делегирует в AlarmHandler (зуммер + экран + кнопка).

    Защита от повторного срабатывания: _last_triggered хранит (дата, час, минута)
    последнего срабатывания. Если пользователь ставит новый будильник на другое
    время — ключ не совпадает и будильник сработает снова.
    """

    def __init__(
        self,
        interval_seconds: int,
        settings: SettingsManager,
        alarm_handler: AlarmHandler,
    ) -> None:
        super().__init__(interval_seconds)
        self._settings = settings
        self._alarm_handler = alarm_handler
        self._last_triggered: tuple[date, int, int] | None = None

    def execute(self) -> None:
        alarm = self._settings.get_alarm()
        if alarm is None:
            return

        now = datetime.now()

        if now.hour == alarm.hour and now.minute == alarm.minute:
            key = (now.date(), alarm.hour, alarm.minute)
            if self._last_triggered == key:
                return
            self._last_triggered = key
            self._alarm_handler.trigger()
