"""Drawing helpers for a 3-colour (black / white / red) e-paper panel.

Everything is drawn with anti-aliasing OFF, so each pixel is exactly one of the
three panel colours. That makes text crisp on e-ink and makes splitting the
image into the panel's black and red planes trivial and fast.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFont

WIDTH, HEIGHT = 800, 480
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (215, 38, 30)

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
FAMILIES = {"inter": "Inter.ttf", "archivo": "Archivo.ttf"}

Color = Tuple[int, int, int]


@lru_cache(maxsize=128)
def font(family: str, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONT_DIR, FAMILIES[family])
    try:
        f = ImageFont.truetype(path, size)
    except OSError:
        try:
            return ImageFont.load_default(size)  # Pillow >= 10.1
        except TypeError:
            return ImageFont.load_default()
    try:
        values = []
        for axis in f.get_variation_axes():
            name = axis.get("name", b"")
            name = name.decode() if isinstance(name, bytes) else str(name)
            name = name.lower()
            if "weight" in name:
                v = weight
            elif "optical" in name:
                v = size
            else:
                v = axis.get("default", axis["minimum"])
            values.append(max(axis["minimum"], min(axis["maximum"], v)))
        f.set_variation_by_axes(values)
    except Exception:  # noqa: BLE001 - static font or FreeType without variations
        pass
    return f


class Canvas:
    def __init__(self, accent: Color = RED, background: Color = WHITE):
        self.img = Image.new("RGB", (WIDTH, HEIGHT), background)
        self.d = ImageDraw.Draw(self.img)
        self.d.fontmode = "1"  # no anti-aliasing
        self.accent = accent

    # -- text -----------------------------------------------------------------
    def text(self, xy, s: str, f, fill: Color = BLACK, anchor: str = "ls") -> None:
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor)

    def width(self, s: str, f) -> int:
        return int(self.d.textlength(s, font=f))

    def fit(self, s: str, f, max_w: int) -> str:
        if self.width(s, f) <= max_w:
            return s
        while s and self.width(s + "…", f) > max_w:
            s = s[:-1]
        return s.rstrip() + "…"

    def wrap(self, s: str, f, max_w: int, max_lines: int) -> List[str]:
        words = s.split()
        lines: List[str] = []
        i = 0
        while i < len(words) and len(lines) < max_lines:
            cur = words[i]
            i += 1
            while i < len(words) and self.width(cur + " " + words[i], f) <= max_w:
                cur += " " + words[i]
                i += 1
            lines.append(cur)
        if i < len(words) and lines:  # text left over: ellipsize the last line
            lines[-1] = self.fit(lines[-1] + " " + " ".join(words[i:]), f, max_w)
        return [self.fit(line, f, max_w) for line in lines] or [""]

    # -- shapes ---------------------------------------------------------------
    def rect(self, box, fill: Optional[Color] = None, outline: Optional[Color] = None, width: int = 1) -> None:
        self.d.rectangle(box, fill=fill, outline=outline, width=width)

    def hline(self, x0: int, x1: int, y: int, width: int = 1, fill: Color = BLACK) -> None:
        self.d.rectangle((x0, y, x1, y + width - 1), fill=fill)

    def vline(self, x: int, y0: int, y1: int, width: int = 1, fill: Color = BLACK) -> None:
        self.d.rectangle((x, y0, x + width - 1, y1), fill=fill)

    def circle(self, cx: int, cy: int, r: int, fill: Optional[Color] = None,
               outline: Optional[Color] = None, width: int = 1) -> None:
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=width)

    def qr(self, data: str, x: int, y: int, size: int) -> None:
        import qrcode
        q = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
        q.add_data(data)
        q.make(fit=True)
        m = q.get_matrix()
        n = len(m)
        cell = max(1, size // n)
        ox = x + (size - cell * n) // 2
        oy = y + (size - cell * n) // 2
        for r, row in enumerate(m):
            for c, on in enumerate(row):
                if on:
                    self.d.rectangle((ox + c * cell, oy + r * cell, ox + (c + 1) * cell - 1, oy + (r + 1) * cell - 1), fill=BLACK)

    def wifi_icon(self, x: int, y: int, fill: Color = BLACK) -> None:
        """12x10 px Wi-Fi glyph, top-left at (x, y)."""
        cx, cy = x + 6, y + 10
        for r in (10, 7, 4):
            self.d.arc((cx - r, cy - r, cx + r, cy + r), 225, 315, fill=fill, width=2)
        self.d.rectangle((cx - 1, cy - 2, cx, cy - 1), fill=fill)


def to_planes(img: Image.Image) -> Tuple[Image.Image, Image.Image]:
    """Split an RGB render into the two 1-bit planes the panel wants (0 = ink)."""
    r, g, _ = img.convert("RGB").split()
    redness = ImageChops.multiply(r.point(lambda v: 255 if v > 150 else 0),
                                  g.point(lambda v: 255 if v < 110 else 0))
    dark = img.convert("L").point(lambda v: 255 if v < 128 else 0)
    black_ink = ImageChops.subtract(dark, redness)
    black = ImageChops.invert(black_ink).convert("1")
    red = ImageChops.invert(redness).convert("1")
    return black, red


def compose(black: Image.Image, red: Image.Image) -> Image.Image:
    """What the panel will actually show, for previews and the web UI."""
    out = Image.new("RGB", black.size, WHITE)
    out.paste(BLACK, mask=ImageChops.invert(black.convert("L")))
    out.paste(RED, mask=ImageChops.invert(red.convert("L")))
    return out
