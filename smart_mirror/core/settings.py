from __future__ import annotations

import json
import os
import threading

from smart_mirror.data.alarm import AlarmData
from smart_mirror.data.location import LocationData


class SettingsManager:
    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: dict = self._load_raw()

    # ── Alarm ────────────────────────────────────────────────────────────────

    def get_alarm(self) -> AlarmData | None:
        with self._lock:
            raw = self._data.get("alarm")
            if raw:
                try:
                    return AlarmData(**raw)
                except (KeyError, TypeError):
                    pass
            return None

    def set_alarm(self, alarm: AlarmData) -> None:
        with self._lock:
            self._data["alarm"] = {"hour": alarm.hour, "minute": alarm.minute}
            self._save()

    def clear_alarm(self) -> None:
        with self._lock:
            self._data.pop("alarm", None)
            self._save()

    # ── Location ─────────────────────────────────────────────────────────────

    def get_location(self) -> LocationData | None:
        with self._lock:
            raw = self._data.get("location")
            if raw:
                try:
                    return LocationData(
                        latitude=float(raw["latitude"]),
                        longitude=float(raw["longitude"]),
                        city=raw.get("city", ""),
                    )
                except (KeyError, TypeError, ValueError):
                    pass
            return None

    def set_location(self, location: LocationData) -> None:
        with self._lock:
            self._data["location"] = {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "city": location.city,
            }
            self._save()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load_raw(self) -> dict:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        """Atomic write: write to .tmp then replace. Safe on power loss."""
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)
