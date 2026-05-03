from __future__ import annotations

import logging

import requests

from smart_mirror.data.location import LocationData

logger = logging.getLogger(__name__)

_API_URL = "http://ip-api.com/json/"
_TIMEOUT_SECONDS = 10


class LocationDetector:
    """Determines device location by IP address using ip-api.com (free, no API key)."""

    def detect(self) -> LocationData | None:
        """
        Fetches current location from IP geolocation API.
        Returns None if detection fails (offline, API down, etc.).
        """
        try:
            response = requests.get(_API_URL, timeout=_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.warning("IP geolocation returned status: %s", data.get("status"))
                return None

            location = LocationData(
                latitude=float(data["lat"]),
                longitude=float(data["lon"]),
                city=data.get("city", ""),
            )
            logger.info("Auto-detected location: %s", location)
            return location

        except Exception:
            logger.warning("Could not auto-detect location (no internet?)")
            return None
