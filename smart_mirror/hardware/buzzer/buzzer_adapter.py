from __future__ import annotations

from abc import ABC, abstractmethod


class BuzzerAdapter(ABC):
    """
    Абстракция зуммера.

    Реализации:
      - ConsoleBuzzer  — для разработки (пишет в лог)
      - Ky012Buzzer    — KY-012 активный зуммер на GPIO (Pi)
    """

    @abstractmethod
    def start(self) -> None:
        """Начать непрерывный звук."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Остановить звук."""
        ...
