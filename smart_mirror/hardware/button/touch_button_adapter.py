from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class TouchButtonAdapter(ABC):
    """
    Абстракция сенсорной кнопки.

    Реализации:
      - ConsoleButton  — для разработки (ждёт нажатия Enter в stdin)
      - Ttp223Button   — TTP223 ёмкостный сенсор на GPIO (Pi)

    Паттерн: callback-based.
    После start_listening() адаптер сам следит за нажатием в фоне
    и вызывает on_press() один раз когда кнопка нажата.
    """

    @abstractmethod
    def start_listening(self, on_press: Callable[[], None]) -> None:
        """
        Начать слушать кнопку.
        on_press() будет вызван из фонового потока при нажатии.
        """
        ...

    @abstractmethod
    def stop_listening(self) -> None:
        """Прекратить слушать кнопку."""
        ...
