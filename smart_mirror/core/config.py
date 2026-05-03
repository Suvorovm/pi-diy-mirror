from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class MqttConfig:
    broker_host: str
    broker_port: int
    topic_prefix: str


@dataclass(frozen=True)
class WeatherConfig:
    latitude: float
    longitude: float
    refresh_interval_seconds: int


@dataclass(frozen=True)
class IntervalConfig:
    time_seconds: int
    phrase_seconds: int
    alarm_check_seconds: int


@dataclass(frozen=True)
class Config:
    mqtt: MqttConfig
    weather: WeatherConfig
    intervals: IntervalConfig
    phrases_file: str

    @staticmethod
    def load(path: str) -> Config:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        mqtt = MqttConfig(**raw["mqtt"])
        weather = WeatherConfig(**raw["weather"])
        intervals = IntervalConfig(**raw["intervals"])
        return Config(
            mqtt=mqtt,
            weather=weather,
            intervals=intervals,
            phrases_file=raw["phrases_file"],
        )
