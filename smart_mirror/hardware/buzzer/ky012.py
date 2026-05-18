from __future__ import annotations

import logging

from smart_mirror.hardware.buzzer.buzzer_adapter import BuzzerAdapter

logger = logging.getLogger(__name__)

_DEFAULT_PIN = 19  # GPIO19 — вывод S зуммера KY-012


class Ky012Buzzer(BuzzerAdapter):
    """
    KY-012 активный зуммер.

    Подключение:
      S   → GPIO19 (Pin 35)
      +   → 3.3V
      -   → GND

    Принцип: активный зуммер, не требует ШИМ.
      GPIO HIGH → зуммер пищит
      GPIO LOW  → тишина
    """

    def __init__(self, pin: int = _DEFAULT_PIN) -> None:
        import RPi.GPIO as GPIO
        self._pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.OUT, initial=GPIO.LOW)
        logger.debug("Ky012Buzzer ready on GPIO%d", self._pin)

    def start(self) -> None:
        import RPi.GPIO as GPIO
        GPIO.output(self._pin, GPIO.HIGH)
        logger.debug("Buzzer ON")

    def stop(self) -> None:
        import RPi.GPIO as GPIO
        GPIO.output(self._pin, GPIO.LOW)
        logger.debug("Buzzer OFF")
