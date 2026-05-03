import logging
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from smart_mirror.commands.registry import CommandRegistry
from smart_mirror.commands.restart_device import RestartDeviceCommand
from smart_mirror.commands.set_alarm import SetAlarmCommand
from smart_mirror.core.app import SmartMirrorApp
from smart_mirror.core.config import Config
from smart_mirror.core.settings import SettingsManager
from smart_mirror.display.console_display import ConsoleDisplay
from smart_mirror.mqtt.client import MqttClient
from smart_mirror.routines.alarm_check_routine import AlarmCheckRoutine
from smart_mirror.routines.phrase_routine import PhraseRoutine
from smart_mirror.routines.runner import RoutineRunner
from smart_mirror.routines.time_routine import TimeRoutine
from smart_mirror.routines.weather_routine import WeatherRoutine
from smart_mirror.weather.fetcher import WeatherFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    config = Config.load(os.path.join(BASE_DIR, "config.json"))
    settings = SettingsManager(os.path.join(BASE_DIR, "settings.json"))
    display = ConsoleDisplay()

    registry = CommandRegistry(settings, display)
    registry.register(SetAlarmCommand)
    registry.register(RestartDeviceCommand)

    weather_fetcher = WeatherFetcher(config.weather)

    runner = RoutineRunner()
    runner.register(TimeRoutine(config.intervals.time_seconds, display))
    runner.register(WeatherRoutine(config.weather.refresh_interval_seconds, weather_fetcher, display))
    runner.register(PhraseRoutine(config.intervals.phrase_seconds, config.phrases_file, display))
    runner.register(AlarmCheckRoutine(config.intervals.alarm_check_seconds, settings, display))

    mqtt_client = MqttClient(config.mqtt, registry)

    app = SmartMirrorApp(
        config=config,
        settings=settings,
        display=display,
        mqtt_client=mqtt_client,
        routine_runner=runner,
        registry=registry,
    )

    app.run_forever()


if __name__ == "__main__":
    main()
