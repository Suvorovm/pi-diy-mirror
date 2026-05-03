from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt

from smart_mirror.commands.registry import CommandRegistry
from smart_mirror.core.config import MqttConfig

logger = logging.getLogger(__name__)


class MqttClient:
    def __init__(self, config: MqttConfig, registry: CommandRegistry) -> None:
        self._config = config
        self._registry = registry
        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def start(self) -> None:
        self._client.connect(self._config.broker_host, self._config.broker_port)
        self._client.loop_start()
        logger.info("MQTT client started, connecting to %s:%d", self._config.broker_host, self._config.broker_port)

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT client stopped")

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            topic = self._config.topic_prefix + "#"
            client.subscribe(topic)
            logger.info("Connected to broker, subscribed to '%s'", topic)
        else:
            logger.error("MQTT connection failed with code %d", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        if rc != 0:
            logger.warning("Unexpected MQTT disconnect (rc=%d), paho will reconnect", rc)

    def _on_message(self, client, userdata, message) -> None:
        topic: str = message.topic
        prefix = self._config.topic_prefix

        if not topic.startswith(prefix):
            return

        sub_topic = topic[len(prefix):]

        try:
            raw = json.loads(message.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raw = {}

        logger.debug("Received MQTT message: topic='%s' payload=%s", sub_topic, raw)
        self._registry.dispatch(sub_topic, raw)
