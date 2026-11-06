"""Calendar views: month (default), week, agenda. 800x480, black/white/red."""
from __future__ import annotations

import calendar as pycal
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional

from PIL import Image

from ..models import Event, events_on
from .canvas import BLACK, HEIGHT, WHITE, WIDTH, Canvas, font, palette

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DOW = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class RenderContext:
    now: datetime                       # timezone-aware, local
    events: List[Event] = field(default_factory=list)
    view: str = "month"
    theme: str = "classic"              # classic | mono | bold | dark
    week_start: int = 0                 # 0 = Monday
    clock_24h: bool = True
    updated: Optional[datetime] = None
    host: str = ""
    offline: bool = False

    @property
    def accent(self):
        return palette(self.theme)[2]

    @property
    def today(self) -> date:
        return self.now.date()

    def hm(self, dt: datetime) -> str:
        if self.clock_24h:
            return dt.strftime("%H:%M")
        h = dt.hour % 12 or 12
        return f"{h}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"

    def when(self, e: Event) -> str:
        return "All day" if e.all_day else self.hm(e.start)

    def span(self, e: Event) -> str:
        if e.all_day:
            return "All day"
        return f"{self.hm(e.start)} – {self.hm(e.end)}"


def _footer(c: Canvas, ctx: RenderContext, x0: int, x1: int, y: int, fill=None) -> None:
    # No "updated HH:MM" when healthy: it would change every sync and force a ~20 s
    # e-ink refresh even when no event changed. Staleness is only shown when it matters.
    f = font("inter", 11, 500)
    if ctx.offline:
        stamp = ctx.hm(ctx.updated) if ctx.updated else "never"
        c.text((x0, y), f"Offline · last sync {stamp}", f, fill)
    if ctx.host and not ctx.offline:
        w = c.width(ctx.host, f)
        c.text((x1 - w, y), ctx.host, f, fill)
        c.wifi_icon(x1 - w - 18, y - 10, fill)


def _ongoing_or_next(ctx: RenderContext, evs: List[Event]) -> Optional[Event]:
    timed = [e for e in evs if not e.all_day and e.end > ctx.now]
    return min(timed, key=lambda e: e.start) if timed else None


# --------------------------------------------------------------------------- month

