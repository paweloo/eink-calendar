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
