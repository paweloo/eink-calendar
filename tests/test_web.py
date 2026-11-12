"""Drive the web UI + controller together (fake Wi-Fi, PNG display, demo calendar)."""
import re
import threading

import pytest

from inkcal.app import App
from inkcal.display import PngDisplay
from inkcal.network import FakeNetwork
from inkcal.storage import Paths
from inkcal.web import create_web


@pytest.fixture
def device(tmp_path):
    paths = Paths(str(tmp_path / "data"), str(tmp_path / "etc"))
    net = FakeNetwork(online=False)
    dev = App(paths, PngDisplay(paths.screen_png), net, demo=False, port=8080)
    t = threading.Thread(target=dev.run, daemon=True)
    t.start()
    yield dev
    dev.stop()


def _drain(dev):
    """Wait until the controller processed everything queued so far."""
    done = threading.Event()
    dev.post(done.set)
    assert done.wait(10)


def test_setup_to_link_to_run(device, tmp_path):
    dev = device
    _drain(dev)
    assert dev.mode == "setup"
    c = create_web(dev).test_client()

    # Captive portal: any foreign host is redirected to the setup page.
    r = c.get("/generate_204", headers={"Host": "connectivitycheck.gstatic.com"})
    assert r.status_code == 302 and "10.42.0.1" in r.headers["Location"]

    r = c.get("/wifi", headers={"Host": "10.42.0.1"})
    assert b"Home-5G" in r.data
    r = c.post("/wifi", data={"ssid": "Home-5G", "password": "wrong-pass-but-long"}, headers={"Host": "10.42.0.1"})
    assert b"Connecting" in r.data
    _drain(dev)
    assert dev.mode == "link"

    # Settings are locked until paired.
    assert c.get("/settings").status_code == 302

    # Wrong code, then right code.
    assert b"doesn" in c.post("/link", data={"code": "000000" if dev.code.value != "000000" else "111111"}).data
    r = c.post("/link", data={"code": dev.code.value})
    assert r.status_code == 302 and r.headers["Location"].endswith("/link/google")

    # No OAuth client configured in tests -> helpful error page, not a crash.
    r = c.get("/link/google")
    assert r.status_code == 500 and b"isn" in r.data

    # Pretend Google linking succeeded by switching to demo data.
    dev.demo = True
    dev.post(dev.on_linked)
    _drain(dev)
    assert dev.mode == "run" and dev.events

    r = c.get("/settings")
    assert r.status_code == 200 and b"Calendars to show" in r.data
    assert c.get("/screen.png").mimetype == "image/png"

    # Live preview: unsaved options change the picture but not the settings or the panel.
    import io
    from PIL import Image
    shown = dev.display._last_hash
    def blackness(r):
        img = Image.open(io.BytesIO(r.data)).convert("L")
        return sum(1 for p in img.getdata() if p < 128) / (800 * 480)
    assert blackness(c.get("/screen.png?theme=dark&view=agenda")) > 0.6
    assert blackness(c.get("/screen.png?theme=bogus")) < 0.4          # invalid value -> saved theme
    assert dev.settings.get("theme") == "classic" and dev.display._last_hash == shown

    r = c.post("/settings", data={"view": "week", "theme": "mono", "refresh_minutes": "30",
                                  "quiet_start": "22:00", "quiet_end": "07:00", "device_name": "Hall",
                                  "cal_personal": "on"})
    assert b"Saved" in r.data
    assert dev.settings.get("view") == "week" and dev.settings.get("calendars") == ["personal"]

    # A second browser has to pair with a fresh code from the screen.
    c2 = create_web(dev).test_client()
    assert c2.get("/settings").status_code == 302
    c2.post("/pair/show", data={"next": "/settings"})
    _drain(dev)
    r = c2.post("/pair", data={"code": dev.code.value, "next": "/settings"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/settings")
    assert c2.get("/settings").status_code == 200

    # Unpair all phones invalidates both cookies.
    c2.post("/action/logout_browsers")
    assert c.get("/settings").status_code == 302


def test_oauth_callback_rejects_unknown_state(device):
    _drain(device)
    c = create_web(device).test_client()
    r = c.get("/oauth/callback?code=x&state=bogus.aHR0cDovLzEwLjAuMC4x", headers={"Host": "10.42.0.1"})
    assert r.status_code == 400


def test_settings_open_right_after_google_link(device):
    """The sign-in is saved before the controller leaves "link" mode (it first spends ~20 s
    drawing "You're all set"). Opening settings in that gap must not send the user to Google."""
    dev = device
    _drain(dev)
    c = create_web(dev).test_client()
    with c.session_transaction() as s:
        s["epoch"] = dev.settings.get("auth_epoch")
    dev.mode = "link"                                  # controller hasn't caught up yet
    dev.tokens.save({"refresh_token": "r", "email": "me@example.com"})
    assert c.get("/").headers["Location"].endswith("/settings")
    assert c.get("/link").headers["Location"].endswith("/settings")
    assert c.get("/settings").status_code == 200
    assert c.get("/screen.png").status_code == 200


def test_pairing_carries_over_between_ip_and_local_name(device, monkeypatch):
    """Paired on the IP (from the panel's QR code), then opened <name>.local: no second code."""
    import inkcal.web as web_mod
    from urllib.parse import urlsplit
    monkeypatch.setattr(web_mod, "local_ip", lambda: "192.168.1.50")
    dev = device
    _drain(dev)
    dev.mode = "run"
    web = create_web(dev)
    ip, local = {"Host": "192.168.1.50:8080"}, {"Host": f"{dev.mdns_host}:8080"}
    on_ip, on_local = web.test_client(), web.test_client()   # separate cookie jars, like two hosts
    with on_ip.session_transaction(headers=ip) as s:
        s["epoch"] = dev.settings.get("auth_epoch")

    # .local pair page offers to try the IP address.
    page = on_local.get("/pair?next=/settings", headers=local).data.decode()
    go = re.search(r'location\.replace\("([^"]+)"\)', page).group(1).replace("\\u0026", "&")
    assert "http://192.168.1.50:8080/healthz" in page and go.startswith("http://192.168.1.50:8080/pair/handoff")

    # The IP side knows this browser and sends it back with a token.
    u = urlsplit(go)
    r = on_ip.get(f"{u.path}?{u.query}", headers=ip)
    back = urlsplit(r.headers["Location"])
    assert back.netloc == f"{dev.mdns_host}:8080" and back.path == "/pair/accept"

    accept = f"{back.path}?{back.query}"
    r = on_local.get(accept, headers=local)
    assert r.headers["Location"].endswith("/settings")
    assert on_local.get("/settings", headers=local).status_code == 200

    # Tokens are single-use.
    stranger = web.test_client()
    assert "/pair" in stranger.get(accept, headers=local).headers["Location"]
    assert stranger.get("/settings", headers=local).status_code == 302

    # A browser that isn't paired on the IP either just gets the code form, without looping.
    r = stranger.get(f"{u.path}?{u.query}", headers=ip)
    assert r.headers["Location"].startswith(f"http://{dev.mdns_host}:8080/pair?") and "h=0" in r.headers["Location"]
    assert b"location.replace" not in stranger.get("/pair?next=/settings&h=0", headers=local).data

    # Tokens are never sent to a host that isn't this device.
    assert on_ip.get("/pair/handoff?next=/settings&back=evil.example", headers=ip).status_code == 400
