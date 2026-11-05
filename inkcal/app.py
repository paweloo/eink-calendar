"""The device controller: one long-running process, three modes.

  SETUP  no working Wi-Fi  -> hotspot + captive portal, Welcome screen
  LINK   online, no Google -> Link screen with pairing code
  RUN    online + linked   -> sync on schedule, redraw only when something changed

All display and network actions run on the main thread (one job queue), so the
web UI never blocks on a 20-second e-ink refresh or a Wi-Fi reconnect.
"""
from __future__ import annotations

import hmac
import logging
import queue
import secrets
import subprocess
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .device import load_or_create_identity, local_ip
from .google import (AuthError, ConfigError, DemoCalendar, GoogleCalendar, OAuthClient,
                     TokenStore, revoke, zone)
from .models import Event
from .network import HOTSPOT_IP, NetworkError
from .render import RenderContext, render_view, screens
from .settings import Settings, in_quiet_hours, parse_hhmm
from .storage import Paths

log = logging.getLogger(__name__)

SETUP, LINK, RUN = "setup", "link", "run"
PAIR_SCREEN_SECONDS = 300
SETUP_RETRY_SECONDS = 600       # with a saved network, retry it every 10 min while in setup
OFFLINE_AFTER_SECONDS = 3600    # show "Offline" footer after an hour of failed syncs


class PairCode:
    """6-digit code shown on the panel; proves the person is next to the device."""

    MAX_FAILURES = 5

    def __init__(self, on_change: Callable[[], None] = lambda: None):
        self._on_change = on_change
        self._lock = threading.Lock()
        self.new(notify=False)

    def new(self, notify: bool = True) -> str:
        with self._lock:
            self.value = f"{secrets.randbelow(10 ** 6):06d}"
            self.failures = 0
        if notify:
            self._on_change()
        return self.value

    def check(self, attempt: str) -> bool:
        attempt = "".join(ch for ch in (attempt or "") if ch.isdigit())
        with self._lock:
            ok = hmac.compare_digest(attempt, self.value)
            if not ok:
                self.failures += 1
                locked = self.failures >= self.MAX_FAILURES
            else:
                locked = False
        if locked:
            log.warning("too many wrong codes, issuing a new one")
            self.new()
        return ok


