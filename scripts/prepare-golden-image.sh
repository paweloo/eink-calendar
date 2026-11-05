#!/usr/bin/env bash
# Turn a fully installed, tested Pi into a "golden" SD card that can be cloned.
# Run ON THE PI as root. It wipes everything specific to this unit and powers off.
#   sudo ./scripts/prepare-golden-image.sh            keep SSH enabled (for your own test fleet)
#   sudo ./scripts/prepare-golden-image.sh --no-ssh   for units you ship to customers
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

DISABLE_SSH=0
[[ "${1:-}" == "--no-ssh" ]] && DISABLE_SSH=1

read -r -p "This erases Wi-Fi, Google sign-in and identity on THIS card and powers off. Type GOLDEN: " ok
[[ "$ok" == "GOLDEN" ]] || { echo "Cancelled."; exit 1; }

systemctl stop inkcal.service || true

echo "==> Per-device data"
rm -rf /var/lib/inkcal/*

echo "==> Saved Wi-Fi networks"
nmcli -t -f NAME,TYPE con show | awk -F: '$2=="802-11-wireless"{print $1}' | while read -r c; do
  nmcli con delete "$c" || true
done
rm -f /etc/NetworkManager/system-connections/*

echo "==> Machine identity (regenerated on next boot)"
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
hostnamectl set-hostname calendar-new
sed -i '/^127.0.1.1/d' /etc/hosts && echo -e "127.0.1.1\tcalendar-new" >> /etc/hosts

if [[ $DISABLE_SSH -eq 1 ]]; then
  echo "==> SSH off"
  systemctl disable ssh.service || true
fi

echo "==> Logs and history"
journalctl --rotate && journalctl --vacuum-time=1s
rm -f /root/.bash_history /home/*/.bash_history
apt-get clean

systemctl enable inkcal-firstboot.service
sync
echo "Golden image ready. Powering off; then clone the card (docs/MANUFACTURING.md)."
sleep 2
poweroff
