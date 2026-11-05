"""What happens when the device is unplugged and plugged back in (often together with the router)."""
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import requests

from inkcal import app as app_mod
from inkcal.app import App
from inkcal.google import AuthError, GoogleCalendar, OAuthClient, TokenStore
from inkcal.models import Event, event_from_dict, event_to_dict
from inkcal.storage import Paths, save_json

TZ = ZoneInfo("Europe/Warsaw")


class CountingDisplay:
    def __init__(self):
        self.shown = 0

    def show(self, img, force=False):
        self.shown += 1
        return True


class HomeNetwork:
    """A saved home network that may be down (router still booting) or without internet."""

    def __init__(self, wifi=False, internet=False):
        self.wifi, self.internet, self.hotspot = wifi, internet, False

    def online(self):
        return self.wifi and self.internet

    def current_ssid(self):
        return "Home-5G" if self.wifi else None

    def saved_wifi(self):
        return ["wifi-Home-5G"]

    def scan(self):
        return []

    def start_hotspot(self, ssid, password):
        self.hotspot = True

    def stop_hotspot(self):
        self.hotspot = False


class Source:
    def __init__(self, ok=True):
        self.ok, self.calls = ok, 0

    def timezone(self):
        self.calls += 1
        if not self.ok:
            raise requests.ConnectionError("no internet")
        return "Europe/Warsaw"

    def calendars(self):
        return [{"id": "c", "name": "Me", "primary": True, "selected": True}]

    def events(self, ids, start, end, tz):
        return [Event("Dentist", datetime.now(tz), datetime.now(tz) + timedelta(hours=1))]


@pytest.fixture
def make_device(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod.time, "sleep", lambda s: None)  # skip the boot wait for Wi-Fi

    def make(net, source=None, clock=True, cached=True):
        paths = Paths(str(tmp_path / "data"), str(tmp_path / "etc"))
        TokenStore(paths).save({"refresh_token": "r", "email": "me@example.com"})
        if cached:
            ev = Event("Yoga", datetime(2026, 11, 5, 17, 30, tzinfo=TZ), datetime(2026, 11, 5, 18, 30, tzinfo=TZ))
            save_json(paths.events, {"synced_at": time.time() - 600, "events": [event_to_dict(ev)]})
        dev = App(paths, CountingDisplay(), net, clock_synced=lambda: clock)
        dev.settings.update(quiet_enabled=False)  # tests must not depend on the time of day
        dev.source = lambda: source or Source()
        return dev
    return make


def test_router_still_booting_keeps_last_screen(make_device):
    net, src = HomeNetwork(wifi=False), Source(ok=False)
    dev = make_device(net, src)
    dev._boot()
    assert dev.mode == "run" and not net.hotspot          # no setup screen, no setup Wi-Fi
    assert [e.title for e in dev.events] == ["Yoga"]      # cached events loaded
    dev._tick()
    assert dev.display.shown == 0                         # panel keeps the picture from before

    # The router comes back: the next retry (30 s, not 15 min) syncs and redraws.
    net.wifi = net.internet = True
    src.ok = True
    assert dev._sync_due_in() <= app_mod.BOOT_RETRY_SECONDS
    dev._last_attempt -= app_mod.BOOT_RETRY_SECONDS
    dev._tick()
    assert dev.display.shown == 1 and [e.title for e in dev.events] == ["Dentist"]
    # From now on the normal interval applies.
    assert dev._sync_due_in() > 60


def test_waits_for_clock_before_syncing_or_drawing(make_device):
    src = Source()
    dev = make_device(HomeNetwork(wifi=True, internet=True), src, clock=False)
    dev._boot()
    assert dev.mode == "run" and src.calls == 0 and dev.display.shown == 0
    dev._booted -= app_mod.CLOCK_WAIT_SECONDS  # NTP blocked on this network: trust the clock anyway
    dev._last_attempt = None
    dev._tick()
    assert src.calls == 1 and dev.display.shown == 1


def test_offline_for_an_hour_draws_cached_events(make_device):
    dev = make_device(HomeNetwork(wifi=True, internet=False), Source(ok=False))
    dev._boot()
    dev._tick()
    assert dev.display.shown == 0
    dev._booted -= app_mod.OFFLINE_AFTER_SECONDS
    dev._last_attempt = None
    dev._tick()
    assert dev.display.shown == 1 and dev.events and dev.mode == "run"


def test_wifi_without_internet_never_falls_back_to_setup(make_device):
    dev = make_device(HomeNetwork(wifi=True, internet=False), Source(ok=False))
    dev._boot()
    dev._tick()
    dev._booted -= 10 * 3600
    dev._tick()
    assert dev.mode == "run"


