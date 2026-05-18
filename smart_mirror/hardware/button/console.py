from __future__ import annotations

import logging
import threading
from typing import Callable

from smart_mirror.hardware.button.touch_button_adapter import TouchButtonAdapter

logger = logging.getLogger(__name__)


class ConsoleButton(TouchButtonAdapter):
    """
    Консольная заглушка кнопки — ждёт нажатия Enter в stdin.
    Используется при разработке вместо реального TTP223.
    """

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start_listening(self, on_press: Callable[[], None]) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._wait_for_enter,
            args=(on_press,),
            daemon=True,
            name="ConsoleButton",
        )
        self._thread.start()

    def stop_listening(self) -> None:
        self._stop.set()

    def _wait_for_enter(self, on_press: Callable[[], None]) -> None:
        logger.info("[КНОПКА] Нажми Enter чтобы отключить будильник...")
        try:
            input()
        except EOFError:
            return
        if not self._stop.is_set():
            on_press()
