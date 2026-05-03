from dataclasses import dataclass


@dataclass
class WeatherData:
    temperature_celsius: float
    weather_code: int
    description: str
    wind_speed_kmh: float
