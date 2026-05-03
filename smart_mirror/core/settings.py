from __future__ import annotations

import json
import os
import threading

from smart_mirror.data.alarm import AlarmData


class SettingsManager:
    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._alarm: AlarmData | None = self._load()

    def get_alarm(self) -> AlarmData | None:
        with self._lock:
            return self._alarm

    def set_alarm(self, alarm: AlarmData) -> None:
        with self._lock:
            self._alarm = alarm
            self._save({"alarm": {"hour": alarm.hour, "minute": alarm.minute}})

    def clear_alarm(self) -> None:
        with self._lock:
            self._alarm = None
            self._save({})

    def _load(self) -> AlarmData | None:
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, encoding="utf-8") as f:
                raw = json.load(f)
            if "alarm" in raw:
                return AlarmData(**raw["alarm"])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        return None

    def _save(self, data: dict) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)
