"""User settings, editable from the web UI."""
from __future__ import annotations

import copy
import threading
from datetime import time
from typing import Any, Dict

from .storage import Paths, load_json, save_json

VIEWS = ("month", "week", "agenda")
THEMES = {
    "classic": "Classic: red accents",
    "mono": "Mono: black only",
    "bold": "Bold: inverted header",
    "dark": "Dark: white on black, red accents",
}
REFRESH_CHOICES = (5, 15, 30, 60)

DEFAULTS: Dict[str, Any] = {
    "device_name": "E-ink calendar",
    "view": "month",
    "theme": "classic",
    "week_start": 0,          # 0 = Monday, 6 = Sunday
    "clock_24h": True,
    "refresh_minutes": 15,
    "quiet_enabled": True,
    "quiet_start": "23:00",
    "quiet_end": "06:00",
    "calendars": None,        # None = calendars selected in Google; else list of ids
    "timezone": None,         # filled from the Google account
    "auth_epoch": 1,          # bump to log out every paired browser
}


class Settings:
    def __init__(self, paths: Paths):
        self._paths = paths
        self._lock = threading.Lock()
        stored = load_json(paths.settings, {}) or {}
        self._data = {**DEFAULTS, **{k: v for k, v in stored.items() if k in DEFAULTS}}

    def get(self, key: str) -> Any:
        with self._lock:
            return copy.deepcopy(self._data[key])

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    def update(self, **changes: Any) -> None:
        with self._lock:
            for key, value in changes.items():
                if key not in DEFAULTS:
                    raise KeyError(key)
                self._data[key] = value
            save_json(self._paths.settings, self._data)

    def reset(self) -> None:
        with self._lock:
            epoch = self._data.get("auth_epoch", 1)
            self._data = {**DEFAULTS, "auth_epoch": epoch + 1}
            save_json(self._paths.settings, self._data)


def parse_hhmm(value: str) -> time:
    hh, mm = value.strip().split(":")
    return time(int(hh), int(mm))


def in_quiet_hours(now: time, start: time, end: time) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end  # wraps past midnight
