from __future__ import annotations

import signal
import threading

from smart_mirror.commands.registry import CommandRegistry
from smart_mirror.core.config import Config
from smart_mirror.core.settings import SettingsManager
from smart_mirror.display.display_adapter import DisplayAdapter
from smart_mirror.mqtt.client import MqttClient
from smart_mirror.routines.runner import RoutineRunner


class SmartMirrorApp:
    def __init__(
        self,
        config: Config,
        settings: SettingsManager,
        display: DisplayAdapter,
        mqtt_client: MqttClient,
        routine_runner: RoutineRunner,
        registry: CommandRegistry,
    ) -> None:
        self._config = config
        self._settings = settings
        self._display = display
        self._mqtt = mqtt_client
        self._runner = routine_runner
        self._registry = registry
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._runner.start()
        self._mqtt.start()

    def stop(self) -> None:
        self._mqtt.stop()
        self._runner.stop()
        self._stop_event.set()

    def run_forever(self) -> None:
        self.start()

        def _handle_signal(sig, frame):
            self.stop()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        self._stop_event.wait()
