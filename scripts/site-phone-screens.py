"""Capture the calendar's own phone pages (Wi-Fi setup, link code, settings) as iPhone-width PNGs for the site.

Renders the real Flask templates against a throwaway dev device with demo data, then screenshots them with
headless Chrome at 390 CSS px, 2x. Output: site/public/phone/{wifi,link,settings}.png

    .venv/bin/python scripts/site-phone-screens.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from inkcal.app import App  # noqa: E402
from inkcal.display import PngDisplay  # noqa: E402
from inkcal.network import FakeNetwork  # noqa: E402
from inkcal.storage import Paths  # noqa: E402
from inkcal.web import create_web  # noqa: E402

OUT = ROOT / "site" / "public" / "phone"
CSS = (ROOT / "inkcal" / "web" / "static" / "style.css").read_text()
PANEL = ROOT / "site" / "public" / "screens" / "view-month-classic.png"
WIDTH, SCALE = 390, 2
CHROME = next((p for p in (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
) if p and Path(p).exists()), None)


def standalone(html: str, tmp: Path) -> str:
    """Inline the stylesheet, point the live preview at a real render, drop scripts."""
    html = re.sub(r'<link rel="stylesheet"[^>]*>', f"<style>{CSS}</style>", html)
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    return html.replace('src="/screen.png"', f'src="{PANEL.as_uri()}"')


def grab(app: App, path: str, mode: str) -> str:
    app.mode = mode
    web = create_web(app)
    client = web.test_client()
    with client.session_transaction() as s:
        s["epoch"] = app.settings.get("auth_epoch")
    r = client.get(path, headers={"Host": "localhost"})
    assert r.status_code == 200, (path, r.status_code, r.headers.get("Location"))
    return r.get_data(as_text=True)


def shoot(html: str, name: str, tmp: Path) -> None:
    page = tmp / f"{name}.html"
    page.write_text(html)
    # Headless Chrome won't make a window narrower than 500 px, so frame the page at phone width.
    frame = tmp / f"{name}-frame.html"
    frame.write_text(f'<body style="margin:0"><iframe src="{page.as_uri()}" '
                     f'style="width:{WIDTH}px;height:3400px;border:0;display:block"></iframe>')
    png = tmp / f"{name}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--allow-file-access-from-files", f"--force-device-scale-factor={SCALE}",
                    "--window-size=500,3400", "--virtual-time-budget=3000",
                    f"--screenshot={png}", frame.as_uri()],
                   check=True, capture_output=True)
    img = Image.open(png).convert("RGB").crop((0, 0, WIDTH * SCALE, 3400 * SCALE))
    # Trim the empty page background below the content.
    bg = img.getpixel((2, img.height - 2))
    px = img.load()
    bottom = img.height - 1
    while bottom > 0 and all(px[x, bottom] == bg for x in range(0, img.width, 4)):
        bottom -= 1
    img = img.crop((0, 0, img.width, min(img.height, bottom + 40 * SCALE)))
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{name}.png", optimize=True)
    print(OUT / f"{name}.png", img.size)


def main() -> None:
    if not CHROME:
        sys.exit("Google Chrome or Chromium is needed for screenshots.")
    if not PANEL.exists():
        sys.exit("Run scripts/site-screens.sh first.")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        paths = Paths(str(tmp / "data"), str(tmp / "etc"))
        app = App(paths, PngDisplay(paths.screen_png), FakeNetwork(), demo=True, port=80)
        app.settings.update(device_name="Kitchen calendar")
        app.ident["hostname"] = "calendar-7f3a"  # same unit as the panel renders

        # Settings: a linked device with demo calendars, just synced.
        src = app.source()
        app.calendars = src.calendars()
        app.last_sync, app.last_sync_ok = datetime.now().replace(hour=8, minute=42), 0.0
        shoot(standalone(grab(app, "/settings", "run"), tmp), "settings", tmp)

        # Wi-Fi picker, as the phone sees it right after scanning the QR code.
        app.scan_cache = app.net.scan()
        shoot(standalone(grab(app, "/wifi", "setup"), tmp), "wifi", tmp)

        # Link step: an unlinked device asking for the code on its screen.
        # Typed in the code the panel's link screen shows (482913).
        app.demo, app.mode = False, "link"
        r = create_web(app).test_client().get("/link", headers={"Host": "localhost"})
        assert r.status_code == 200, r.status_code
        html = r.get_data(as_text=True).replace('name="code"', 'name="code" value="482 913"')
        shoot(standalone(html, tmp), "link", tmp)


if __name__ == "__main__":
    main()
