from __future__ import annotations

import logging
import threading

from smart_mirror.display.display_adapter import DisplayAdapter
from smart_mirror.hardware.buzzer.buzzer_adapter import BuzzerAdapter
from smart_mirror.hardware.button.touch_button_adapter import TouchButtonAdapter

logger = logging.getLogger(__name__)


class AlarmHandler:
    """
    Координирует срабатывание будильника:

      1. AlarmCheckRoutine замечает совпадение времени → вызывает trigger()
      2. trigger(): показывает баннер на экране + включает зуммер +
                    начинает слушать кнопку
      3. Пользователь нажимает кнопку → _on_button_press() → _dismiss()
      4. _dismiss(): выключает зуммер + убирает баннер с экрана

    Потокобезопасен: trigger() и _dismiss() могут вызываться из
    разных потоков (RoutineRunner и callback GPIO/stdin).
    """

    def __init__(
        self,
        display: DisplayAdapter,
        buzzer: BuzzerAdapter,
        button: TouchButtonAdapter,
    ) -> None:
        self._display = display
        self._buzzer = buzzer
        self._button = button
        self._active = False
        self._lock = threading.Lock()

    def trigger(self) -> None:
        """
        Вызвать при наступлении времени будильника.
        Идемпотентен — повторный вызов игнорируется.
        """
        with self._lock:
            if self._active:
                return
            self._active = True

        logger.info("Alarm triggered — starting buzzer and waiting for button press")
        self._display.show_alarm_triggered()
        self._buzzer.start()
        self._button.start_listening(self._on_button_press)

    def _on_button_press(self) -> None:
        self._dismiss()

    def _dismiss(self) -> None:
        with self._lock:
            if not self._active:
                return
            self._active = False

        logger.info("Alarm dismissed by user")
        self._buzzer.stop()
        self._button.stop_listening()
        self._display.dismiss_alarm_triggered()
