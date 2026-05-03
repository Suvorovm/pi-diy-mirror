from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

from smart_mirror.commands.base import Command, CommandPayload

logger = logging.getLogger(__name__)


@dataclass
class RestartDevicePayload(CommandPayload):
    pass


class RestartDeviceCommand(Command):
    @staticmethod
    def topic() -> str:
        return "device/restart"

    @staticmethod
    def parse_payload(raw: dict) -> RestartDevicePayload:
        return RestartDevicePayload()

    def execute(self, payload: RestartDevicePayload) -> None:
        logger.info("Restarting device...")
        try:
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error("Reboot failed: %s", e)
