# E-ink Calendar

A Google Calendar on a Waveshare 7.5" black/white/red e-paper panel, driven by a Raspberry Pi Zero 2 W.
Built to be set up by anyone with a phone and to be copied onto many devices.

- **Setup with no keyboard:** the screen shows a QR code. Your phone joins the calendar's own Wi-Fi, picks
  the home network, then links Google with a 6-digit code shown on the screen.
- **Views:** month (default), week, agenda. **Themes:** classic (red), mono, bold, dark (white on black, red accents).
- **Settings on the phone** at `http://calendar-xxxx.local`: view, theme, week start, 24-hour clock, which calendars to show,
  sync interval, quiet hours, switch account, sign out, change Wi-Fi, restart, factory reset.
- **Fast and gentle on the panel:** screens are drawn directly with Pillow (no browser), in about 10 ms on a laptop.
  The panel redraws only when what it shows actually changes.

## Project layout

```
inkcal/                 the app (Python 3.9+, runs as a systemd service)
  app.py                controller: setup → link → run, sync schedule, job queue
  google.py             OAuth + Calendar API over plain HTTPS, demo data source
  network.py            Wi-Fi + setup hotspot via NetworkManager (nmcli)
  display.py            Waveshare panel / PNG output, skip-if-unchanged
  render/               views.py (month/week/agenda), screens.py (welcome, link…), canvas.py
  web/                  Flask UI: captive portal, pairing, Google link, settings
  vendor/waveshare_epd  Waveshare driver for the 7.5" (B) V2 (MIT)
  assets/fonts          Archivo + Inter (SIL OFL)
relay/index.html        static OAuth redirect page (GitHub Pages)
system/                 systemd units, polkit rule, captive-portal DNS
scripts/                install.sh (on Pi), deploy.sh (from Mac), prepare-golden-image.sh
docs/                   INSTALL, GOOGLE_SETUP, MANUFACTURING
tests/                  pytest
```

## Develop on the Mac

```bash
cd ~/Documents/Projects/eink-calendar
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

.venv/bin/python -m inkcal preview               # every screen → out/preview/*.png
.venv/bin/python -m inkcal run --dev             # web UI on http://localhost:8080,
                                                 # panel image in .dev-data/screen.png
.venv/bin/python -m inkcal run --dev --offline   # start in Wi-Fi setup mode
.venv/bin/python -m pytest -q
```

In `--dev` mode, Wi-Fi is simulated and, unless `.dev-data/google_client.json` exists, demo events are used.
To pair the browser, read the 6-digit code from `.dev-data/screen.png` (or the log).

## Put it on a Pi

See **[docs/INSTALL.md](docs/INSTALL.md)**. In short: flash Raspberry Pi OS Lite, then
`./scripts/deploy.sh pi@calendar-dev.local`.
