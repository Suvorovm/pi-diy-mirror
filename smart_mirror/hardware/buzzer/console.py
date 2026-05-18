from __future__ import annotations

import logging

from smart_mirror.hardware.buzzer.buzzer_adapter import BuzzerAdapter

logger = logging.getLogger(__name__)


class ConsoleBuzzer(BuzzerAdapter):
    """Консольная заглушка зуммера — пишет в лог вместо GPIO."""

    def start(self) -> None:
        logger.info("[ЗУММЕР] BEEP BEEP BEEP... (нажми Enter чтобы отключить)")

    def stop(self) -> None:
        logger.info("[ЗУММЕР] тишина")
