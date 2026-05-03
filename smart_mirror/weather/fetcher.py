from __future__ import annotations

import requests

from smart_mirror.core.config import WeatherConfig
from smart_mirror.data.weather import WeatherData

# WMO Weather interpretation codes → human-readable descriptions
_WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Ясно",
    1: "Преимущественно ясно", 2: "Переменная облачность", 3: "Пасмурно",
    45: "Туман", 48: "Иней",
    51: "Лёгкая морось", 53: "Морось", 55: "Сильная морось",
    61: "Небольшой дождь", 63: "Дождь", 65: "Сильный дождь",
    71: "Небольшой снег", 73: "Снег", 75: "Сильный снег",
    77: "Снежные зёрна",
    80: "Небольшой ливень", 81: "Ливень", 82: "Сильный ливень",
    85: "Небольшой снегопад", 86: "Снегопад",
    95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
}

_API_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherFetcher:
    def __init__(self, config: WeatherConfig) -> None:
        self._config = config

    def fetch(self) -> WeatherData:
        params = {
            "latitude": self._config.latitude,
            "longitude": self._config.longitude,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "wind_speed_unit": "kmh",
        }
        response = requests.get(_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["current"]

        code = int(data["weather_code"])
        return WeatherData(
            temperature_celsius=float(data["temperature_2m"]),
            weather_code=code,
            description=_WMO_DESCRIPTIONS.get(code, f"Код {code}"),
            wind_speed_kmh=float(data["wind_speed_10m"]),
        )
