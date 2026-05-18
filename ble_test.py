"""
BLE Diagnostic — запускай на Raspberry Pi:
    python ble_test.py

Проверяет всю цепочку:
  1. Зависимости (bless, dbus-next, bleak)
  2. D-Bus system bus доступен
  3. Bluetooth-адаптер найден и включён
  4. GATT-сервер запускается и рекламирует
  5. Выводит UUID в логе — сверь с тем, что указан в Flutter-приложении

Если шаг проходит — печатает [OK], при ошибке — [FAIL] + объяснение.
"""

import asyncio
import sys


def check(label: str, ok: bool, hint: str = "") -> bool:
    status = "[OK] " if ok else "[FAIL]"
    print(f"  {status} {label}")
    if not ok and hint:
        print(f"         → {hint}")
    return ok


# ── 1. Импорты ──────────────────────────────────────────────────────────────────
print("\n=== 1. Python dependencies ===")

try:
    import bless  # noqa: F401
    check("bless installed", True)
except ImportError as e:
    check("bless installed", False, f"pip install bless==0.3.0   ({e})")
    sys.exit(1)

try:
    import dbus_next  # noqa: F401
    check("dbus-next installed", True)
except ImportError as e:
    check("dbus-next installed", False, f"pip install dbus-next==0.2.3   ({e})")
    sys.exit(1)

try:
    import bleak  # noqa: F401
    check("bleak installed", True)
except ImportError as e:
    check("bleak installed", False, f"pip install bleak   ({e})")
    sys.exit(1)

# ── 2. D-Bus system bus ─────────────────────────────────────────────────────────
print("\n=== 2. D-Bus system bus ===")

async def _check_dbus() -> bool:
    try:
        from dbus_next.aio import MessageBus
        from dbus_next.constants import BusType
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        await bus.wait_for_disconnect()  # не нужен, просто подключаемся
        return True
    except Exception as e:
        print(f"         Error: {e}")
        return False

async def _test_dbus():
    try:
        from dbus_next.aio import MessageBus
        from dbus_next.constants import BusType
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        check("Connected to D-Bus system bus", True)
        bus.disconnect()
        return True
    except Exception as e:
        check(
            "Connected to D-Bus system bus", False,
            f"D-Bus error: {e}\n"
            "         Fix: sudo systemctl start dbus",
        )
        return False

dbus_ok = asyncio.run(_test_dbus())
if not dbus_ok:
    sys.exit(1)

# ── 3. Bluetooth adapter ────────────────────────────────────────────────────────
print("\n=== 3. Bluetooth adapter ===")

import subprocess

def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()

rc, out = run(["systemctl", "is-active", "bluetooth"])
if check("bluetooth service running", rc == 0,
         "sudo systemctl enable --now bluetooth"):
    pass
else:
    sys.exit(1)

rc, out = run(["hciconfig"])
has_adapter = "hci0" in out
if check("HCI adapter present (hci0)", has_adapter,
         "No Bluetooth adapter found — check hardware or 'sudo hciconfig hci0 up'"):
    print(f"         {out.splitlines()[0] if out else ''}")
else:
    sys.exit(1)

# Is it up?
hci_up = "UP" in out
check("Adapter is UP", hci_up,
      "sudo hciconfig hci0 up")

# ── 4. GATT server startup test ─────────────────────────────────────────────────
print("\n=== 4. GATT server (10-second advertising test) ===")

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
WRITE_UUID   = "abcdef01-1234-5678-1234-56789abcdef0"
STATUS_UUID  = "abcdef02-1234-5678-1234-56789abcdef0"
DEVICE_NAME  = "SMART_MIRROR"

async def _test_gatt():
    from bless import BlessServer
    from bless import GATTCharacteristicProperties as Prop
    from bless import GATTAttributePermissions as Perm

    loop = asyncio.get_running_loop()
    server = BlessServer(name=DEVICE_NAME, loop=loop)
    server.read_request_func  = lambda c, **kw: bytearray(c.value or b"")
    server.write_request_func = lambda c, v, **kw: None

    gatt = {
        SERVICE_UUID: {
            WRITE_UUID: {
                "Properties": Prop.write,
                "Permissions": Perm.writeable,
                "Value": None,
            },
            STATUS_UUID: {
                "Properties": Prop.read | Prop.notify,
                "Permissions": Perm.readable,
                "Value": bytearray(b'{"status":"idle"}'),
            },
        }
    }

    try:
        await server.add_gatt(gatt)
        await server.start()
        check("BlessServer started + advertising", True)
        print(f"\n  Service UUID : {SERVICE_UUID}")
        print(f"  Device name  : {DEVICE_NAME}")
        print(f"\n  Now scan with your phone for 10 seconds...")
        await asyncio.sleep(10)
        await server.stop()
        check("BlessServer stopped cleanly", True)
    except Exception as e:
        check("BlessServer started + advertising", False, str(e))
        print("\n  Common fixes:")
        print("    sudo usermod -aG bluetooth $USER   (then re-login)")
        print("    sudo systemctl restart bluetooth")
        print("    sudo hciconfig hci0 up")
        return False
    return True

gatt_ok = asyncio.run(_test_gatt())

# ── Summary ─────────────────────────────────────────────────────────────────────
print("\n=== Summary ===")
if gatt_ok:
    print("  All checks passed.")
    print("  If the device STILL doesn't appear in Flutter scan:")
    print("    - Make sure Flutter scans for Service UUID, not just device name")
    print(f"    - Service UUID to filter on: {SERVICE_UUID}")
    print("    - Try restarting Bluetooth on the phone")
else:
    print("  Fix the errors above and re-run this script.")
