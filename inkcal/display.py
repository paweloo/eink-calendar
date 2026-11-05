"""Display back-ends: the real Waveshare panel, or PNG files for development."""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Optional

from PIL import Image

from .render import compose, to_planes

log = logging.getLogger(__name__)


class Display:
    """Base class: skips refreshes when the picture did not change (e-ink refresh
    of a 3-colour panel takes ~15-20 s and flashes, so we only do it when needed)."""

    def __init__(self, preview_path: Optional[Path] = None):
        self._last_hash: Optional[str] = None
        self._lock = threading.Lock()
        self.preview_path = preview_path

    def show(self, img: Image.Image, force: bool = False) -> bool:
        black, red = to_planes(img)
        digest = hashlib.sha1(black.tobytes() + red.tobytes()).hexdigest()
        with self._lock:
            if not force and digest == self._last_hash:
                log.debug("screen unchanged, skipping refresh")
                return False
            if self.preview_path:
                compose(black, red).save(self.preview_path)
            t = time.monotonic()
            self._push(black, red)
            log.info("display refreshed in %.1f s", time.monotonic() - t)
            self._last_hash = digest
            return True

    def _push(self, black: Image.Image, red: Image.Image) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        self.show(Image.new("RGB", (800, 480), (255, 255, 255)), force=True)


class PngDisplay(Display):
    """Development: writes the panel image to a PNG (open it in Preview, it auto-reloads)."""

    def _push(self, black: Image.Image, red: Image.Image) -> None:
        log.info("screen written to %s", self.preview_path)


class WaveshareDisplay(Display):
    """Waveshare 7.5" e-Paper HAT (B) V2, 800x480 black/white/red."""

    def _push(self, black: Image.Image, red: Image.Image) -> None:
        from .vendor.waveshare_epd import epd7in5b_V2

        epd = epd7in5b_V2.EPD()
        try:
            epd.init()
            epd.display(epd.getbuffer(black), epd.getbuffer(red))
        finally:
            epd.sleep()  # never leave the panel powered: high voltage damages it over time
