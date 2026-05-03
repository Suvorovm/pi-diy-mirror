from dataclasses import dataclass


@dataclass
class AlarmData:
    hour: int
    minute: int

    def __str__(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"
