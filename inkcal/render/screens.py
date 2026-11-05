"""Full-screen states shown outside the normal calendar views."""
from __future__ import annotations

from PIL import Image

from .canvas import BLACK, HEIGHT, RED, WHITE, WIDTH, Canvas, font


def _accent(theme: str):
    return BLACK if theme == "mono" else RED


def _step(c: Canvas, n: int, text: str, y: int, active: bool) -> None:
    if active:
        c.circle(55, y, 15, fill=c.accent)
        c.text((55, y), str(n), font("inter", 15, 700), WHITE, anchor="mm")
    else:
        c.circle(55, y, 15, outline=BLACK, width=2)
        c.text((55, y), str(n), font("inter", 15, 700), BLACK, anchor="mm")
    for i, line in enumerate(c.wrap(text, font("inter", 16), 360, 2)):
        c.text((84, y + 6 + 21 * i), line, font("inter", 16))


def welcome(ssid: str, password: str, theme: str = "classic") -> Image.Image:
    c = Canvas(accent=_accent(theme))
    hf = font("archivo", 96, 900)
    c.text((36, 106), "Hello", hf)
    c.text((36 + c.width("Hello", hf), 106), ".", hf, c.accent)
    c.text((40, 150), "Let’s set up your calendar.", font("inter", 24, 500))
    _step(c, 1, "Scan the code with your phone to join the setup Wi-Fi.", 214, True)
    _step(c, 2, "A setup page opens. Pick your home Wi-Fi.", 284, False)
    _step(c, 3, "Link your Google account. That’s it.", 354, False)

    c.vline(512, 40, HEIGHT - 40)
    c.qr(f"WIFI:T:WPA;S:{_esc(ssid)};P:{_esc(password)};;", 556, 56, 200)
    c.text((656, 296), "OR JOIN MANUALLY", font("inter", 11, 700), anchor="ms")
    lf, vf = font("inter", 14), font("inter", 14, 700)
    for i, (k, v) in enumerate((("Network", ssid), ("Password", password))):
        y = 326 + 24 * i
        c.text((552, y), k, lf)
        c.text((760 - c.width(v, vf), y), v, vf)
    return c.img


def link(url: str, code: str, wifi_name: str = "", theme: str = "classic",
         title: str = "Link your\nGoogle account",
         note: str = "Only someone who can see this screen can use the code.") -> Image.Image:
    c = Canvas(accent=_accent(theme))
    y = 44
    if wifi_name:
        c.d.line((40, 38, 45, 43, 54, 32), fill=BLACK, width=3)
        c.text((64, 45), f"Connected to {wifi_name}", font("inter", 14, 600))
        y = 62
    hf = font("archivo", 52, 900)
    lines = title.split("\n")
    for i, line in enumerate(lines):
        y += 50
        c.text((38, y), line, hf)
    y += 40
    for line in c.wrap("On a phone or laptop on the same Wi-Fi, scan the code or open", font("inter", 17), 420, 2):
        c.text((40, y), line, font("inter", 17))
        y += 23
    c.text((40, y + 10), url.replace("http://", ""), font("inter", 26, 700))

    c.text((40, 362), "THEN ENTER THIS CODE", font("inter", 11, 700))
    x = 40
    df = font("archivo", 36, 900)
    for i, ch in enumerate(code):
        c.rect((x, 374, x + 49, 435), outline=c.accent, width=2)
        c.text((x + 25, 405), ch, df, anchor="mm")
        x += 58 + (14 if i == 2 else 0)

    c.vline(536, 40, HEIGHT - 40)
    c.qr(url, 568, 100, 200)
    for i, line in enumerate(c.wrap(note, font("inter", 13), 200, 3)):
        c.text((668, 336 + 18 * i), line, font("inter", 13), anchor="ms")
    return c.img


def ready(email: str, host: str, device_name: str, theme: str = "classic") -> Image.Image:
    accent = _accent(theme)
    c = Canvas(accent=accent, background=accent)
    c.circle(76, 76, 31, outline=WHITE, width=5)
    c.d.line((60, 78, 71, 89, 92, 66), fill=WHITE, width=5)
    c.text((40, 210), "You’re all set.", font("archivo", 84, 900), WHITE)
    c.text((44, 262), c.fit(f"Fetching events from {email or 'your account'}…", font("inter", 22, 500), 700),
           font("inter", 22, 500), WHITE)
    c.text((44, 292), "Your calendar appears in a moment.", font("inter", 22, 500), WHITE)
    c.hline(44, WIDTH - 45, 386, 2, WHITE)
    c.text((44, 414), "SETTINGS ANY TIME", font("inter", 11, 700), WHITE)
    c.text((44, 442), host, font("inter", 20, 700), WHITE)
    df = font("inter", 14, 500)
    s = f"Device name: {device_name}"
    c.text((WIDTH - 45 - c.width(s, df), 442), s, df, WHITE)
    return c.img


def message(title: str, body: str, footer: str = "", theme: str = "classic") -> Image.Image:
    """Generic status screen: connecting, errors, factory reset, etc."""
    c = Canvas(accent=_accent(theme))
    c.rect((40, 60, 51, 71), fill=c.accent)
    tf = font("archivo", 52, 900)
    y = 130
    for line in c.wrap(title, tf, 720, 2):
        c.text((40, y), line, tf)
        y += 56
    y += 10
    for line in c.wrap(body, font("inter", 20), 680, 6):
        c.text((42, y), line, font("inter", 20))
        y += 28
    if footer:
        c.hline(40, WIDTH - 41, 420, 2)
        c.text((42, 450), footer, font("inter", 14, 600))
    return c.img


def _esc(s: str) -> str:
    for ch in "\\;,:\"":
        s = s.replace(ch, "\\" + ch)
    return s
