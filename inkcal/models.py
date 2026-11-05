from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo
from typing import Any, Dict, Iterable, List


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


def event_to_dict(e: Event) -> Dict[str, Any]:
    return {"title": e.title, "start": e.start.isoformat(), "end": e.end.isoformat(),
            "all_day": e.all_day, "location": e.location, "calendar_id": e.calendar_id}


def event_from_dict(d: Dict[str, Any], tz: tzinfo) -> Event:
    return Event(title=d["title"], start=datetime.fromisoformat(d["start"]).astimezone(tz),
                 end=datetime.fromisoformat(d["end"]).astimezone(tz), all_day=bool(d.get("all_day")),
                 location=d.get("location", ""), calendar_id=d.get("calendar_id", ""))


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