def test_no_wifi_for_ten_minutes_opens_setup(make_device):
    net = HomeNetwork(wifi=False)
    dev = make_device(net, Source(ok=False))
    dev._boot()
    dev._tick()
    assert dev.mode == "run"
    dev._no_wifi_since -= app_mod.NO_WIFI_SETUP_SECONDS
    dev._tick()
    assert dev.mode == "setup" and net.hotspot


def test_router_replaced_while_running_opens_setup_after_30_min(make_device):
    net, src = HomeNetwork(wifi=True, internet=True), Source()
    dev = make_device(net, src)
    dev._boot()
    assert dev.mode == "run" and dev._synced_since_boot
    assert dev._seconds_until_tick() <= app_mod.WIFI_CHECK_SECONDS  # checks Wi-Fi even with a 60-min sync

    net.wifi = net.internet = False                    # new router, different name/password
    src.ok = False
    dev._tick()
    dev._no_wifi_since -= app_mod.NO_WIFI_SETUP_SECONDS  # 10 min is not enough while running…
    dev._tick()
    assert dev.mode == "run" and not net.hotspot
    dev._no_wifi_since -= app_mod.NO_WIFI_RUNNING_SECONDS  # …30 min is
    dev._tick()
    assert dev.mode == "setup" and net.hotspot


def test_wifi_back_within_30_min_stays_on_calendar(make_device):
    net, src = HomeNetwork(wifi=True, internet=True), Source()
    dev = make_device(net, src)
    dev._boot()
    net.wifi = False
    dev._tick()
    dev._no_wifi_since -= app_mod.NO_WIFI_RUNNING_SECONDS - 60
    net.wifi = True                                    # router finished rebooting
    dev._tick()
    assert dev._no_wifi_since is None
    net.wifi = False
    dev._tick()                                        # the timer starts over
    assert dev.mode == "run"


def test_not_linked_and_offline_still_opens_setup(make_device, tmp_path):
    net = HomeNetwork(wifi=False)
    dev = make_device(net)
    dev.tokens.clear()
    dev._boot()
    assert dev.mode == "setup"


def test_event_cache_roundtrip():
    e = Event("Trip", datetime(2026, 11, 7, tzinfo=TZ), datetime(2026, 11, 9, tzinfo=TZ), all_day=True,
              location="Kraków", calendar_id="c1")
    back = event_from_dict(event_to_dict(e), TZ)
    assert back == e and back.calendar_id == "c1" and back.days()[0].day == 7


# ---------------------------------------------------------------- Google: 401 after a power cut

class Resp:
    def __init__(self, status, data=None, text=""):
        self.status_code, self._data, self.text = status, data or {}, text

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)


class GoogleStub:
    def __init__(self, api, token=None):
        self.api, self.token = list(api), list(token or [])
        self.bearers = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.bearers.append(headers["Authorization"])
        return self.api.pop(0)

    def post(self, url, timeout=None, data=None):
        return self.token.pop(0)


def _google(tmp_path, http, expires_in=3000):
    paths = Paths(str(tmp_path / "data"), str(tmp_path / "etc"))
    store = TokenStore(paths)
    # The clock went back after a power cut, so this already-expired token looks valid.
    store.save({"access_token": "old", "refresh_token": "r", "expires_at": time.time() + expires_in})
    return GoogleCalendar(OAuthClient("id", "secret", "https://relay/"), store, http), store


def test_refused_access_token_is_refreshed_not_signed_out(tmp_path):
    http = GoogleStub(api=[Resp(401), Resp(200, {"value": "Europe/Warsaw"})],
                      token=[Resp(200, {"access_token": "new", "expires_in": 3600})])
    cal, store = _google(tmp_path, http)
    assert cal.timezone() == "Europe/Warsaw"
    assert http.bearers == ["Bearer old", "Bearer new"]
    assert store.load()["access_token"] == "new" and store.linked


def test_401_even_with_fresh_token_keeps_sign_in(tmp_path):
    http = GoogleStub(api=[Resp(401), Resp(401)], token=[Resp(200, {"access_token": "new"})])
    cal, store = _google(tmp_path, http)
    with pytest.raises(requests.HTTPError):
        cal.timezone()
    assert store.linked


def test_revoked_sign_in_still_signs_out(tmp_path):
    http = GoogleStub(api=[Resp(401)], token=[Resp(400, text='{"error": "invalid_grant"}')])
    cal, _ = _google(tmp_path, http)
    with pytest.raises(AuthError):
        cal.timezone()
