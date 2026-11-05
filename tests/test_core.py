from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from inkcal.app import PairCode
from inkcal.google import DemoCalendar, decode_state, encode_state, parse_event
from inkcal.models import Event, dedupe, events_on
from inkcal.render import RenderContext, render_view, screens, to_planes
from inkcal.render.canvas import BLACK, RED, WHITE
from inkcal.settings import in_quiet_hours

TZ = ZoneInfo("Europe/Warsaw")


def _events(now):
    return DemoCalendar().events([], now - timedelta(days=40), now + timedelta(days=40), TZ)


@pytest.mark.parametrize("view", ["month", "week", "agenda"])
@pytest.mark.parametrize("theme", ["classic", "mono", "bold"])
@pytest.mark.parametrize("day", [date(2026, 1, 17), date(2026, 8, 31), date(2026, 2, 1), date(2026, 12, 31)])
def test_views_render_three_colours(view, theme, day):
    now = datetime(day.year, day.month, day.day, 9, 0, tzinfo=TZ)
    img = render_view(RenderContext(now=now, events=_events(now), view=view, theme=theme, host="calendar-x.local"))
    assert img.size == (800, 480)
    colours = {c for _, c in img.getcolors(1 << 16)}
    assert colours <= {WHITE, BLACK, RED}, colours
    if theme == "mono":
        assert RED not in colours


def test_planes_are_disjoint():
    img = screens.welcome("Calendar-ABCD", "k7m2p9xa")
    black, red = to_planes(img)
    assert black.mode == red.mode == "1"
    b, r = black.load(), red.load()
    for y in range(0, 480, 3):
        for x in range(0, 800, 3):
            assert not (b[x, y] == 0 and r[x, y] == 0)


def test_all_day_and_timed_parsing():
    ad = parse_event({"summary": "Trip", "start": {"date": "2026-01-10"}, "end": {"date": "2026-01-13"}}, TZ)
    assert ad.all_day and ad.days() == [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)]
    t = parse_event({"summary": "Call", "start": {"dateTime": "2026-01-10T08:00:00Z"},
                     "end": {"dateTime": "2026-01-10T09:00:00Z"}}, TZ)
    assert t.start.hour == 9 and not t.all_day  # UTC -> Warsaw
    assert parse_event({"status": "cancelled", "start": {"date": "2026-01-10"}}, TZ) is None
    declined = {"summary": "x", "start": {"date": "2026-01-10"}, "end": {"date": "2026-01-11"},
                "attendees": [{"self": True, "responseStatus": "declined"}]}
    assert parse_event(declined, TZ) is None


def test_dedupe_and_events_on():
    s = datetime(2026, 1, 10, 9, tzinfo=TZ)
    a = Event("Standup", s, s + timedelta(hours=1), calendar_id="a")
    b = Event("standup", s, s + timedelta(hours=1), calendar_id="b")
    ad = Event("Holiday", s.replace(hour=0), s.replace(hour=0) + timedelta(days=1), True)
    out = dedupe([a, b, ad])
    assert len(out) == 2
    assert events_on(out, date(2026, 1, 10))[0].all_day


def test_state_roundtrip():
    st = encode_state("abc123", "http://192.168.1.23:8080")
    assert decode_state(st) == {"nonce": "abc123", "base": "http://192.168.1.23:8080"}


def test_quiet_hours_wrap():
    assert in_quiet_hours(time(23, 30), time(23), time(6))
    assert in_quiet_hours(time(5, 59), time(23), time(6))
    assert not in_quiet_hours(time(6), time(23), time(6))
    assert in_quiet_hours(time(13), time(12), time(14))


def test_pair_code_lockout():
    changed = []
    pc = PairCode(on_change=lambda: changed.append(1))
    first = pc.value
    assert pc.check(first[:3] + " " + first[3:])
    for _ in range(PairCode.MAX_FAILURES):
        pc.check("not-it")
    assert pc.value != first and changed
