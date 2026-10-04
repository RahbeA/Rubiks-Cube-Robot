"""Optional USB serial output to an Arduino (pyserial)."""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_port: Any = None
_port_name = ""


def list_ports() -> list[str]:
    try:
        import serial.tools.list_ports
    except ImportError:
        return []
    devices = sorted({port.device for port in serial.tools.list_ports.comports()})
    # Prefer call-out devices on macOS (work better for writing than tty.*).
    cu_first = [device for device in devices if "/cu." in device]
    rest = [device for device in devices if device not in cu_first]
    return cu_first + rest


DEFAULT_BAUD = 115200


def connect(port: str, baud: int = DEFAULT_BAUD) -> None:
    global _port, _port_name
    try:
        import serial
    except ImportError as error:
        raise RuntimeError("pyserial is not installed. Run: pip install pyserial") from error

    disconnect()

    try:
        candidate = serial.Serial(
            port,
            baud,
            timeout=1,
            write_timeout=3,
        )
    except serial.SerialException as error:
        raise RuntimeError(
            f"Could not open {port}. Close the Arduino Serial Monitor and any other app "
            f"using this port, then try again. ({error})"
        ) from error

    # Avoid long reset/boot glitches on some boards.
    candidate.dtr = False
    candidate.rts = False

    with _lock:
        _port = candidate
        _port_name = port


def disconnect() -> None:
    global _port, _port_name
    with _lock:
        if _port is not None:
            try:
                _port.close()
            except OSError:
                pass
        _port = None
        _port_name = ""


def status() -> dict[str, Any]:
    ports = list_ports()
    with _lock:
        return {
            "connected": _port is not None and getattr(_port, "is_open", False),
            "port": _port_name,
            "available_ports": ports,
            "recommended_port": next(
                (device for device in ports if "usbmodem" in device.lower()),
                ports[0] if ports else "",
            ),
        }


def send_line(text: str) -> None:
    with _lock:
        if _port is None or not getattr(_port, "is_open", False):
            raise RuntimeError("Serial port is not connected.")
        payload = (text.rstrip() + "\n").encode("utf-8")
        _port.write(payload)
        _port.flush()


def send_moves(moves: list[str], *, one_per_line: bool = False) -> None:
    """Send one space-separated line so firmware can turn opposite faces together."""
    cleaned = [move.strip() for move in moves if move.strip()]
    if not cleaned:
        return
    if one_per_line:
        import time

        for move in cleaned:
            send_line(move)
            time.sleep(0.05)
        return
    send_line(" ".join(cleaned))
