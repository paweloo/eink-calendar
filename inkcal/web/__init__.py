"""Local web UI: Wi-Fi setup (captive portal), Google linking, settings.

Security model
  * Setup mode: anyone who joined the WPA2 hotspot (password shown on the panel) may pick Wi-Fi.
  * Everything else needs a browser "paired" by typing the 6-digit code shown on the panel.
    Pairing is a signed cookie tied to settings.auth_epoch; factory reset / "sign out all
    browsers" bumps the epoch and invalidates every cookie.
"""
from __future__ import annotations

import io
import logging
import secrets
import time
from functools import wraps
from typing import TYPE_CHECKING

from flask import Flask, abort, redirect, render_template, request, send_file, session, url_for

from ..google import AuthError, ConfigError, auth_url, decode_state, encode_state, exchange_code, new_pkce
from ..network import HOTSPOT_IP
from ..render import compose, to_planes
from ..settings import REFRESH_CHOICES, THEMES, VIEWS, parse_hhmm

if TYPE_CHECKING:
    from ..app import App

log = logging.getLogger(__name__)
OAUTH_TTL = 15 * 60


def create_web(dev: "App") -> Flask:
    web = Flask(__name__)
    web.secret_key = dev.ident["secret_key"]
    web.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True,
                      PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 365)

    # ------------------------------------------------------------------ helpers
    def paired() -> bool:
        return session.get("epoch") == dev.settings.get("auth_epoch")

    def need_pairing(view):
        @wraps(view)
        def wrapper(*a, **kw):
            if not paired():
                return redirect(url_for("pair", next=request.path))
            return view(*a, **kw)
        return wrapper

    def page(template: str, **kw):
        return render_template(template, dev=dev, mode=dev.mode, paired=paired(),
                               device_name=dev.settings.get("device_name"), **kw)

    @web.before_request
    def captive_portal():
        dev.last_web_activity = time.time()
        if dev.mode == "setup":
            host = (request.host or "").split(":")[0]
            if host not in (HOTSPOT_IP, dev.mdns_host, dev.hostname, "localhost", "127.0.0.1"):
                # Phone OS connectivity checks land here -> opens the setup page automatically.
                return redirect(f"http://{HOTSPOT_IP}/", code=302)
        return None

    @web.after_request
    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        return resp

    # ------------------------------------------------------------------ routing by mode
    def current_mode() -> str:
        # /oauth/callback saves the Google sign-in right away, but the controller switches to
        # "run" a moment later, on its own thread (after a ~20 s "You're all set" refresh).
        # Treat that gap as "run", or "Open settings" would send the user back to Google.
        if dev.mode == "link" and dev.linked:
            return "run"
        return dev.mode

    @web.route("/")
    def index():
        mode = current_mode()
        if mode == "setup":
            return redirect(url_for("wifi"))
        if mode == "link":
            return redirect(url_for("link"))
        return redirect(url_for("settings"))

    # ------------------------------------------------------------------ Wi-Fi
    @web.route("/wifi", methods=["GET", "POST"])
    def wifi():
        if dev.mode != "setup":
            return redirect(url_for("index"))
        if request.method == "POST":
            ssid = request.form.get("ssid") or request.form.get("other_ssid", "").strip()
            password = request.form.get("password", "")
            if not ssid:
                return page("wifi.html", networks=dev.scan_cache, error="Choose a network.")
            if password and not 8 <= len(password) <= 63:
                return page("wifi.html", networks=dev.scan_cache, selected=ssid,
                            error="Wi-Fi passwords are 8 to 63 characters.")
            dev.post(lambda: dev.connect_wifi(ssid, password))
            return page("connecting.html", ssid=ssid)
        return page("wifi.html", networks=dev.scan_cache, selected=(dev.scan_cache[0]["ssid"] if dev.scan_cache else ""))

    # ------------------------------------------------------------------ pairing
    @web.route("/pair", methods=["GET", "POST"])
    def pair():
        nxt = request.values.get("next") or url_for("index")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = url_for("index")
        if paired():
            return redirect(nxt)
        error = None
        if request.method == "POST":
            if dev.code.check(request.form.get("code", "")):
                session.permanent = True
                session["epoch"] = dev.settings.get("auth_epoch")
                dev.post(dev.end_pairing)
                return redirect(nxt)
            error = "That code doesn’t match the one on the screen."
        return page("pair.html", next=nxt, error=error, showing=dev._pair_until > time.time())

    @web.route("/pair/show", methods=["POST"])
    def pair_show():
        dev.post(dev.show_pair_code)
        return redirect(url_for("pair", next=request.form.get("next", "/")))

    # ------------------------------------------------------------------ Google
    @web.route("/link", methods=["GET", "POST"])
    def link():
        if dev.mode == "setup":
            return redirect(url_for("wifi"))
        if dev.mode == "link" and dev.linked:
            return redirect(url_for("settings"))  # just linked, controller still catching up
        if dev.mode == "link" and not paired():
            error = None
            if request.method == "POST":
                if dev.code.check(request.form.get("code", "")):
                    session.permanent = True
                    session["epoch"] = dev.settings.get("auth_epoch")
                    return redirect(url_for("link_google"))
                error = "That code doesn’t match the one on the screen."
            return page("link.html", error=error)
        if not paired():
            return redirect(url_for("pair", next="/link"))
        return page("link.html", error=None)

    @web.route("/link/google", methods=["GET", "POST"])
    @need_pairing
    def link_google():
        try:
            client = dev.oauth_client()
        except ConfigError as e:
            return page("message.html", title="Google sign-in isn’t set up",
                        body=f"{e}. See docs/GOOGLE_SETUP.md."), 500
        now = time.time()
        for k in [k for k, v in dev.pending_oauth.items() if now - v["ts"] > OAUTH_TTL]:
            dev.pending_oauth.pop(k, None)
        nonce = secrets.token_urlsafe(16)
        pkce = new_pkce()
        dev.pending_oauth[nonce] = {"verifier": pkce["verifier"], "ts": now}
        state = encode_state(nonce, dev.base_url())
        return redirect(auth_url(client, state, pkce["challenge"]))

    @web.route("/oauth/callback")
    def oauth_callback():
        if request.args.get("error"):
            return page("message.html", title="Sign-in cancelled",
                        body="Nothing was changed. You can try again any time.", action=("Try again", "/link"))
        state = decode_state(request.args.get("state", ""))
        pending = dev.pending_oauth.pop(state["nonce"], None)
        if not pending or time.time() - pending["ts"] > OAUTH_TTL:
            return page("message.html", title="This sign-in link has expired",
                        body="Start again from the calendar’s page.", action=("Start again", "/link")), 400
        try:
            token = exchange_code(dev.oauth_client(), request.args.get("code", ""), pending["verifier"])
        except (AuthError, ConfigError) as e:
            log.error("token exchange failed: %s", e)
            return page("message.html", title="Google sign-in failed", body=str(e),
                        action=("Try again", "/link")), 502
        if "calendar.readonly" not in token.get("scope", ""):
            return page("message.html", title="Calendar access is needed",
                        body="Please tick the box that lets the calendar see your events.",
                        action=("Try again", "/link")), 400
        dev.tokens.save(token)
        dev.post(dev.on_linked)
        return page("linked.html", email=token.get("email", ""))

    # ------------------------------------------------------------------ settings
    @web.route("/settings", methods=["GET", "POST"])
    @need_pairing
    def settings():
        if current_mode() != "run":
            return redirect(url_for("index"))
        saved = False
        error = None
        if request.method == "POST":
            f = request.form
            try:
                changes = {
                    "device_name": (f.get("device_name") or "").strip()[:40] or "E-ink calendar",
                    "view": f.get("view") if f.get("view") in VIEWS else "month",
                    "theme": f.get("theme") if f.get("theme") in THEMES else "classic",
                    "week_start": 6 if f.get("week_start") == "6" else 0,
                    "clock_24h": f.get("clock_24h") == "on",
                    "refresh_minutes": int(f.get("refresh_minutes", 15)),
                    "quiet_enabled": f.get("quiet_enabled") == "on",
                    "quiet_start": f.get("quiet_start", "23:00"),
                    "quiet_end": f.get("quiet_end", "06:00"),
                }
                if changes["refresh_minutes"] not in REFRESH_CHOICES:
                    raise ValueError("refresh")
                parse_hhmm(changes["quiet_start"])
                parse_hhmm(changes["quiet_end"])
                if dev.calendars:
                    changes["calendars"] = [c["id"] for c in dev.calendars if f.get("cal_" + c["id"]) == "on"]
                cal_changed = changes.get("calendars") != dev.settings.get("calendars")
                dev.settings.update(**changes)
                dev.post(lambda: dev.refresh(force_sync=cal_changed, force_display=True))
                saved = True
            except (ValueError, TypeError):
                error = "Some values were not valid."
        s = dev.settings.all()
        chosen = s["calendars"]
        cals = [{**c, "on": (c["id"] in chosen) if chosen is not None else c["selected"]} for c in dev.calendars]
        return page("settings.html", s=s, cals=cals, views=VIEWS, themes=THEMES, refresh=REFRESH_CHOICES,
                    email=dev.tokens.email if not dev.demo else "demo@example.com",
                    wifi=dev.net.current_ssid(), saved=saved, error=error,
                    last_sync=dev.last_sync.strftime("%H:%M") if dev.last_sync else None,
                    last_error=dev.last_error, version=__import__("inkcal").__version__)

    @web.route("/action/<name>", methods=["POST"])
    @need_pairing
    def action(name: str):
        if name == "sync":
            dev.post(lambda: dev.refresh(force_sync=True))
            return redirect(url_for("settings"))
        if name == "signout":
            dev.post(dev.sign_out)
            return page("message.html", title="Signed out",
                        body="The calendar now shows the link screen. Link another account any time.",
                        action=("Link an account", "/link"))
        if name == "switch":
            dev.post(dev.sign_out)
            return redirect(url_for("link_google"))
        if name == "wifi":
            dev.post(dev.start_wifi_setup)
            return page("message.html", title="Wi-Fi setup is on",
                        body=f"Join “{dev.ident['hotspot_ssid']}” (password on the screen) to pick a new network.")
        if name == "logout_browsers":
            dev.settings.update(auth_epoch=dev.settings.get("auth_epoch") + 1)
            return redirect(url_for("pair"))
        if name == "restart":
            dev.post(dev.reboot)
            return page("message.html", title="Restarting…", body="The calendar will be back in about a minute.")
        if name == "reset":
            if request.form.get("confirm") != "RESET":
                return redirect(url_for("settings") + "#device")
            dev.post(dev.factory_reset)
            return page("message.html", title="Factory reset",
                        body="Everything was erased. Follow the steps on the calendar’s screen to set it up again.")
        abort(404)

    @web.route("/screen.png")
    @need_pairing
    def screen():
        if current_mode() != "run":
            abort(404)
        # Live preview from the settings form: unsaved display options as query parameters.
        a, preview = request.args, {}
        if a.get("view") in VIEWS:
            preview["view"] = a["view"]
        if a.get("theme") in THEMES:
            preview["theme"] = a["theme"]
        if a.get("week_start") in ("0", "6"):
            preview["week_start"] = int(a["week_start"])
        if a.get("clock_24h") in ("0", "1"):
            preview["clock_24h"] = a["clock_24h"] == "1"
        black, red = to_planes(dev.render(**preview))
        buf = io.BytesIO()
        compose(black, red).save(buf, "PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")

    @web.route("/healthz")
    def healthz():
        return {"mode": dev.mode, "linked": dev.linked, "last_error": dev.last_error}

    return web
