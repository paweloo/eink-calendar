"""Wi-Fi control through NetworkManager (nmcli), the default on Raspberry Pi OS Bookworm.

The Pi Zero 2 W has one radio: it is EITHER a hotspot (setup) OR a client of the
home network. So we scan before starting the hotspot and keep that list.
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

HOTSPOT_CON = "inkcal-hotspot"
HOTSPOT_IP = "10.42.0.1"
IFACE = "wlan0"


class NetworkError(Exception):
    pass


def _split(line: str) -> List[str]:
    """nmcli -t escapes ':' inside values as '\\:'."""
    return [p.replace("\\:", ":") for p in re.split(r"(?<!\\):", line)]


class NetworkManager:
    def _nmcli(self, *args: str, timeout: int = 30, check: bool = True) -> str:
        cmd = ["nmcli", *args]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise NetworkError(f"timeout: {' '.join(args[:3])}") from e
        if check and res.returncode != 0:
            raise NetworkError((res.stderr or res.stdout).strip() or f"nmcli failed ({res.returncode})")
        return res.stdout

    # -- state ------------------------------------------------------------------
    def online(self) -> bool:
        try:
            out = self._nmcli("-t", "networking", "connectivity", "check", timeout=15).strip()
            return out == "full"
        except NetworkError:
            return False

    def current_ssid(self) -> Optional[str]:
        try:
            out = self._nmcli("-t", "-f", "ACTIVE,SSID", "dev", "wifi", "list", "--rescan", "no")
        except NetworkError:
            return None
        for line in out.splitlines():
            parts = _split(line)
            if parts and parts[0] == "yes" and len(parts) > 1:
                return parts[1] or None
        return None

    def saved_wifi(self) -> List[str]:
        out = self._nmcli("-t", "-f", "NAME,TYPE", "con", "show", check=False)
        names = []
        for line in out.splitlines():
            parts = _split(line)
            if len(parts) >= 2 and parts[1] == "802-11-wireless" and parts[0] != HOTSPOT_CON:
                names.append(parts[0])
        return names

    def hotspot_active(self) -> bool:
        out = self._nmcli("-t", "-f", "NAME", "con", "show", "--active", check=False)
        return HOTSPOT_CON in out.splitlines()

    # -- actions ----------------------------------------------------------------
    def scan(self) -> List[Dict]:
        out = self._nmcli("-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes",
                          timeout=40, check=False)
        best: Dict[str, Dict] = {}
        for line in out.splitlines():
            parts = _split(line)
            if len(parts) < 3 or not parts[0]:
                continue
            ssid, signal, sec = parts[0], int(parts[1] or 0), parts[2]
            if ssid not in best or signal > best[ssid]["signal"]:
                best[ssid] = {"ssid": ssid, "signal": signal, "secure": bool(sec and sec != "--")}
        return sorted(best.values(), key=lambda n: -n["signal"])

    def start_hotspot(self, ssid: str, password: str) -> None:
        self._nmcli("con", "delete", HOTSPOT_CON, check=False)
        self._nmcli(
            "con", "add", "type", "wifi", "ifname", IFACE, "con-name", HOTSPOT_CON,
            "autoconnect", "no", "ssid", ssid,
            "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
            "ipv4.method", "shared", "ipv4.addresses", f"{HOTSPOT_IP}/24",
            "ipv6.method", "disabled",
            "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password,
            "wifi-sec.proto", "rsn", "wifi-sec.pairwise", "ccmp", "wifi-sec.group", "ccmp",
            # The Zero 2 W's brcmfmac chip mishandles protected management frames in AP mode:
            # phones then report "couldn't join" even with the right password.
            "wifi-sec.pmf", "disable",
            # A fixed, universally allowed 2.4 GHz channel instead of whatever the driver picks.
            "802-11-wireless.channel", "6",
        )
        self._nmcli("con", "up", HOTSPOT_CON, timeout=40)
        log.info("hotspot %s up", ssid)

    def stop_hotspot(self) -> None:
        self._nmcli("con", "down", HOTSPOT_CON, check=False)

    def connect(self, ssid: str, password: str) -> bool:
        """Create (or replace) a saved network and bring it up. Returns True on success."""
        name = f"wifi-{ssid}"
        self._nmcli("con", "delete", name, check=False)
        args = ["con", "add", "type", "wifi", "ifname", IFACE, "con-name", name, "ssid", ssid,
                "connection.autoconnect", "yes", "connection.autoconnect-priority", "10"]
        if password:
            args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
        self._nmcli(*args)
        self.stop_hotspot()
        time.sleep(2)
        try:
            self._nmcli("--wait", "45", "con", "up", name, timeout=60)
        except NetworkError as e:
            log.warning("could not join %s: %s", ssid, e)
            self._nmcli("con", "delete", name, check=False)
            return False
        for _ in range(15):
            if self.online():
                return True
            time.sleep(2)
        return self.current_ssid() == ssid

    def forget_all(self) -> None:
        for name in self.saved_wifi():
            self._nmcli("con", "delete", name, check=False)


class FakeNetwork:
    """For development on a laptop: pretends to be online with a home network."""

    def __init__(self, online: bool = True):
        self._online = online
        self._ssid: Optional[str] = "Home-5G" if online else None
        self._hotspot = False

    def online(self) -> bool:
        return self._online

    def current_ssid(self) -> Optional[str]:
        return self._ssid

    def saved_wifi(self) -> List[str]:
        return [f"wifi-{self._ssid}"] if self._ssid else []

    def hotspot_active(self) -> bool:
        return self._hotspot

    def scan(self) -> List[Dict]:
        return [{"ssid": "Home-5G", "signal": 82, "secure": True},
                {"ssid": "Home-2.4G", "signal": 70, "secure": True},
                {"ssid": "Neighbour_Net", "signal": 40, "secure": True},
                {"ssid": "Cafe Guest", "signal": 22, "secure": False}]

    def start_hotspot(self, ssid: str, password: str) -> None:
        self._hotspot, self._online = True, False
        log.info("[fake] hotspot %s / %s", ssid, password)

    def stop_hotspot(self) -> None:
        self._hotspot = False

    def connect(self, ssid: str, password: str) -> bool:
        time.sleep(1)
        ok = password != "wrong"
        self._hotspot = False
        self._online, self._ssid = ok, (ssid if ok else None)
        return ok

    def forget_all(self) -> None:
        self._ssid, self._online = None, False
