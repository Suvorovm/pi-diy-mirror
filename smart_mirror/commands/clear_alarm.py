from __future__ import annotations

from dataclasses import dataclass

from smart_mirror.commands.base import Command, CommandPayload


@dataclass
class ClearAlarmPayload(CommandPayload):
    pass


class ClearAlarmCommand(Command):
    @staticmethod
    def topic() -> str:
        return "alarm/clear"

    @staticmethod
    def parse_payload(raw: dict) -> ClearAlarmPayload:
        return ClearAlarmPayload()

    def execute(self, payload: ClearAlarmPayload) -> None:
        self._settings.clear_alarm()
        self._display.update_alarm(None)
