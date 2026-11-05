"""Command line.

  python -m inkcal run                 on the device (systemd runs this)
  python -m inkcal run --dev           on a laptop: PNG instead of panel, fake Wi-Fi, demo events,
                                       web UI on http://localhost:8080
  python -m inkcal preview [--out DIR] render every screen to PNG
  python -m inkcal firstboot           (root) give a freshly cloned card its own identity
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

from .storage import Paths


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    logging.getLogger("waitress").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def cmd_run(args) -> None:
    from waitress import serve

    from .app import App
    from .display import PngDisplay, WaveshareDisplay
    from .network import FakeNetwork, NetworkManager
    from .web import create_web

    paths = Paths(args.data)
    on_pi = os.path.exists("/dev/spidev0.0") and not args.dev
    display = WaveshareDisplay(paths.screen_png) if on_pi and not args.png else PngDisplay(paths.screen_png)
    use_nm = platform.system() == "Linux" and shutil.which("nmcli") and not args.dev
    network = NetworkManager() if use_nm else FakeNetwork(online=not args.offline)
    port = args.port or (8080 if args.dev else 80)

    app = App(paths, display, network, demo=args.demo or (args.dev and not paths.google_client.exists()), port=port)
    web = create_web(app)
    threading.Thread(target=serve, kwargs=dict(app=web, host="0.0.0.0", port=port, threads=4, ident="inkcal"),
                     daemon=True, name="web").start()
    logging.info("web UI on port %d · screen preview: %s", port, paths.screen_png)

    def _term(*_):
        app.stop()
    signal.signal(signal.SIGTERM, _term)
    try:
        app.run()
    except KeyboardInterrupt:
        pass


def cmd_preview(args) -> None:
    from .preview import render_all
    for theme in args.themes.split(","):
        for p in render_all(args.out, theme=theme):
            print(p)


def cmd_firstboot(args) -> None:
    """Run as root once per card (inkcal-firstboot.service)."""
    from .device import load_or_create_identity

    paths = Paths(args.data)
    ident = load_or_create_identity(paths)
    host = ident["hostname"]
    subprocess.run(["hostnamectl", "set-hostname", host], check=False)
    try:
        hosts = Path("/etc/hosts").read_text().splitlines()
        hosts = [line for line in hosts if not line.startswith("127.0.1.1")] + [f"127.0.1.1\t{host}"]
        Path("/etc/hosts").write_text("\n".join(hosts) + "\n")
    except OSError as e:
        logging.warning("could not update /etc/hosts: %s", e)
    if not glob.glob("/etc/ssh/ssh_host_*_key"):
        subprocess.run(["ssh-keygen", "-A"], check=False)
    for p in [paths.data, *paths.data.rglob("*")]:
        try:
            shutil.chown(p, "inkcal", "inkcal")
        except (LookupError, OSError):
            pass
    logging.info("first boot done: %s (%s)", host, ident["hotspot_ssid"])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="inkcal")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--data", help="data directory (default /var/lib/inkcal or ./.dev-data)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--dev", action="store_true", help="laptop mode: PNG display, fake Wi-Fi, port 8080")
    r.add_argument("--demo", action="store_true", help="demo events instead of Google")
    r.add_argument("--offline", action="store_true", help="with --dev: start in Wi-Fi setup mode")
    r.add_argument("--png", action="store_true", help="write PNG even on the Pi (no panel attached)")
    r.add_argument("--port", type=int)
    r.set_defaults(fn=cmd_run)

    p = sub.add_parser("preview")
    p.add_argument("--out", default="out/preview")
    p.add_argument("--themes", default="classic,mono,bold")
    p.set_defaults(fn=cmd_preview)

    f = sub.add_parser("firstboot")
    f.set_defaults(fn=cmd_firstboot)

    args = ap.parse_args(argv)
    _setup_logging(args.verbose)
    args.fn(args)


if __name__ == "__main__":
    main(sys.argv[1:])
