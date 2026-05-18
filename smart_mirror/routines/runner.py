from __future__ import annotations

import logging
import threading
import time

from smart_mirror.routines.routine import Routine

logger = logging.getLogger(__name__)


class RoutineRunner:
    def __init__(self) -> None:
        self._routines: list[Routine] = []
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def register(self, routine: Routine) -> None:
        self._routines.append(routine)

    def start(self) -> None:
        self._stop_event.clear()
        for routine in self._routines:
            t = threading.Thread(
                target=self._run_routine,
                args=(routine,),
                daemon=True,
                name=type(routine).__name__,
            )
            self._threads.append(t)
            t.start()
            logger.debug("Started routine '%s' (interval=%ds)", type(routine).__name__, routine.interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()

    def _run_routine(self, routine: Routine) -> None:
        while not self._stop_event.is_set():
            try:
                routine.execute()
            except Exception:
                logger.exception("Error in routine '%s'", type(routine).__name__)
            self._stop_event.wait(timeout=routine.interval_seconds)
