from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smart_mirror.core.settings import SettingsManager
    from smart_mirror.display.base import DisplayAdapter


@dataclass
class CommandPayload:
    pass


class Command(ABC):
    def __init__(self, settings: SettingsManager, display: DisplayAdapter) -> None:
        self._settings = settings
        self._display = display

    @staticmethod
    @abstractmethod
    def topic() -> str:
        """MQTT sub-topic this command handles, e.g. 'alarm/set'."""
        ...

    @staticmethod
    @abstractmethod
    def parse_payload(raw: dict) -> CommandPayload: ...

    @abstractmethod
    def execute(self, payload: CommandPayload) -> None: ...
