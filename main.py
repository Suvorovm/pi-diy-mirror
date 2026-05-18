import argparse
import logging
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from smart_mirror.alarm.handler import AlarmHandler
from smart_mirror.commands.clear_alarm import ClearAlarmCommand
from smart_mirror.commands.registry import CommandRegistry
from smart_mirror.commands.restart_device import RestartDeviceCommand
from smart_mirror.commands.set_alarm import SetAlarmCommand
from smart_mirror.commands.set_location import SetLocationCommand
from smart_mirror.core.app import SmartMirrorApp
from smart_mirror.core.config import Config
from smart_mirror.core.settings import SettingsManager
from smart_mirror.display.display_adapter import DisplayAdapter
from smart_mirror.display.console_display import ConsoleDisplay
from smart_mirror.hardware.buzzer.buzzer_adapter import BuzzerAdapter
from smart_mirror.hardware.button.touch_button_adapter import TouchButtonAdapter
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


def _build_display(display_type: str) -> DisplayAdapter:
    if display_type == "st7735":
        from smart_mirror.display.st7735_display import St7735Display
        return St7735Display()
    return ConsoleDisplay()


def _build_hardware(display_type: str) -> tuple[BuzzerAdapter, TouchButtonAdapter]:
    """Возвращает (buzzer, button) для выбранного бэкенда."""
    if display_type == "st7735":
        from smart_mirror.hardware.buzzer.ky012 import Ky012Buzzer
        from smart_mirror.hardware.button.ttp223 import Ttp223Button
        return Ky012Buzzer(), Ttp223Button()
    from smart_mirror.hardware.buzzer.console import ConsoleBuzzer
    from smart_mirror.hardware.button.console import ConsoleButton
    return ConsoleBuzzer(), ConsoleButton()


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
    parser = argparse.ArgumentParser(description="Smart Mirror")
    parser.add_argument(
        "--display",
        choices=["console", "st7735"],
        default="console",
        help="Бэкенд дисплея: console (по умолчанию) или st7735 (TFT на Pi)",
    )
    args = parser.parse_args()

    config = Config.load(os.path.join(BASE_DIR, "config.json"))
    settings = SettingsManager(os.path.join(BASE_DIR, "settings.json"))
    display = _build_display(args.display)
    buzzer, button = _build_hardware(args.display)
    alarm_handler = AlarmHandler(display, buzzer, button)
    logger.info("Display backend: %s", args.display)

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
    runner.register(AlarmCheckRoutine(config.intervals.alarm_check_seconds, settings, alarm_handler))

    mqtt_client = MqttClient(config.mqtt, registry)

    app = SmartMirrorApp(
        config=config,
        settings=settings,
        display=display,
        mqtt_client=mqtt_client,
        routine_runner=runner,
        registry=registry,
    )

    try:
        app.run_forever()
    finally:
        if args.display == "st7735":
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                logger.info("GPIO cleanup done")
            except Exception:
                pass


if __name__ == "__main__":
    main()