def month(ctx: RenderContext) -> Image.Image:
    c = Canvas(ctx.theme)
    A, INK, today = c.accent, c.ink, ctx.today
    bold = ctx.theme == "bold"

    # Header
    if bold:
        c.rect((0, 0, 499, 63), fill=BLACK)
    fg = WHITE if bold else INK
    year_col = (WHITE if A == BLACK else A) if bold else A
    title = MONTHS[today.month - 1].upper()
    yf = font("archivo", 32, 900)
    size = 48
    while size > 30 and c.width(title, font("archivo", size, 900)) + 14 + c.width(str(today.year), yf) > 476:
        size -= 2
    hf = font("archivo", size, 900)
    c.text((12, 52), title, hf, fg)
    c.text((12 + c.width(title, hf) + 14, 52), str(today.year), yf, year_col)

    # Weekday labels
    gx0, gw = 12, 476
    cw = gw / 7
    lf = font("inter", 12, 700)
    for i in range(7):
        c.text((gx0 + cw * i + cw / 2, 80), DOW[(ctx.week_start + i) % 7], lf, anchor="mm")

    # Grid
    weeks = pycal.Calendar(ctx.week_start).monthdatescalendar(today.year, today.month)
    top = 94
    rh = min(66, (HEIGHT - 4 - top) // len(weeks))
    r = min(28, rh // 2 - 3)
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    counts: Dict[date, int] = {}
    for e in ctx.events:
        for d in e.days():
            if month_start <= d < month_end:
                counts[d] = counts.get(d, 0) + 1

    nf, nf_b = font("inter", 19, 500), font("inter", 19, 700)
    for wi, week in enumerate(weeks):
        for di, d in enumerate(week):
            if d.month != today.month:
                continue
            cx = int(gx0 + cw * di + cw / 2)
            cy = int(top + rh * wi + rh / 2)
            n = min(counts.get(d, 0), 3)
            if d == today:
                c.circle(cx, cy, r, fill=A)
                num_col, dot_col, f = WHITE, WHITE, nf_b
            else:
                c.circle(cx, cy, r, outline=INK, width=1)
                num_col, dot_col, f = INK, A, nf
            c.text((cx, cy - (4 if n else 0)), str(d.day), f, num_col, anchor="mm")
            if n:
                total = n * 5 + (n - 1) * 3
                x = cx - total // 2
                for _ in range(n):
                    c.d.ellipse((x, cy + 11, x + 4, cy + 15), fill=dot_col)
                    x += 8

    # Right panel
    c.vline(500, 0, HEIGHT - 1)
    px, pw = 523, 255
    c.text((px, 27), "TODAY", font("inter", 13, 700), A)
    c.text((px - 4, 108), str(today.day), font("archivo", 92, 900))
    c.text((px, 142), DAY_NAMES[today.weekday()], font("inter", 24, 500))
    c.hline(px, px + pw, 158, 2)
    c.text((px, 184), "SCHEDULE", font("inter", 11, 700))

    y = 198
    todays = events_on(ctx.events, today)
    nxt = _ongoing_or_next(ctx, todays)
    tf, ttl = font("inter", 12, 700), font("inter", 15, 600)
    if not todays:
        c.rect((px, y, px + 2, y + 20), fill=A)
        c.text((px + 13, y + 15), "No events today", font("inter", 15, 700))
        y += 34
    for i, e in enumerate(todays):
        if y > 320:
            c.text((px + 13, y + 12), f"+{len(todays) - i} more today", tf)
            y += 22
            break
        c.rect((px, y, px + 2, y + 33), fill=A if e is nxt else INK)
        c.text((px + 13, y + 11), ctx.span(e), tf)
        c.text((px + 13, y + 30), c.fit(e.title, ttl, pw - 13), ttl)
        y += 44

    upcoming = sorted((e for e in ctx.events if today < e.start.date() <= today + timedelta(days=14)),
                      key=lambda e: (e.start, e.title))
    if upcoming and y < 400:
        y += 6
        c.text((px, y + 11), "COMING UP", font("inter", 11, 700))
        y += 20
        bf, rf = font("inter", 13, 700), font("inter", 13, 400)
        for e in upcoming:
            if y + 13 > 448:
                break
            d = e.start.date()
            c.text((px, y + 13), f"{DOW[d.weekday()]} {d.day}", bf)
            c.text((px + 62, y + 13), c.fit(f"{ctx.when(e)} · {e.title}", rf, pw - 62), rf)
            y += 21

    _footer(c, ctx, px, px + pw, 468)
    return c.img


# --------------------------------------------------------------------------- week

def week(ctx: RenderContext) -> Image.Image:
    c = Canvas(ctx.theme)
    A, INK, PAPER, today = c.accent, c.ink, c.paper, ctx.today
    bold = ctx.theme == "bold"
    start = today - timedelta(days=(today.weekday() - ctx.week_start) % 7)
    days = [start + timedelta(days=i) for i in range(7)]
    end = days[-1]

    if bold:
        c.rect((0, 0, WIDTH - 1, 69), fill=BLACK)
    fg = WHITE if bold else INK
    year_col = (WHITE if A == BLACK else A) if bold else A
    m0, m1 = MONTHS[start.month - 1][:3].upper(), MONTHS[end.month - 1][:3].upper()
    title = f"{m0} {start.day}–{end.day}" if m0 == m1 else f"{m0} {start.day} – {m1} {end.day}"
    hf = font("archivo", 48 if m0 == m1 else 40, 900)
    c.text((12, 52), title, hf, fg)
    c.text((12 + c.width(title, hf) + 14, 52), str(end.year), font("archivo", 32, 900), year_col)
    wk = f"WEEK {today.isocalendar()[1]}"
    wf = font("inter", 12, 700)
    c.text((WIDTH - 12 - c.width(wk, wf), 50), wk, wf, fg)
    if not bold:
        c.hline(12, WIDTH - 13, 68, 2)

    x0, gw = 12, WIDTH - 24
    cw = gw / 7
    bottom = 446
    hf_dow, hf_num = font("inter", 11, 700), font("archivo", 30, 900)
    tf, ttl, adf = font("inter", 11, 700), font("inter", 13, 600), font("inter", 12, 600)
    for i, d in enumerate(days):
        x = int(x0 + cw * i)
        xr = int(x0 + cw * (i + 1))
        if i:
            c.vline(x, 72, bottom + 2)
        col = INK
        if d == today:
            c.rect((x + 4, 76, xr - 4, 126), fill=A)
            col = WHITE
        c.text((x + 11, 93), DOW[d.weekday()], hf_dow, col)
        c.text((x + 10, 120), str(d.day), hf_num, col)

        y = 140
        inner = xr - x - 20
        evs = events_on(ctx.events, d)
        if not evs:
            c.text((x + 11, y + 12), "—", ttl)
        for k, e in enumerate(evs):
            if e.all_day:
                lines = c.wrap(e.title, adf, inner - 8, 2)
                h = 8 + 15 * len(lines)
            else:
                lines = c.wrap(e.title, ttl, inner, 2)
                h = 14 + 17 * len(lines)
            if y + h > bottom - (18 if k < len(evs) - 1 else 0):
                c.text((x + 11, y + 12), f"+{len(evs) - k} more", tf)
                break
            if e.all_day:
                c.rect((x + 8, y, xr - 8, y + h), fill=INK)
                for li, line in enumerate(lines):
                    c.text((x + 13, y + 16 + 15 * li), line, adf, PAPER)
            else:
                c.text((x + 11, y + 10), ctx.hm(e.start), tf)
                for li, line in enumerate(lines):
                    c.text((x + 11, y + 27 + 17 * li), line, ttl)
            y += h + 10

    c.hline(12, WIDTH - 13, 452)
    _footer(c, ctx, 12, WIDTH - 13, 470)
    return c.img


# --------------------------------------------------------------------------- agenda

def agenda(ctx: RenderContext) -> Image.Image:
    c = Canvas(ctx.theme)
    A, INK, today, now = c.accent, c.ink, ctx.today, ctx.now

    # Left: big date in white on a solid panel: red on classic, black elsewhere
    # (on the dark theme the black panel merges with the page, so draw a red divider)
    c.rect((0, 0, 259, HEIGHT - 1), fill=A if ctx.theme == "classic" else BLACK)
    if c.paper == BLACK:
        c.vline(259, 0, HEIGHT - 1, 2, A)
    c.text((22, 34), DAY_NAMES[today.weekday()].upper(), font("inter", 13, 700), WHITE)
    c.text((14, 150), str(today.day), font("archivo", 140, 900), WHITE)
    c.text((22, 190), f"{MONTHS[today.month - 1]} {today.year}", font("inter", 22, 500), WHITE)
    c.hline(22, 237, 210, 2, WHITE)

    soon = [e for e in ctx.events if e.end > now and e.start.date() <= today + timedelta(days=14)]
    timed = sorted((e for e in soon if not e.all_day), key=lambda e: e.start)
    nxt = timed[0] if timed else None
    label = "NOW" if nxt and nxt.start <= now else "NEXT UP"
    c.text((22, 238), label, font("inter", 11, 700), WHITE)
    if nxt:
        d = nxt.start.date()
        big = ctx.hm(nxt.start) if d == today else f"{DOW[d.weekday()][:3].title()} {d.day}"
        c.text((22, 274), big, font("archivo", 30, 900), WHITE)
        lines = c.wrap(nxt.title, font("inter", 17, 600), 216, 2)
        for i, line in enumerate(lines):
            c.text((22, 300 + 21 * i), line, font("inter", 17, 600), WHITE)
        sub = []
        if nxt.location:
            sub.append(nxt.location)
        sub.append(("until " + ctx.hm(nxt.end)) if d == today else ctx.span(nxt))
        c.text((22, 300 + 21 * len(lines) + 2), c.fit(" · ".join(sub), font("inter", 13), 216), font("inter", 13), WHITE)
    else:
        c.text((22, 270), "Nothing planned", font("inter", 17, 600), WHITE)
    _footer(c, ctx, 22, 237, 466, WHITE)

    # Right: next 14 days
    x0, x1 = 284, WIDTH - 24
    c.text((x0, 50), "UPCOMING", font("archivo", 32, 900))
    w = c.width("UPCOMING", font("archivo", 32, 900))
    c.text((x0 + w + 12, 50), "14 DAYS", font("archivo", 20, 900), A)
    c.hline(x0, x1, 60, 2)

    ef, eb = font("inter", 15, 500), font("inter", 15, 700)
    tcol = c.width("88:88" if ctx.clock_24h else "88:88 PM", eb) + 16
    tcol = max(tcol, c.width("All day", eb) + 16)
    y = 62
    shown = 0
    for i in range(15):
        d = today + timedelta(days=i)
        evs = [e for e in events_on(ctx.events, d) if d != today or e.all_day or e.end > now]
        if not evs:
            continue
        h = max(58, 18 + 22 * len(evs))
        if y + h > HEIGHT - 6:
            fit_n = (HEIGHT - 6 - y - 18) // 22
            if fit_n < 1:
                break
            evs = evs[:fit_n]
            h = max(58, 18 + 22 * len(evs))
            if y + h > HEIGHT - 6:
                break
        c.text((x0, y + 24), "TODAY" if d == today else DOW[d.weekday()], font("inter", 11, 700),
               A if d == today else INK)
        c.text((x0, y + 50), str(d.day), font("archivo", 26, 900), A if d == today else INK)
        for k, e in enumerate(evs):
            by = y + 30 + 22 * k
            c.text((x0 + 80, by), ctx.when(e), eb)
            c.text((x0 + 80 + tcol, by), c.fit(e.title, ef, x1 - x0 - 80 - tcol), ef)
        y += h
        c.hline(x0, x1, y - 1)
        shown += 1
    if not shown:
        c.text((x0, 100), "Nothing in the next two weeks.", font("inter", 17, 500))
    return c.img


VIEWS: Dict[str, Callable[[RenderContext], Image.Image]] = {"month": month, "week": week, "agenda": agenda}


def render_view(ctx: RenderContext) -> Image.Image:
    return VIEWS.get(ctx.view, month)(ctx)
