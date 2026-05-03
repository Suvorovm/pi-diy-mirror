from __future__ import annotations

from dataclasses import dataclass

from smart_mirror.commands.base import Command, CommandPayload
from smart_mirror.data.alarm import AlarmData


@dataclass
class SetAlarmPayload(CommandPayload):
    hour: int
    minute: int


class SetAlarmCommand(Command):
    @staticmethod
    def topic() -> str:
        return "alarm/set"

    @staticmethod
    def parse_payload(raw: dict) -> SetAlarmPayload:
        return SetAlarmPayload(hour=int(raw["hour"]), minute=int(raw["minute"]))

    def execute(self, payload: SetAlarmPayload) -> None:
        if not (0 <= payload.hour <= 23 and 0 <= payload.minute <= 59):
            raise ValueError(f"Invalid alarm time: {payload.hour}:{payload.minute}")
        alarm = AlarmData(hour=payload.hour, minute=payload.minute)
        self._settings.set_alarm(alarm)
        self._display.update_alarm(alarm)
