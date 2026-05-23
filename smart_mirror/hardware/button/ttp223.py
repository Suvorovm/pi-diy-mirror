from __future__ import annotations

import logging
import threading
from typing import Callable

from smart_mirror.hardware.button.touch_button_adapter import TouchButtonAdapter

logger = logging.getLogger(__name__)

_DEFAULT_PIN = 17  # GPIO17 — вывод OUT кнопки TTP223
_POLL_INTERVAL = 0.05  # сек


class Ttp223Button(TouchButtonAdapter):
    """
    TTP223 ёмкостный сенсор.

    Подключение:
      OUT → GPIO17 (Pin 11)
      VCC → 3.3V
      GND → GND

    Принцип: OUT = HIGH когда палец касается площадки.
    Используем опрос (polling) в daemon-потоке — надёжнее, чем
    GPIO.add_event_detect с bouncetime (известный баг RPi.GPIO, при котором
    callback может не сработать).
    """

    def __init__(self, pin: int = _DEFAULT_PIN) -> None:
        import RPi.GPIO as GPIO
        self._pin = pin
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN)
        logger.debug("Ttp223Button ready on GPIO%d", self._pin)

    def start_listening(self, on_press: Callable[[], None]) -> None:
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(on_press,),
            daemon=True,
            name="Ttp223PollThread",
        )
        self._thread.start()
        logger.debug("TTP223 polling started on GPIO%d", self._pin)

    def _poll_loop(self, on_press: Callable[[], None]) -> None:
        import RPi.GPIO as GPIO
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                if GPIO.input(self._pin) == GPIO.HIGH:
                    logger.debug("TTP223 touch detected on GPIO%d", self._pin)
                    on_press()
                    return
            except Exception:
                logger.exception("TTP223 poll error on GPIO%d", self._pin)
                return
            self._stop_event.wait(_POLL_INTERVAL)

    def stop_listening(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._stop_event = None
        logger.debug("TTP223 stopped listening on GPIO%d", self._pin)
