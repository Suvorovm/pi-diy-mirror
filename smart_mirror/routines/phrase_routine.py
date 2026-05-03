from __future__ import annotations

import json
import random

from smart_mirror.display.base import DisplayAdapter
from smart_mirror.routines.base import Routine


class PhraseRoutine(Routine):
    def __init__(
        self,
        interval_seconds: int,
        phrases_file: str,
        display: DisplayAdapter,
    ) -> None:
        super().__init__(interval_seconds)
        self._display = display
        with open(phrases_file, encoding="utf-8") as f:
            self._phrases: list[str] = json.load(f)

    def execute(self) -> None:
        if self._phrases:
            self._display.update_phrase(random.choice(self._phrases))