class App:
    def __init__(self, paths: Paths, display, network, demo: bool = False, port: int = 80):
        self.paths = paths
        self.display = display
        self.net = network
        self.demo = demo
        self.port = port
        self.ident = load_or_create_identity(paths)
        self.settings = Settings(paths)
        self.tokens = TokenStore(paths)
        self.code = PairCode(on_change=lambda: self.post(self._redraw_mode_screen))
        self.mode: Optional[str] = None
        self.scan_cache: List[Dict] = []
        self.calendars: List[Dict] = []
        self.events: List[Event] = []
        self.last_sync: Optional[datetime] = None
        self.last_sync_ok: Optional[float] = None
        self.last_error: Optional[str] = None
        self.last_web_activity = 0.0
        self.pending_oauth: Dict[str, Dict[str, Any]] = {}
        self._pair_until = 0.0
        self._setup_since = 0.0
        self._q: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._stop = threading.Event()

    # ------------------------------------------------------------------ helpers
    @property
    def hostname(self) -> str:
        return self.ident["hostname"]

    @property
    def mdns_host(self) -> str:
        return f"{self.hostname}.local"

    def base_url(self) -> str:
        """URL phones use to reach us. IP rather than .local: Android has no mDNS in browsers."""
        host = HOTSPOT_IP if self.mode == SETUP else (local_ip() or self.mdns_host)
        return f"http://{host}" + ("" if self.port == 80 else f":{self.port}")

    @property
    def linked(self) -> bool:
        return self.demo or self.tokens.linked

    def oauth_client(self) -> OAuthClient:
        return OAuthClient.load(self.paths)

    def source(self):
        return DemoCalendar() if self.demo else GoogleCalendar(self.oauth_client(), self.tokens)

    @property
    def tz(self):
        return zone(self.settings.get("timezone"))

    def post(self, job: Callable[[], None]) -> None:
        """Run a job on the main thread (thread-safe; used by the web UI)."""
        self._q.put(job)

    def stop(self) -> None:
        self._stop.set()
        self.post(lambda: None)

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        self._boot()
        while not self._stop.is_set():
            try:
                job = self._q.get(timeout=self._seconds_until_tick())
            except queue.Empty:
                job = None
            try:
                if job:
                    job()
                else:
                    self._tick()
            except Exception:  # noqa: BLE001 - the device must keep running
                log.exception("job failed")

    def _boot(self) -> None:
        if not self.net.online() and self.net.saved_wifi():
            log.info("waiting for saved Wi-Fi…")
            for _ in range(20):
                if self.net.online():
                    break
                time.sleep(3)
        if self.net.online():
            self._enter_link_or_run()
        else:
            self._enter_setup()

    def _seconds_until_tick(self) -> float:
        if self.mode != RUN:
            return 30
        now = datetime.now(self.tz)
        waits = [60 * 60]
        if self.last_sync:
            nxt = self.last_sync + timedelta(minutes=self.settings.get("refresh_minutes"))
            waits.append((nxt - now).total_seconds())
        else:
            waits.append(0)
        midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=now.tzinfo)
        waits.append((midnight - now).total_seconds() + 5)
        if self._pair_until:
            waits.append(self._pair_until - time.time())
        return max(1.0, min(waits))

    def _tick(self) -> None:
        if self.mode == SETUP:
            idle = time.time() - max(self.last_web_activity, self._setup_since)
            if self.net.saved_wifi() and idle > SETUP_RETRY_SECONDS:
                log.info("retrying saved Wi-Fi")
                self.net.stop_hotspot()
                for _ in range(15):
                    time.sleep(3)
                    if self.net.online():
                        self._enter_link_or_run()
                        return
                self._enter_setup()
        elif self.mode == LINK:
            if self.linked:
                self._enter_link_or_run()
        elif self.mode == RUN:
            if self._pair_until and time.time() >= self._pair_until:
                self._pair_until = 0
            self.refresh()

    # ------------------------------------------------------------------ modes
    def _enter_setup(self, error_ssid: Optional[str] = None) -> None:
        self.mode = SETUP
        self._setup_since = time.time()
        try:
            self.scan_cache = self.net.scan() or self.scan_cache
        except NetworkError as e:
            log.warning("scan failed: %s", e)
        try:
            self.net.start_hotspot(self.ident["hotspot_ssid"], self.ident["hotspot_password"])
        except NetworkError as e:
            log.error("could not start hotspot: %s", e)
        theme = self.settings.get("theme")
        if error_ssid:
            img = screens.message(
                f"Couldn’t join {error_ssid}",
                "The password may be wrong, or the network is out of range. The setup Wi-Fi is back on: "
                "join it again and pick your network.",
                f"Network {self.ident['hotspot_ssid']}  ·  password {self.ident['hotspot_password']}", theme)
        else:
            img = screens.welcome(self.ident["hotspot_ssid"], self.ident["hotspot_password"], theme)
        self.display.show(img)

    def _enter_link_or_run(self) -> None:
        if self.linked:
            self.mode = RUN
            self.refresh(force_sync=True)
        else:
            self.mode = LINK
            self.code.new(notify=False)
            self._show_link_screen()

    def _show_link_screen(self) -> None:
        self.display.show(screens.link(self.base_url(), self.code.value, self.net.current_ssid() or "",
                                       self.settings.get("theme")))

    def _redraw_mode_screen(self) -> None:
        if self.mode == LINK:
            self._show_link_screen()
        elif self.mode == RUN and self._pair_until:
            self.show_pair_code()

    # ------------------------------------------------------------------ sync + draw
    def _window(self, today: date):
        month_start = today.replace(day=1)
        start = min(month_start, today - timedelta(days=7)) - timedelta(days=1)
        end = max(month_start + timedelta(days=42), today + timedelta(days=16))
        return start, end

    def sync(self) -> None:
        src = self.source()
        tz_name = src.timezone()
        if tz_name != self.settings.get("timezone"):
            self.settings.update(timezone=tz_name)
        tz = zone(tz_name)
        self.calendars = src.calendars()
        chosen = self.settings.get("calendars")
        ids = [c["id"] for c in self.calendars if (c["id"] in chosen if chosen is not None else c["selected"])]
        start, end = self._window(datetime.now(tz).date())
        self.events = src.events(ids, datetime(start.year, start.month, start.day, tzinfo=tz),
                                 datetime(end.year, end.month, end.day, tzinfo=tz), tz)
        self.last_sync = datetime.now(tz)
        self.last_sync_ok = time.time()
        self.last_error = None
        log.info("synced %d events from %d calendars", len(self.events), len(ids))

    def refresh(self, force_sync: bool = False, force_display: bool = False) -> None:
        if self.mode != RUN:
            return
        now = datetime.now(self.tz)
        due = force_sync or not self.last_sync or \
            now - self.last_sync >= timedelta(minutes=self.settings.get("refresh_minutes"))
        if due:
            try:
                self.sync()
            except AuthError as e:
                log.warning("Google sign-in no longer valid: %s", e)
                self.tokens.clear()
                self._enter_link_or_run()
                return
            except ConfigError as e:
                self.last_error = str(e)
                log.error("%s", e)
            except Exception as e:  # noqa: BLE001 - network hiccups etc.
                self.last_error = str(e)
                self.last_sync = now  # back off until next interval
                log.warning("sync failed: %s", e)
        if self._pair_until and time.time() < self._pair_until:
            return
        s = self.settings
        if not force_display and s.get("quiet_enabled") and in_quiet_hours(
                datetime.now(self.tz).time(), parse_hhmm(s.get("quiet_start")), parse_hhmm(s.get("quiet_end"))):
            log.debug("quiet hours, not redrawing")
            return
        self.display.show(self.render(), force=force_display)

    def render(self):
        s = self.settings
        offline = bool(self.last_sync_ok is None or time.time() - self.last_sync_ok > OFFLINE_AFTER_SECONDS)
        ctx = RenderContext(
            now=datetime.now(self.tz), events=self.events, view=s.get("view"), theme=s.get("theme"),
            week_start=s.get("week_start"), clock_24h=s.get("clock_24h"),
            updated=datetime.fromtimestamp(self.last_sync_ok, self.tz) if self.last_sync_ok else None,
            host=self.mdns_host, offline=offline and self.last_error is not None,
        )
        return render_view(ctx)

    # ------------------------------------------------------------------ actions (called via post())
    def connect_wifi(self, ssid: str, password: str) -> None:
        self.display.show(screens.message(
            f"Connecting to {ssid}…",
            "This takes up to a minute. The next step will appear on this screen.",
            theme=self.settings.get("theme")))
        try:
            ok = self.net.connect(ssid, password)
        except NetworkError as e:
            log.warning("connect failed: %s", e)
            ok = False
        if ok:
            self._enter_link_or_run()
        else:
            self._enter_setup(error_ssid=ssid)

    def start_wifi_setup(self) -> None:
        self._enter_setup()

    def on_linked(self) -> None:
        self.settings.update(calendars=None)
        self.display.show(screens.ready(self.tokens.email, self.mdns_host, self.settings.get("device_name"),
                                        self.settings.get("theme")))
        self.mode = RUN
        self.last_sync = None
        self.refresh(force_sync=True)

    def show_pair_code(self) -> None:
        if self.mode == LINK:
            self._show_link_screen()
            return
        self._pair_until = time.time() + PAIR_SCREEN_SECONDS
        self.display.show(screens.link(
            self.base_url(), self.code.value, "", self.settings.get("theme"),
            title="Pair a phone\nwith this calendar",
            note="The calendar comes back after pairing, or in 5 minutes."))

    def end_pairing(self) -> None:
        self.code.new(notify=False)
        if self._pair_until:
            self._pair_until = 0
            self.refresh(force_display=True)

    def sign_out(self) -> None:
        revoke(self.tokens.load())
        self.tokens.clear()
        self.events, self.calendars, self.last_sync = [], [], None
        self.settings.update(calendars=None)
        self._enter_link_or_run()

    def factory_reset(self) -> None:
        log.warning("factory reset")
        revoke(self.tokens.load())
        self.tokens.clear()
        self.settings.reset()
        self.events, self.calendars, self.last_sync, self.last_sync_ok = [], [], None, None
        self.net.forget_all()
        self._enter_setup()

    def reboot(self) -> None:
        self.display.show(screens.message("Restarting…", "Back in about a minute.",
                                          theme=self.settings.get("theme")))
        subprocess.run(["systemctl", "reboot"], check=False)
