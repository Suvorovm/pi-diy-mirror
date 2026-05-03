import logging
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from smart_mirror.commands.clear_alarm import ClearAlarmCommand
from smart_mirror.commands.registry import CommandRegistry
from smart_mirror.commands.restart_device import RestartDeviceCommand
from smart_mirror.commands.set_alarm import SetAlarmCommand
from smart_mirror.commands.set_location import SetLocationCommand
from smart_mirror.core.app import SmartMirrorApp
from smart_mirror.core.config import Config
from smart_mirror.core.settings import SettingsManager
from smart_mirror.display.console_display import ConsoleDisplay
from smart_mirror.location.detector import LocationDetector
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

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _bootstrap_location(settings: SettingsManager, display: ConsoleDisplay) -> None:
    """
    If no location is saved in settings, auto-detect from IP and persist it.
    If auto-detection also fails, we leave settings empty — WeatherRoutine will
    fall back to the coordinates in config.json.
    """
    if settings.get_location() is not None:
        logger.info("Using saved location: %s", settings.get_location())
        display.update_location(settings.get_location())
        return

    logger.info("No saved location found — attempting auto-detection...")
    detected = LocationDetector().detect()
    if detected:
        settings.set_location(detected)
        display.update_location(detected)
        logger.info("Location saved: %s", detected)
    else:
        logger.warning("Location auto-detection failed. Weather will use config.json defaults.")


def main() -> None:
    config = Config.load(os.path.join(BASE_DIR, "config.json"))
    settings = SettingsManager(os.path.join(BASE_DIR, "settings.json"))
    display = ConsoleDisplay()

    # Determine location before starting routines
    _bootstrap_location(settings, display)

    registry = CommandRegistry(settings, display)
    registry.register(SetAlarmCommand)
    registry.register(ClearAlarmCommand)
    registry.register(SetLocationCommand)
    registry.register(RestartDeviceCommand)

    weather_fetcher = WeatherFetcher()

    runner = RoutineRunner()
    runner.register(TimeRoutine(config.intervals.time_seconds, display))
    runner.register(WeatherRoutine(
        interval_seconds=config.weather.refresh_interval_seconds,
        fetcher=weather_fetcher,
        settings=settings,
        display=display,
        default_location=config.weather,
    ))
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
