from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

from smart_mirror.commands.base import Command

if TYPE_CHECKING:
    from smart_mirror.core.settings import SettingsManager
    from smart_mirror.display.base import DisplayAdapter

logger = logging.getLogger(__name__)


class CommandRegistry:
    def __init__(self, settings: SettingsManager, display: DisplayAdapter) -> None:
        self._settings = settings
        self._display = display
        self._commands: dict[str, Type[Command]] = {}

    def register(self, command_class: Type[Command]) -> None:
        self._commands[command_class.topic()] = command_class
        logger.debug("Registered command for topic '%s'", command_class.topic())

    def dispatch(self, sub_topic: str, raw: dict) -> None:
        command_class = self._commands.get(sub_topic)
        if command_class is None:
            logger.warning("No command registered for topic '%s'", sub_topic)
            return
        try:
            payload = command_class.parse_payload(raw)
            command = command_class(self._settings, self._display)
            command.execute(payload)
        except Exception:
            logger.exception("Error executing command for topic '%s'", sub_topic)
