"""Where the device keeps its files, and small JSON helpers.

Layout (on the Pi):
  /etc/inkcal/google_client.json   OAuth client, installed at the factory (same on every device)
  /var/lib/inkcal/device.json      identity of this unit (created on first boot)
  /var/lib/inkcal/settings.json    user settings
  /var/lib/inkcal/token.json       Google tokens of the linked account
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional


class Paths:
    def __init__(self, data_dir: Optional[str] = None, etc_dir: Optional[str] = None):
        self.data = Path(data_dir or os.environ.get("INKCAL_DATA") or _default_data())
        self.etc = Path(etc_dir or os.environ.get("INKCAL_ETC") or _default_etc(self.data))
        self.data.mkdir(parents=True, exist_ok=True)

    @property
    def device(self) -> Path:
        return self.data / "device.json"

    @property
    def settings(self) -> Path:
        return self.data / "settings.json"

    @property
    def token(self) -> Path:
        return self.data / "token.json"

    @property
    def google_client(self) -> Path:
        return self.etc / "google_client.json"

    @property
    def screen_png(self) -> Path:
        return self.data / "screen.png"


def _default_data() -> str:
    if Path("/var/lib/inkcal").is_dir():
        return "/var/lib/inkcal"
    return str(Path.cwd() / ".dev-data")


def _default_etc(data: Path) -> str:
    if Path("/etc/inkcal").is_dir():
        return "/etc/inkcal"
    return str(data)


def load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data: Any, mode: int = 0o600) -> None:
    """Atomic write so a power cut never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
