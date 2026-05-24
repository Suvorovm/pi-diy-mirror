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
import socket
import threading
from typing import Callable

from bless import BlessServer, BlessGATTCharacteristic  # type: ignore[import]
from bless import GATTCharacteristicProperties as Prop  # type: ignore[import]
from bless import GATTAttributePermissions as Perm  # type: ignore[import]

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
        self._stop_event: asyncio.Event | None = None
        # Prevents parallel connection attempts
        self._connecting = False

    # ── Public API ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start advertising in a background daemon thread."""
        self._prepare_adapter()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="BleProvisioner",
        )
        self._thread.start()
        logger.info("BLE provisioner started (advertising as '%s')", DEVICE_NAME)

    @staticmethod
    def _prepare_adapter() -> None:
        """Ensure the BLE adapter is ready for LE advertising.

        bless on some BlueZ versions does not register the advertisement
        packet correctly, so we drive it manually via bluetoothctl.
        bless still handles the GATT application (characteristics).
        """
        import subprocess

        # 1. Enable LE at the controller level
        for cmd in [
            ["sudo", "btmgmt", "le", "on"],
            ["sudo", "btmgmt", "connectable", "on"],
        ]:
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except Exception as e:
                logger.warning("btmgmt %s failed: %s", cmd[2], e)

        # 2. Set adapter alias so the device name is correct in scan results
        try:
            subprocess.run(
                ["bluetoothctl", "system-alias", DEVICE_NAME],
                capture_output=True,
                timeout=5,
            )
            logger.info("BLE adapter alias set to '%s'", DEVICE_NAME)
        except Exception as e:
            logger.warning("Failed to set adapter alias: %s", e)

        # 3. Register advertisement (name + service UUID) via bluetoothctl
        bt_script = "\n".join([
            "menu advertise",
            f"name {DEVICE_NAME}",
            f"uuids {SERVICE_UUID}",
            "discoverable on",
            "back",
            "advertise on",
            "quit",
        ]) + "\n"
        try:
            subprocess.run(
                ["bluetoothctl"],
                input=bt_script,
                capture_output=True,
                text=True,
                timeout=10,
            )
            logger.info("BLE advertising configured via bluetoothctl")
        except Exception as e:
            logger.warning("bluetoothctl advertising setup failed: %s", e)

    def stop(self) -> None:
        """Signal the BLE server to shut down cleanly."""
        if self._loop and self._loop.is_running() and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)

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

        # asyncio.Event for clean shutdown — set by stop() via call_soon_threadsafe
        self._stop_event = asyncio.Event()

        server = BlessServer(name=DEVICE_NAME, loop=loop)
        server.read_request_func = self._on_read
        server.write_request_func = self._on_write
        self._server = server

        initial_ip = _get_local_ip()
        initial_status = (
            _encode_status("connected", ip=initial_ip)
            if initial_ip
            else _encode_status("idle")
        )
        if initial_ip:
            logger.info("BLE: already connected, advertising IP %s", initial_ip)

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
                    "Value": initial_status,
                },
            }
        }

        await server.add_gatt(gatt)
        await server.start()
        logger.info("BLE GATT server started, advertising as '%s'", DEVICE_NAME)

        # Block until stop() is called — cleaner than raw create_future()
        await self._stop_event.wait()

        await server.stop()
        logger.info("BLE GATT server stopped")

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

        if result == WifiResult.CONNECTED:
            ip = _get_local_ip()
            await self._notify_status("connected", ip=ip)
            logger.info("BLE: notified client with IP %s", ip)
            # Fire the MQTT-restart callback in a separate thread — never block the BLE loop
            threading.Thread(
                target=self._on_wifi_connected,
                daemon=True,
                name="MqttRestart",
            ).start()
        else:
            await self._notify_status(result.value)

        self._connecting = False

    async def _notify_status(self, status: str, **extra) -> None:
        """Update the STATUS characteristic and push a BLE notification."""
        if self._server is None:
            return
        char = self._server.get_characteristic(STATUS_UUID)
        if char is None:
            return
        char.value = _encode_status(status, **extra)
        self._server.update_value(SERVICE_UUID, STATUS_UUID)
        logger.debug("BLE status → %s %s", status, extra)


def _encode_status(status: str, **extra) -> bytearray:
    return bytearray(json.dumps({"status": status, **extra}).encode("utf-8"))


def _get_local_ip() -> str:
    """Return the outbound IP of the Wi-Fi interface by probing a remote address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return ""
