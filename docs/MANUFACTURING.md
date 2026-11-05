# Making many devices

The idea: set up **one** card perfectly, wipe what is unique to that unit, copy the card image to
as many cards as you need. On its first boot each copy gives itself its own identity.

## What is unique per unit (created on first boot)

| Item | Where | Example |
|---|---|---|
| Serial (from the Pi's CPU) | `/var/lib/inkcal/device.json` | `…a1b27f3a` |
| Hostname | system | `calendar-7f3a` |
| Setup Wi-Fi name / password | `device.json` | `Calendar-7F3A` / `k7m2p9xa` |
| Web cookie signing key | `device.json` | random |
| SSH host keys, machine-id | system | random |

Shared by all units: the app (`/opt/inkcal`) and the Google OAuth client (`/etc/inkcal/google_client.json`).

## 1. Build the golden card

1. Follow [INSTALL.md](INSTALL.md) on a fresh card until the calendar works end to end
   (Wi-Fi setup → Google link → calendar shows events → settings).
2. Optional: `sudo apt full-upgrade -y && sudo reboot` so units ship with current security fixes.
3. Wipe this unit's data and power off:
   ```bash
   ssh pi@calendar-xxxx.local
   cd ~/eink-calendar && sudo ./scripts/prepare-golden-image.sh           # test fleet: SSH stays on
   #  or: sudo ./scripts/prepare-golden-image.sh --no-ssh                  # customer units
   ```

## 2. Read the card into an image (on the Mac)

```bash
diskutil list                                   # find the card, e.g. /dev/disk4. Be careful here!
diskutil unmountDisk /dev/disk4
sudo dd if=/dev/rdisk4 of=~/inkcal-golden.img bs=4m status=progress
```

A 64 GB card gives a 64 GB file. Shrink it so it fits any card ≥ 8 GB and expands itself on first boot.
[PiShrink](https://github.com/Drewsif/PiShrink) runs on Linux, so use it inside a Pi or a Linux VM:

```bash
sudo pishrink.sh -z inkcal-golden.img           # -> inkcal-golden.img.gz (~1.5 GB)
```

## 3. Write copies

Use Raspberry Pi Imager → *Use custom* → `inkcal-golden.img.gz` → **No** to "customise settings".
For larger batches, a USB card duplicator or `balenaEtcher` (it can write several cards at once).

## 4. Per-unit check (2 minutes)

1. Insert the card, attach the panel, power on. Within ~1 minute the screen shows **Hello.** with a
   QR code and a unique `Calendar-XXXX` network name.
2. Scan the code with a phone: the setup page opens. That proves the hotspot and captive portal work.
3. Note the `Calendar-XXXX` name on the unit's label / box for support.

## Before shipping to customers

- Google app verification (see GOOGLE_SETUP.md) and the relay page on your own domain.
- Golden image made with `--no-ssh`, or SSH with key-only login.
- Think about: over-the-air updates (today: re-deploy per unit), read-only root file system
  (`raspi-config` → Performance → Overlay FS) to protect SD cards from power cuts, and CE/FCC
  marking for the finished enclosure.
