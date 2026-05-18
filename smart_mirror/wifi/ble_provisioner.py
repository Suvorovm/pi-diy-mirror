"""
BLE Wi-Fi Provisioner — GATT server for receiving Wi-Fi credentials from a mobile app.

Architecture
────────────
BLE is used ONLY for initial Wi-Fi setup.  After a successful connection the device
continues to operate over Wi-Fi (MQTT etc.).  The provisioner stays running in the
background so the user can always re-provision (e.g. to switch networks).

Threading model
───────────────
`bless` requires an asyncio event loop.  We run the entire GATT server inside a
dedicated daemon thread with its own event loop.  The rest of the app stays purely
threaded (no asyncio).  The only cross-thread interaction is the `on_wifi_connected`
callback, which is called in a new daemon thread so it never blocks the BLE loop.

GATT layout
───────────
Service UUID    : 12345678-1234-5678-1234-56789abcdef0
  Write char    : abcdef01-1234-5678-1234-56789abcdef0
    → client sends: {"ssid": "Home_Wifi", "password": "12345678"}
  Notify char   : abcdef02-1234-5678-1234-56789abcdef0
    → server sends: {"status": "idle|connecting|connected|wrong_password|no_internet|error"}

Pi setup (run once)
───────────────────
  sudo systemctl enable --now bluetooth
  # Make sure the user can access the BLE adapter:
  sudo usermod -aG bluetooth pi
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Callable

from bless import BlessServer, BlessGATTCharacteristic  # type: ignore[import]
from bless import BlessGATTCharacteristicProperties as Prop  # type: ignore[import]
from bless import BlessGATTCharacteristicPermissions as Perm  # type: ignore[import]

from smart_mirror.wifi.wifi_manager import WifiManager, WifiResult

logger = logging.getLogger(__name__)

# ── UUIDs (must match the Flutter app) ─────────────────────────────────────────
SERVICE_UUID  = "12345678-1234-5678-1234-56789abcdef0"
WRITE_UUID    = "abcdef01-1234-5678-1234-56789abcdef0"
STATUS_UUID   = "abcdef02-1234-5678-1234-56789abcdef0"

DEVICE_NAME   = "SMART_MIRROR"


class BleProvisioner:
    """
    Advertises a BLE GATT server.  When it receives valid Wi-Fi credentials it:
      1. Sends status notifications back to the mobile client.
      2. Connects to the Wi-Fi network via WifiManager.
      3. Calls `on_wifi_connected` so the caller can restart MQTT.
    """

    def __init__(
        self,
        wifi_manager: WifiManager,
        on_wifi_connected: Callable[[], None],
    ) -> None:
        self._wifi = wifi_manager
        self._on_wifi_connected = on_wifi_connected
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: BlessServer | None = None
        self._thread: threading.Thread | None = None
        # Prevents parallel connection attempts
        self._connecting = False

    # ── Public API ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start advertising in a background daemon thread."""
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="BleProvisioner",
        )
        self._thread.start()
        logger.info("BLE provisioner started (advertising as '%s')", DEVICE_NAME)

    def stop(self) -> None:
        """Signal the event loop to stop."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ── Internal — runs inside the daemon thread ────────────────────────────────

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._serve())
        except Exception:
            logger.exception("BLE provisioner crashed")
        finally:
            loop.close()
            logger.info("BLE provisioner stopped")

    async def _serve(self) -> None:
        loop = asyncio.get_running_loop()

        server = BlessServer(name=DEVICE_NAME, loop=loop)
        server.read_request_func = self._on_read
        server.write_request_func = self._on_write
        self._server = server

        gatt: dict = {
            SERVICE_UUID: {
                WRITE_UUID: {
                    "Properties": Prop.write,
                    "Permissions": Perm.writeable,
                    "Value": None,
                },
                STATUS_UUID: {
                    "Properties": Prop.read | Prop.notify,
                    "Permissions": Perm.readable,
                    "Value": _encode_status("idle"),
                },
            }
        }

        await server.add_gatt(gatt)
        await server.start()
        logger.info("BLE GATT server started, waiting for connections...")

        # Keep the loop alive until stop() is called
        await asyncio.get_event_loop().create_future()

    # ── GATT callbacks ──────────────────────────────────────────────────────────

    def _on_read(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        return bytearray(characteristic.value or b"")

    def _on_write(self, characteristic: BlessGATTCharacteristic, value: bytearray, **kwargs) -> None:
        if str(characteristic.uuid).lower() != WRITE_UUID.lower():
            return

        if self._connecting:
            logger.warning("BLE: credentials received while already connecting — ignored")
            return

        try:
            raw = json.loads(value.decode("utf-8"))
            ssid: str = raw["ssid"]
            password: str = raw["password"]
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            logger.warning("BLE: invalid credentials payload: %s", e)
            return

        logger.info("BLE: received credentials for SSID '%s'", ssid)
        # Schedule async task on the running loop (we are already inside the loop)
        asyncio.ensure_future(self._connect_wifi(ssid, password))

    # ── Wi-Fi connection flow ───────────────────────────────────────────────────

    async def _connect_wifi(self, ssid: str, password: str) -> None:
        self._connecting = True
        await self._notify_status("connecting")

        loop = asyncio.get_running_loop()
        try:
            # Run blocking nmcli call in a thread pool so the BLE loop stays responsive
            result: WifiResult = await loop.run_in_executor(
                None, self._wifi.connect, ssid, password
            )
        except Exception:
            logger.exception("BLE: unexpected error during Wi-Fi connect")
            await self._notify_status("error")
            self._connecting = False
            return

        logger.info("BLE: Wi-Fi connect result: %s", result.value)
        await self._notify_status(result.value)

        if result == WifiResult.CONNECTED:
            # Fire the MQTT-restart callback in a separate thread — never block the BLE loop
            threading.Thread(
                target=self._on_wifi_connected,
                daemon=True,
                name="MqttRestart",
            ).start()

        self._connecting = False

    async def _notify_status(self, status: str) -> None:
        """Update the STATUS characteristic and push a BLE notification."""
        if self._server is None:
            return
        char = self._server.get_characteristic(STATUS_UUID)
        if char is None:
            return
        char.value = _encode_status(status)
        self._server.update_value(SERVICE_UUID, STATUS_UUID)
        logger.debug("BLE status → %s", status)


def _encode_status(status: str) -> bytearray:
    return bytearray(json.dumps({"status": status}).encode("utf-8"))
