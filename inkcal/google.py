"""Google OAuth + Calendar API using plain HTTPS (no google-api-python-client:
it is slow to import and memory hungry on a Pi Zero 2).

Sign-in flow ("local first"):
  phone -> device web UI -> Google consent -> relay page (static, HTTPS) ->
  phone browser is sent back to http://<device-ip>/oauth/callback -> device
  exchanges the code itself (PKCE + client secret). The relay never sees tokens.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import threading
import time
from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests

from .models import Event, dedupe
from .storage import Paths, load_json, save_json

log = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API = "https://www.googleapis.com/calendar/v3"
SCOPES = "openid email https://www.googleapis.com/auth/calendar.readonly"
TIMEOUT = 20


class AuthError(Exception):
    """The stored sign-in is no longer valid; the user has to link again."""


class ConfigError(Exception):
    pass


# --------------------------------------------------------------------------- OAuth

class OAuthClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @classmethod
    def load(cls, paths: Paths) -> "OAuthClient":
        raw = load_json(paths.google_client)
        if not raw:
            raise ConfigError(f"Google OAuth client missing: {paths.google_client}")
        conf = raw.get("web") or raw.get("installed") or raw
        redirect = (conf.get("redirect_uris") or [None])[0]
        if not redirect:
            raise ConfigError("google_client.json has no redirect_uris (add the relay page URL)")
        return cls(conf["client_id"], conf["client_secret"], redirect)


def new_pkce() -> Dict[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return {"verifier": verifier, "challenge": challenge}


def encode_state(nonce: str, return_base: str) -> str:
    """state = <nonce>.<base64url(device base URL)>; the relay page reads the second part."""
    b = base64.urlsafe_b64encode(return_base.encode()).rstrip(b"=").decode()
    return f"{nonce}.{b}"


def decode_state(state: str) -> Dict[str, str]:
    nonce, _, b = state.partition(".")
    pad = "=" * (-len(b) % 4)
    return {"nonce": nonce, "base": base64.urlsafe_b64decode(b + pad).decode() if b else ""}


def auth_url(client: OAuthClient, state: str, challenge: str, login_hint: str = "") -> str:
    params = {
        "client_id": client.client_id,
        "redirect_uri": client.redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent select_account",   # always returns a refresh token; lets user pick account
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return AUTH_URL + "?" + urlencode(params)


def _email_from_id_token(id_token: str) -> str:
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("email", "")
    except Exception:  # noqa: BLE001 - cosmetic only
        return ""


class TokenStore:
    def __init__(self, paths: Paths):
        self._path = paths.token
        self._lock = threading.Lock()

    def load(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return load_json(self._path)

    def save(self, token: Dict[str, Any]) -> None:
        with self._lock:
            save_json(self._path, token)

    def clear(self) -> None:
        with self._lock:
            try:
                self._path.unlink()
            except FileNotFoundError:
                pass

    @property
    def linked(self) -> bool:
        t = self.load()
        return bool(t and t.get("refresh_token"))

    @property
    def email(self) -> str:
        return (self.load() or {}).get("email", "")


def exchange_code(client: OAuthClient, code: str, verifier: str) -> Dict[str, Any]:
    r = requests.post(TOKEN_URL, timeout=TIMEOUT, data={
        "code": code,
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "redirect_uri": client.redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    })
    if r.status_code != 200:
        raise AuthError(f"code exchange failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    if not data.get("refresh_token"):
        raise AuthError("Google returned no refresh token")
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + int(data.get("expires_in", 3600)),
        "email": _email_from_id_token(data.get("id_token", "")),
        "scope": data.get("scope", ""),
    }


def revoke(token: Optional[Dict[str, Any]]) -> None:
    if not token:
        return
    try:
        requests.post(REVOKE_URL, timeout=TIMEOUT, data={"token": token.get("refresh_token") or token.get("access_token")})
    except requests.RequestException:
        log.warning("Could not revoke token (offline?)")


# --------------------------------------------------------------------------- Calendar API

class GoogleCalendar:
    def __init__(self, client: OAuthClient, store: TokenStore, session: Optional[requests.Session] = None):
        self._client = client
        self._store = store
        self._http = session or requests.Session()

    def _access_token(self, force_refresh: bool = False) -> str:
        tok = self._store.load()
        if not tok or not tok.get("refresh_token"):
            raise AuthError("not linked")
        if not force_refresh and tok.get("access_token") and tok.get("expires_at", 0) - 120 > time.time():
            return tok["access_token"]
        r = self._http.post(TOKEN_URL, timeout=TIMEOUT, data={
            "client_id": self._client.client_id,
            "client_secret": self._client.client_secret,
            "refresh_token": tok["refresh_token"],
            "grant_type": "refresh_token",
        })
        if r.status_code in (400, 401) and "invalid_grant" in r.text:
            raise AuthError("refresh token revoked or expired")
        r.raise_for_status()
        data = r.json()
        tok["access_token"] = data["access_token"]
        tok["expires_at"] = time.time() + int(data.get("expires_in", 3600))
        self._store.save(tok)
        return tok["access_token"]

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # A 401 here means the ACCESS token was refused, not that the sign-in is gone. It happens
        # after a power cut: the Pi has no battery clock, boots with an old time and thinks an
        # expired token is still valid. So refresh and retry once; only an invalid_grant from the
        # token endpoint (raised in _access_token) means the user really has to link again.
        for attempt in range(2):
            r = self._http.get(API + path, params=params, timeout=TIMEOUT,
                               headers={"Authorization": "Bearer " + self._access_token(force_refresh=attempt > 0)})
            if r.status_code != 401:
                break
            log.info("access token refused (401), refreshing")
        r.raise_for_status()
        return r.json()

    def timezone(self) -> str:
        return self._get("/users/me/settings/timezone").get("value", "UTC")

    def calendars(self) -> List[Dict[str, Any]]:
        out, page = [], None
        while True:
            data = self._get("/users/me/calendarList", {"pageToken": page} if page else None)
            for c in data.get("items", []):
                out.append({
                    "id": c["id"],
                    "name": c.get("summaryOverride") or c.get("summary") or c["id"],
                    "primary": bool(c.get("primary")),
                    "selected": bool(c.get("selected") or c.get("primary")),
                })
            page = data.get("nextPageToken")
            if not page:
                break
        out.sort(key=lambda c: (not c["primary"], c["name"].lower()))
        return out

    def events(self, calendar_ids: Iterable[str], start: datetime, end: datetime, tz: tzinfo) -> List[Event]:
        out: List[Event] = []
        for cal_id in calendar_ids:
            page = None
            while True:
                params = {
                    "timeMin": start.isoformat(),
                    "timeMax": end.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 250,
                    "timeZone": str(tz),
                    "fields": "nextPageToken,items(status,summary,location,start,end,attendees(self,responseStatus),eventType)",
                }
                if page:
                    params["pageToken"] = page
                data = self._get(f"/calendars/{requests.utils.quote(cal_id, safe='')}/events", params)
                for item in data.get("items", []):
                    ev = parse_event(item, tz, cal_id)
                    if ev:
                        out.append(ev)
                page = data.get("nextPageToken")
                if not page:
                    break
        return dedupe(out)


def _parse_dt(value: str, tz: tzinfo) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def parse_event(item: Dict[str, Any], tz: tzinfo, cal_id: str = "") -> Optional[Event]:
    if item.get("status") == "cancelled":
        return None
    if item.get("eventType") in ("workingLocation",):
        return None
    for a in item.get("attendees") or []:
        if a.get("self") and a.get("responseStatus") == "declined":
            return None
    s, e = item.get("start", {}), item.get("end", {})
    if "date" in s:
        sd = date.fromisoformat(s["date"])
        ed = date.fromisoformat(e.get("date", s["date"]))
        if ed <= sd:
            ed = sd + timedelta(days=1)
        start = datetime(sd.year, sd.month, sd.day, tzinfo=tz)
        end = datetime(ed.year, ed.month, ed.day, tzinfo=tz)
        all_day = True
    elif "dateTime" in s:
        start = _parse_dt(s["dateTime"], tz)
        end = _parse_dt(e.get("dateTime", s["dateTime"]), tz)
        all_day = False
    else:
        return None
    return Event(
        title=(item.get("summary") or "(No title)").strip(),
        start=start, end=end, all_day=all_day,
        location=(item.get("location") or "").split(",")[0].strip(),
        calendar_id=cal_id,
    )


# --------------------------------------------------------------------------- demo source

class DemoCalendar:
    """Fake account for developing on a laptop and for the shop-window demo mode."""

    def __init__(self, tz_name: str = "Europe/Warsaw"):
        self._tz = tz_name

    def timezone(self) -> str:
        return self._tz

    def calendars(self) -> List[Dict[str, Any]]:
        return [
            {"id": "personal", "name": "Personal", "primary": True, "selected": True},
            {"id": "work", "name": "Work", "primary": False, "selected": True},
            {"id": "family", "name": "Family", "primary": False, "selected": True},
            {"id": "holidays", "name": "Holidays", "primary": False, "selected": False},
        ]

    def events(self, calendar_ids: Iterable[str], start: datetime, end: datetime, tz: tzinfo) -> List[Event]:
        today = datetime.now(tz).date()
        base = today - timedelta(days=today.weekday())  # this Monday
        spec = [
            (-14, "09:00", 60, "Team standup"), (-9, None, 0, "Long weekend"), (-7, "19:00", 120, "Book club"),
            (0, "09:00", 30, "Team standup"), (1, "07:30", 60, "Gym"), (1, "12:00", 60, "Project review"),
            (1, "19:00", 90, "Book club"), (2, None, 0, "Mum's birthday"), (5, "09:30", 60, "Pilates"),
            (5, "18:00", 180, "Concert · City Hall"), (7, "08:00", 45, "Dentist"), (9, None, 0, "Team offsite"),
            (10, "19:00", 150, "Dinner with friends"), (17, "10:00", 120, "Car service"),
            (today.weekday(), "08:15", 30, "School run"), (today.weekday(), "13:00", 60, "Lunch with Ana"),
            (today.weekday(), "17:30", 60, "Yoga"), (21, "11:00", 60, "Haircut"), (24, "09:00", 480, "Workshop"),
        ]
        out = []
        for offset, hhmm, minutes, title in spec:
            d = base + timedelta(days=offset)
            if hhmm is None:
                s = datetime(d.year, d.month, d.day, tzinfo=tz)
                ev = Event(title, s, s + timedelta(days=1), True)
            else:
                h, m = map(int, hhmm.split(":"))
                s = datetime(d.year, d.month, d.day, h, m, tzinfo=tz)
                ev = Event(title, s, s + timedelta(minutes=minutes), False, "Studio 4" if title == "Pilates" else "")
            if ev.end > start and ev.start < end:
                out.append(ev)
        return dedupe(out)


def zone(name: Optional[str]) -> tzinfo:
    try:
        return ZoneInfo(name) if name else datetime.now().astimezone().tzinfo or timezone.utc
    except Exception:  # noqa: BLE001
        return timezone.utc
