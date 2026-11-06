#!/usr/bin/env bash
# Install / update the calendar on a Raspberry Pi running Raspberry Pi OS Lite (Bookworm).
# Run ON THE PI, as root, from the project folder:   sudo ./scripts/install.sh
# Safe to run again: it updates the app and keeps the device's identity, sign-in and settings.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/inkcal
DATA=/var/lib/inkcal
ETC=/etc/inkcal

if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
. /etc/os-release
if [[ "${VERSION_CODENAME:-}" != "bookworm" && "${VERSION_CODENAME:-}" != "trixie" ]]; then
  echo "Warning: tested on Raspberry Pi OS Bookworm; you have ${PRETTY_NAME:-unknown}." >&2
fi

echo "==> Packages"
# Everything from apt: no compiling Pillow on a Pi Zero, and security updates come with apt upgrade.
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends \
  python3 python3-pil python3-requests python3-flask python3-waitress python3-qrcode \
  python3-spidev python3-gpiozero python3-lgpio \
  network-manager dnsmasq-base avahi-daemon rsync

echo "==> SPI on"
if command -v raspi-config >/dev/null; then raspi-config nonint do_spi 0; fi

echo "==> Service user"
id inkcal >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --shell /usr/sbin/nologin inkcal
for g in spi gpio netdev; do getent group "$g" >/dev/null && usermod -aG "$g" inkcal; done

echo "==> App -> $APP"
mkdir -p "$APP" "$DATA" "$ETC"
rsync -a --delete --exclude '__pycache__' "$SRC/inkcal/" "$APP/inkcal/"
chown -R root:root "$APP"
chown -R inkcal:inkcal "$DATA"
chmod 750 "$DATA"

if [[ -f "$SRC/secrets/google_client.json" ]]; then
  echo "==> Google OAuth client -> $ETC/google_client.json"
  install -m 640 -o root -g inkcal "$SRC/secrets/google_client.json" "$ETC/google_client.json"
elif [[ ! -f "$ETC/google_client.json" ]]; then
  echo "!! No secrets/google_client.json yet: the calendar will work up to the Google step." >&2
  echo "!! See docs/GOOGLE_SETUP.md, then run this script again." >&2
fi

echo "==> System config"
install -m 644 "$SRC/system/inkcal.service" /etc/systemd/system/inkcal.service
install -m 644 "$SRC/system/inkcal-firstboot.service" /etc/systemd/system/inkcal-firstboot.service
install -m 644 "$SRC/system/50-inkcal.rules" /etc/polkit-1/rules.d/50-inkcal.rules
mkdir -p /etc/NetworkManager/dnsmasq-shared.d
install -m 644 "$SRC/system/inkcal-captive.conf" /etc/NetworkManager/dnsmasq-shared.d/inkcal-captive.conf

# Don't let Wi-Fi power saving make the web UI sluggish
cat > /etc/NetworkManager/conf.d/inkcal-wifi.conf <<'EOF'
[connection]
wifi.powersave = 2
EOF

systemctl daemon-reload
systemctl enable inkcal-firstboot.service inkcal.service >/dev/null
if [[ ! -f "$DATA/device.json" ]]; then
  systemctl start inkcal-firstboot.service
fi
systemctl restart inkcal.service

HOST=$(python3 -c "import json;print(json.load(open('$DATA/device.json'))['hostname'])" 2>/dev/null || hostname)
echo
echo "Done. Device: $HOST"
echo "  Logs:      journalctl -u inkcal -f"
echo "  Web UI:    http://$HOST.local   (or http://$(hostname -I | awk '{print $1}'))"
if [[ ! -e /dev/spidev0.0 ]]; then
  echo "  NOTE: SPI was just enabled. Reboot once so the display works:  sudo reboot"
fi
