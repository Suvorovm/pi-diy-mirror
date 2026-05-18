from __future__ import annotations

import logging
from typing import Callable

from smart_mirror.hardware.button.touch_button_adapter import TouchButtonAdapter

logger = logging.getLogger(__name__)

_DEFAULT_PIN = 17  # GPIO17 — вывод OUT кнопки TTP223


class Ttp223Button(TouchButtonAdapter):
    """
    TTP223 ёмкостный сенсор.

    Подключение:
      OUT → GPIO17 (Pin 11)
      VCC → 3.3V
      GND → GND

    Принцип: OUT = HIGH когда палец касается площадки.
    Используем прерывание по переднему фронту (RISING edge) — это
    эффективнее опроса и не нагружает CPU.
    Bouncetime 300 мс защищает от дребезга.
    """

    def __init__(self, pin: int = _DEFAULT_PIN) -> None:
        import RPi.GPIO as GPIO
        self._pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN)
        logger.debug("Ttp223Button ready on GPIO%d", self._pin)

    def start_listening(self, on_press: Callable[[], None]) -> None:
        import RPi.GPIO as GPIO

        def _callback(channel: int) -> None:
            logger.debug("TTP223 touch detected on GPIO%d", channel)
            on_press()

        GPIO.add_event_detect(
            self._pin,
            GPIO.RISING,
            callback=_callback,
            bouncetime=300,
        )
        logger.debug("TTP223 listening on GPIO%d", self._pin)

    def stop_listening(self) -> None:
        import RPi.GPIO as GPIO
        try:
            GPIO.remove_event_detect(self._pin)
            logger.debug("TTP223 stopped listening on GPIO%d", self._pin)
        except Exception:
            pass  # Уже снято или GPIO не инициализирован
