from __future__ import annotations

from abc import ABC, abstractmethod


class Routine(ABC):
    def __init__(self, interval_seconds: int) -> None:
        self._interval_seconds = interval_seconds

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    @abstractmethod
    def execute(self) -> None: ...
