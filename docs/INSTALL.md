# Installing on the Raspberry Pi

You need: Raspberry Pi Zero 2 WH, Waveshare 7.5" e-Paper HAT (B) V2 (800×480, black/white/red),
a microSD card (8 GB is plenty; your 64 GB is fine), a 5 V micro-USB power supply, and your Mac.

## 1. Connect the display (power off)

1. Plug the HAT board onto the Pi's 40-pin header (the "H" in WH: header already soldered).
   The HAT's pins go over all 40 pins, with the board sitting above the Pi.
2. Connect the panel's flat ribbon cable to the HAT: lift the black latch, slide the cable in
   (contacts facing the board), and press the latch down.
3. If your HAT has small switches: **Interface Config = 0** (4-wire SPI). Leave **Display Config**
   as shipped unless the image looks faded. Waveshare's wiki page for your board says which setting
   your panel revision needs.

## 2. Put Raspberry Pi OS on the card

1. Install **Raspberry Pi Imager** on the Mac (raspberrypi.com/software) and insert the card.
2. *Device:* Raspberry Pi Zero 2 W.
   *OS:* Raspberry Pi OS (other) → **Raspberry Pi OS Lite (64-bit)**. Lite has no desktop, so it boots faster and uses less RAM.
   *Storage:* your SD card.
3. When asked to customise, choose **Edit settings**:
   - Hostname: `calendar-dev`
   - Username / password: e.g. `pi` / a password you'll remember
   - Wi-Fi: your home network (2.4 GHz: the Zero 2 W has no 5 GHz) and your country
   - Locale: your time zone
   - *Services* tab: **Enable SSH** (password authentication is fine for development)
4. Write the card, put it in the Pi and power it on. The first boot takes 2–3 minutes.

## 3. Check you can reach it

```bash
ssh pi@calendar-dev.local
```

If `.local` doesn't resolve, find the Pi's IP address in your router's app and use `ssh pi@<ip>`.
Type `exit` to come back to the Mac.

## 4. Google sign-in (once)

Follow [GOOGLE_SETUP.md](GOOGLE_SETUP.md). It ends with the file `secrets/google_client.json` in this
project. You can skip this step for now: the device works up to the "Link Google" screen without it.

## 5. Install the calendar (from the Mac)

```bash
cd ~/Documents/Projects/eink-calendar
./scripts/deploy.sh pi@calendar-dev.local
```

This copies the project to the Pi and runs `scripts/install.sh` there. That script:
- installs the packages from apt (nothing is compiled on the Pi)
- turns on SPI
- creates the `inkcal` service user
- installs the app to `/opt/inkcal`
- sets up the system services, Wi-Fi permissions and captive portal

**The first time, reboot once so SPI is active:**

```bash
ssh pi@calendar-dev.local sudo reboot
```

On first start the device gives itself a name, for example `calendar-7f3a`. The install script
prints it. From then on, use that name: `ssh pi@calendar-7f3a.local`.

## 6. What you should see

The Pi already knows your Wi-Fi (from Imager), so the display skips the Wi-Fi step and shows
**Link your Google account** with a code. Open the address shown on the screen on your phone,
enter the code, then sign in with Google. A full redraw of the panel takes about 20 seconds.

To try the customer flow (setup hotspot, QR code, Wi-Fi picker), open Settings → *Network & device*
→ **Change**. You can also reset everything with *Factory reset*.

## Updating

Run `./scripts/deploy.sh pi@calendar-7f3a.local` again. Settings, Wi-Fi and sign-in are kept.

## Useful commands (on the Pi)

```bash
journalctl -u inkcal -f              # live log
sudo systemctl restart inkcal        # restart the app
sudo systemctl stop inkcal           # stop it (e.g. to test the panel by hand)
cat /var/lib/inkcal/device.json      # this unit's name and setup-Wi-Fi password
nmcli con show                       # saved networks
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Screen never changes, log says `No such file … spidev0.0` | SPI not active yet: `sudo reboot`. |
| Log: `NativePinFactoryFallback` then `/sys/class/gpio/export … Invalid argument` | gpiozero couldn't use lgpio. Deploy again (the service sets `GPIOZERO_PIN_FACTORY=lgpio` and `LG_WD=/run/inkcal`), and check `dpkg -l python3-lgpio` shows `ii`. |
| Log: `GPIO busy` / `lgpio` errors | Another program uses the display (the old cron job from `raspberry-calendar`?). Remove it: `crontab -e`, `sudo crontab -e`. |
| Image is faint or has a red tint everywhere | Check the ribbon cable is fully in; try the other *Display Config* switch position. |
| New router, or Wi-Fi name/password changed | Wait: after 30 minutes without Wi-Fi the calendar shows the setup screen by itself (10 minutes if you unplug and replug it). Scan the code and pick the new network. If the old network comes back first, the calendar returns to it on its own. |
| Setup Wi-Fi doesn't show up on the phone | Wait a minute after the Welcome screen appears. The Zero 2 W hotspot is 2.4 GHz only. |
| "Google sign-in isn't set up" page | `secrets/google_client.json` missing. See GOOGLE_SETUP.md, then deploy again. |
| After sign-in the phone shows "can't reach page" | The phone must be on the same Wi-Fi as the calendar (not mobile data / VPN). |
