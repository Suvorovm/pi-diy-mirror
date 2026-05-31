from __future__ import annotations

import json
import os
from dataclasses import dataclass

from smart_mirror.commands.command import Command, CommandPayload

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHRASES_FILE = os.path.join(BASE_DIR, "data", "phrases.json")


@dataclass
class SetPhrasesPayload(CommandPayload):
    phrases: list[str]


class SetPhrasesCommand(Command):
    @staticmethod
    def topic() -> str:
        return "phrase/set"

    @staticmethod
    def parse_payload(raw: dict) -> SetPhrasesPayload:
        return SetPhrasesPayload(phrases=list(raw["phrases"]))

    def execute(self, payload: SetPhrasesPayload) -> None:
        with open(PHRASES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload.phrases, f, ensure_ascii=False, indent=2)
