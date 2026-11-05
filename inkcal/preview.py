"""Render every screen with demo data into PNG files (exactly what the panel shows)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .google import DemoCalendar, zone
from .render import RenderContext, compose, render_view, screens, to_planes


def render_all(out_dir: str, when: Optional[datetime] = None, theme: str = "classic") -> list:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tz = zone("Europe/Warsaw")
    now = when or datetime.now(tz)
    demo = DemoCalendar()
    events = demo.events([], now - timedelta(days=40), now + timedelta(days=40), tz)
    images = {}
    for view in ("month", "week", "agenda"):
        ctx = RenderContext(now=now, events=events, view=view, theme=theme, updated=now,
                            host="calendar-7f3a.local")
        t = time.perf_counter()
        images[f"view-{view}"] = render_view(ctx)
        print(f"{view:8s} rendered in {(time.perf_counter() - t) * 1000:.0f} ms")
    images["screen-welcome"] = screens.welcome("Calendar-7F3A", "k7m2p9xa", theme)
    images["screen-link"] = screens.link("http://192.168.1.23", "482913", "Home-5G", theme)
    images["screen-ready"] = screens.ready("you@gmail.com", "calendar-7f3a.local", "Kitchen calendar", theme)
    images["screen-message"] = screens.message(
        "Couldn’t join Home-5G", "The password may be wrong. The setup Wi-Fi is back on: "
        "scan the code again and pick your network.", "Calendar-7F3A · password k7m2p9xa", theme)
    written = []
    for name, img in images.items():
        black, red = to_planes(img)
        path = out / f"{name}-{theme}.png"
        compose(black, red).save(path)
        written.append(str(path))
    return written
