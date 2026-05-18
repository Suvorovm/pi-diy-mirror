from __future__ import annotations

from dataclasses import dataclass

from smart_mirror.commands.command import Command, CommandPayload
from smart_mirror.data.location import LocationData


@dataclass
class SetLocationPayload(CommandPayload):
    latitude: float
    longitude: float
    city: str = ""


class SetLocationCommand(Command):
    @staticmethod
    def topic() -> str:
        return "location/set"

    @staticmethod
    def parse_payload(raw: dict) -> SetLocationPayload:
        return SetLocationPayload(
            latitude=float(raw["latitude"]),
            longitude=float(raw["longitude"]),
            city=str(raw.get("city", "")),
        )

    def execute(self, payload: SetLocationPayload) -> None:
        if not (-90 <= payload.latitude <= 90):
            raise ValueError(f"Invalid latitude: {payload.latitude}")
        if not (-180 <= payload.longitude <= 180):
            raise ValueError(f"Invalid longitude: {payload.longitude}")

        location = LocationData(
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=payload.city,
        )
        self._settings.set_location(location)
        self._display.update_location(location)
