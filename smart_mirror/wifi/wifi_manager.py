from __future__ import annotations

import logging
import subprocess
import time
from enum import Enum

import requests

logger = logging.getLogger(__name__)

_INTERNET_CHECK_URL = "https://api.open-meteo.com/v1/forecast"  # lightweight, no auth
_INTERNET_TIMEOUT = 5
_CONNECT_TIMEOUT = 30  # nmcli may take a while


class WifiResult(Enum):
    CONNECTED = "connected"
    WRONG_PASSWORD = "wrong_password"
    NO_INTERNET = "no_internet"
    ERROR = "error"


class WifiManager:
    """
    Manages Wi-Fi connections on Raspberry Pi via nmcli.

    Requirements on the Pi:
      - NetworkManager must be running: sudo systemctl enable --now NetworkManager
      - The user running this process needs nmcli access (usually works without sudo).
    """

    def connect(self, ssid: str, password: str) -> WifiResult:
        """
        Connect to the given Wi-Fi network.
        Blocks until connected, failed, or timed out (~30 seconds max).
        """
        logger.info("Connecting to Wi-Fi SSID: %s", ssid)
        try:
            cmd = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                cmd += ["password", password, "wifi-sec.key-mgmt", "wpa-psk"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_CONNECT_TIMEOUT,
            )
            output = result.stdout + result.stderr
            logger.debug("nmcli output: %s", output.strip())

            if result.returncode != 0:
                if "Secrets were required" in output or "password" in output.lower():
                    logger.warning("Wrong password for SSID: %s", ssid)
                    return WifiResult.WRONG_PASSWORD
                logger.error("nmcli failed (rc=%d): %s", result.returncode, output.strip())
                return WifiResult.ERROR

        except subprocess.TimeoutExpired:
            logger.error("nmcli connect timed out after %ds", _CONNECT_TIMEOUT)
            return WifiResult.ERROR
        except FileNotFoundError:
            logger.error("nmcli not found — is NetworkManager installed?")
            return WifiResult.ERROR
        except Exception:
            logger.exception("Unexpected error connecting to Wi-Fi")
            return WifiResult.ERROR

        # Connected to AP — now verify internet
        if not self._check_internet():
            logger.warning("Connected to %s but no internet access", ssid)
            return WifiResult.NO_INTERNET

        logger.info("Successfully connected to %s with internet access", ssid)
        return WifiResult.CONNECTED

    def is_connected(self) -> bool:
        """Returns True if any Wi-Fi interface is currently connected."""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "wifi:activated" in result.stdout
        except Exception:
            logger.debug("Could not check Wi-Fi connection state")
            return False

    def _check_internet(self) -> bool:
        """Sends a lightweight HTTP request to verify internet connectivity."""
        try:
            response = requests.head(_INTERNET_CHECK_URL, timeout=_INTERNET_TIMEOUT)
            return response.status_code < 500
        except Exception:
            return False
