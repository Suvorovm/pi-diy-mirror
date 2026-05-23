from __future__ import annotations

import logging
import threading

from smart_mirror.hardware.buzzer.buzzer_adapter import BuzzerAdapter

logger = logging.getLogger(__name__)

_DEFAULT_PIN = 19  # GPIO19 — вывод S зуммера KY-012

# Ритмический паттерн будильника: _ .. _ .. _ ..
# Каждый элемент: (on_ms, off_ms)
#   _ сильная доля  — длинный сигнал
#   .  слабая доля  — короткий сигнал
_PATTERN: list[tuple[int, int]] = [
    (480, 150),   # _  сильная
    (160, 100),   # .  слабая
    (160, 450),   # .  слабая + пауза перед следующим циклом
]


class Ky012Buzzer(BuzzerAdapter):
    """
    KY-012 активный зуммер.

    Подключение:
      S   → GPIO19 (Pin 35)
      +   → 3.3V
      -   → GND

    start() запускает ритмический паттерн (_ ..) в daemon-потоке.
    stop()  останавливает паттерн и глушит зуммер.
    """

    def __init__(self, pin: int = _DEFAULT_PIN) -> None:
        import RPi.GPIO as GPIO
        self._pin = pin
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.OUT, initial=GPIO.LOW)
        logger.debug("Ky012Buzzer ready on GPIO%d", self._pin)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._play_pattern,
            daemon=True,
            name="BuzzerPatternThread",
        )
        self._thread.start()
        logger.debug("Buzzer pattern started")

    def _play_pattern(self) -> None:
        import RPi.GPIO as GPIO
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            for on_ms, off_ms in _PATTERN:
                if self._stop_event.is_set():
                    break
                GPIO.output(self._pin, GPIO.HIGH)
                self._stop_event.wait(on_ms / 1000)
                GPIO.output(self._pin, GPIO.LOW)
                self._stop_event.wait(off_ms / 1000)
        GPIO.output(self._pin, GPIO.LOW)
        logger.debug("Buzzer pattern stopped")

    def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._stop_event = None
        try:
            import RPi.GPIO as GPIO
            GPIO.output(self._pin, GPIO.LOW)
        except Exception:
            pass
        logger.debug("Buzzer OFF")
