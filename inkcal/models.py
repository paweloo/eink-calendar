from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable, List


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime          # timezone-aware, device-local
    end: datetime            # exclusive
    all_day: bool = False
    location: str = ""
    calendar_id: str = field(default="", compare=False)

    def days(self) -> List[date]:
        """Every local date this event touches."""
        last = (self.end - timedelta(microseconds=1)).date() if self.end > self.start else self.start.date()
        out, d = [], self.start.date()
        while d <= last:
            out.append(d)
            d += timedelta(days=1)
        return out

    def on(self, day: date) -> bool:
        return day in self.days()


def sort_key(e: Event):
    return (e.start.date(), not e.all_day, e.start, e.title.lower())


def events_on(events: Iterable[Event], day: date) -> List[Event]:
    return sorted((e for e in events if e.on(day)), key=lambda e: (not e.all_day, e.start, e.title.lower()))


def dedupe(events: Iterable[Event]) -> List[Event]:
    """Same event shared into several calendars shows up once."""
    seen, out = set(), []
    for e in sorted(events, key=sort_key):
        key = (e.title.strip().lower(), e.start, e.end, e.all_day)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out
