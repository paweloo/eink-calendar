"""Identity of one physical unit: serial, hostname, setup-hotspot credentials.

Created once, on first boot, so every card cloned from the same golden image
ends up with its own name and its own setup Wi-Fi password.
"""
from __future__ import annotations

import hashlib
import secrets
import socket
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Optional

from .storage import Paths, load_json, save_json

# No 0/O, 1/l/i: the password is typed from the screen when a phone can't scan QR codes.
_PW_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def read_serial() -> str:
    for path in ("/proc/device-tree/serial-number", "/sys/firmware/devicetree/base/serial-number"):
        try:
            value = Path(path).read_bytes().strip(b"\x00\n ").decode()
            if value:
                return value
        except OSError:
            pass
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("serial"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    # Not a Pi (development): stable per machine.
    return hashlib.sha1(str(uuid.getnode()).encode()).hexdigest()[:16]


def create_identity(serial: Optional[str] = None) -> Dict[str, str]:
    serial = serial or read_serial()
    short = serial[-4:].upper()
    return {
        "serial": serial,
        "short_id": short,
        "hostname": f"calendar-{short.lower()}",
        "hotspot_ssid": f"Calendar-{short}",
        "hotspot_password": "".join(secrets.choice(_PW_ALPHABET) for _ in range(8)),
        "secret_key": secrets.token_hex(32),
    }


def load_or_create_identity(paths: Paths) -> Dict[str, str]:
    ident = load_json(paths.device)
    if not ident:
        ident = create_identity()
        save_json(paths.device, ident)
    return ident


def local_ip() -> Optional[str]:
    """IP of the interface that routes to the internet / LAN (no packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()


def clock_synced() -> bool:
    """True once systemd-timesyncd has set the clock from the internet.

    The Pi has no battery-backed clock: after a power cut it boots with the last saved time
    (possibly days old) until NTP answers. Not a systemd machine (a Mac): always True.
    """
    try:
        res = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return True
    if res.returncode != 0:
        return True
    return res.stdout.strip() == "yes"
