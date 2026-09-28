# legion7-linux-rgb-backlight

Control the RGB lighting of the **Lenovo Legion 7 16ACHg6** (Legion 7 Gen 6, AMD)
on Linux: per-zone colors for the keyboard, logo, vents and neon strip, with
a small GUI and a CLI. Pure Python 3 standard library: no pip packages and
no daemon.

> **Tested on one machine only:** Lenovo Legion 7 16ACHg6, product `82N6`,
> RGB controller ITE `048d:c968`, Ubuntu (GNOME) with kernel 6.18.
> Other Legion models, including other Gen 6 variants like the 7S / `c967`,
> have **not** been tested. The app refuses to run on any other controller ID.

## Contents

- [Features](#features)
- [Check your hardware](#check-your-hardware)
- [Requirements](#requirements)
- [Install](#install)
- [Using the GUI](#using-the-gui)
- [Using the CLI](#using-the-cli)
- [Restore on login](#restore-on-login)
- [Uninstall](#uninstall)
- [How it works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Notes and limitations](#notes-and-limitations)
- [Credits and license](#credits-and-license)

## Features

- 4 independently colored zones: **Keyboard**, **Logo**, **Vents**, **Neon strip**
- Preset colors (White, Red, Orange, Yellow, Green, Cyan, Sky blue, Blue,
  Purple, Pink, Off) or any custom color
- Static and software **Breath** effect, adjustable brightness and speed
- One click back to the built-in firmware effects (Fn+Space)
- Remembers your last setting and can restore it at login

## Check your hardware

```bash
lsusb | grep 048d
# Bus 001 Device 005: ID 048d:c968 Integrated Technology Express, Inc. ITE Device(8258)

cat /sys/class/dmi/id/product_version
# Legion 7 16ACHg6
```

If you do not see `048d:c968`, this tool is not for your laptop. For
many other Legion models, try [OpenRGB](https://openrgb.org),
[L5P-Keyboard-RGB](https://github.com/4JX/L5P-Keyboard-RGB) or
[LenovoLegionLinux](https://github.com/johnfanv2/LenovoLegionLinux).

## Requirements

- Python 3.8+ with Tkinter (for the GUI): `sudo apt install python3-tk`
- `pkexec` (policykit), only if you skip the udev rule
- A Linux kernel with `hidraw`. Every normal distro kernel has it.

## Install

```bash
git clone https://github.com/irfahlevi/legion7-linux-rgb-backlight.git
cd legion7-linux-rgb-backlight
./install.sh              # udev rule + app-menu launcher
# or
./install.sh --autostart  # same, plus restore your colors at every login
```

`install.sh` asks for your sudo password once, to copy
`99-legion-rgb.rules` into `/etc/udev/rules.d/`. That rule lets your user
write to the RGB controller, so you never need sudo again.

Do not move the folder after installing: the launcher points at it. If you
do move it, run `./install.sh` again.

You can also skip installing entirely and run `./legion-rgb-gui` from the
folder. Without the udev rule, each Apply asks for your password through
pkexec, and Breath is unavailable.

## Using the GUI

Open **Legion Backlit RGB** from the app menu, or run:

```bash
./legion-rgb-gui
```

1. **Zone colors:** pick a color from each zone's dropdown. Choose **Custom**
   or click the color square for any color.
   **All zones** sets every zone at once.
2. **Effect:** Static or Breath.
3. **Brightness %** and **Breath speed** (1 = slow, 4 = fast).
4. Press **Apply**. Nothing changes on the laptop until you do.

Other buttons:
- **Off:** all LEDs off.
- **Firmware effects:** hands lighting back to the laptop's built-in effects.

Breath only runs while the GUI window is open. It is animated by the app,
not by the firmware.

## Using the CLI

```bash
./legion-rgb-cli status                               # detected controller + last setting
./legion-rgb-cli static FF0000                        # everything red
./legion-rgb-cli static 00FF00 FFFFFF FF0000 FFFF00   # keyboard, logo, vents, neon strip
./legion-rgb-cli static FFFFFF -b 40                  # white at 40% brightness
./legion-rgb-cli breath 00BFFF -s 2                   # breathe; Ctrl+C stops and keeps the color
./legion-rgb-cli identify                             # light each zone in turn
./legion-rgb-cli off                                  # all LEDs off
./legion-rgb-cli hardware                             # back to firmware effects
```

Colors are `RRGGBB` hex, with or without a leading `#`. Give either 1 color
(all zones) or 4 colors in the order keyboard, logo, vents, neon strip.
Without the udev rule, prefix commands with `pkexec`.

## Restore on login

The last setting is saved to `~/.config/legion-rgb/last.json` whenever you
apply. `./install.sh --autostart` adds a login entry that runs
`legion-rgb-restore`, which re-applies it. A saved Breath effect keeps
running in the background. Login restore needs the udev rule, because there
is no password prompt at login.

## Uninstall

```bash
./install.sh --uninstall
```

This removes the udev rule, launcher and autostart entry. Then delete the
folder, and optionally `~/.config/legion-rgb/`.

## How it works

The controller is an ITE 8258 exposed as `/dev/hidrawN`. Every command is a
192-byte HID **SET_FEATURE** report with ID `0x07`:

| Packet | Meaning |
|---|---|
| `07 B2 00…` | **Software mode:** firmware displays colors sent by the host |
| `07 B1 00…` | **Hardware mode (global):** firmware effects on all zones (`legion-rgb-cli hardware` / GUI Firmware effects) |
| `07 <zone> <N> 00 (led, R, G, B)×N` | Set N LEDs in a zone, up to 47 per packet |

| Zone byte | Area | LEDs |
|---|---|---|
| `A1` | Keyboard | per-key IDs, up to 0xA8 |
| `A2` | Logo | 1–13 |
| `A3` | Vents (left, right, back) | 1–106 |
| `A4` | Neon strip | 1–99 |

`07 B2` is the key step. Without it the firmware ignores or quickly
overwrites host colors. Brightness is applied in software by scaling RGB.

`Fn+Space` is **not** the same as `07 B1`. It is handled by the EC and
cycles the **keyboard zone** through firmware modes (off, wave/animation,
full-device wave), while other zones keep showing the last host frame.
Zones therefore desync after `Fn+Space` (e.g. keyboard cycling while other
zones stay frozen). The full-device firmware wave (rotating rainbow)
reclaims keyboard, vents and neon strip — vents/strip then settle to
rainbow static — but the **logo has been observed to stay on the last host
color** even through that wave. This is EC behavior, not a send bug.
Recovery: press **Apply** to re-assert `07 B2` on all zones, or **Firmware
effects** / `legion-rgb-cli hardware` for a clean global `07 B1`
(verified: `hardware` returns all zones, logo included, to the rotating
rainbow firmware effect — unlike `Fn+Space`, which leaves the logo stuck).
Breath
re-asserts `07 B2` every frame so it retakes the keyboard within ~50 ms;
Static stays apply-and-exit by design (no daemon).

Layout:

```
legion-rgb-gui          Tkinter GUI
legion-rgb-cli          command line
legion-rgb-restore      re-apply last setting (login autostart)
install.sh              udev rule + launcher + icon + autostart
99-legion-rgb.rules     udev rule (hidraw 048d:c968 → user-writable)
assets/icon-*.png       app icon (48/64/128/256 px)
tools/make_icon.py      regenerates the icon (needs Pillow; dev only)
legion_rgb/
  detector.py           finds /dev/hidrawN for 048d:c968
  hid.py                hidraw SET_FEATURE ioctl
  protocol_direct.py    packets, zones, LED IDs, breath loop
  privilege.py          pkexec helper, real-user config dir under pkexec
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `No ITE 048d:c968 controller found` | Not a 16ACHg6, or the device is absent. Check `lsusb \| grep 048d`. |
| `Permission denied on /dev/hidrawN` | Run `./install.sh`, or prefix CLI commands with `pkexec`. |
| GUI does not start: `No module named tkinter` | `sudo apt install python3-tk` |
| Colors reset after Fn+Space | Fn+Space cycles keyboard-zone firmware modes; other zones keep the last host frame, so zones desync. Press Apply to retake all zones (`07 B2`), or Firmware effects / `hardware` for a clean global `07 B1`. |
| Colors gone after reboot | Boot shows a circling rainbow, then the firmware default (static blue on the tested machine) when no autostart is installed. Use `./install.sh --autostart`, or re-apply manually. |
| One zone does not change | Run `./legion-rgb-cli identify` and check which zones light. Please open an issue with the result. |

## Notes and limitations

- **Single-machine testing.** Verified on the hardware listed at the top:
  all four zones, preset and custom colors, per-zone colors, brightness,
  Breath, Off and hardware mode. Not verified: behavior across
  suspend/resume and full reboots, ISO or JP keyboard layouts, and other
  Legion models.
- **Keyboard LED IDs** are the union of OpenRGB's ANSI, ISO and JP maps
  for this model, so any layout should light fully. Sending IDs for keys
  that a layout lacks caused no problems on the tested machine.
- **Brightness** is software-scaled RGB. The hardware brightness level
  (Fn+Space / firmware) is not changed.
- **Fn+Space desync is expected.** The EC drives the keyboard zone;
  `07 B2` host frames are RAM-only and never saved to firmware. Returning
  to firmware static (via `Fn+Space` or reboot without autostart) shows the
  firmware slot (e.g. static blue), not your last software color.
- **No per-key GUI** yet. The protocol supports per-key colors, but the app
  only exposes the 4 zones.
- **Lenovo Vantage / Legion Toolkit** do not exist on Linux, but if you
  dual-boot, the Windows lighting app may take control back after you boot
  Windows.
- **Safety:** the app only sends lighting reports to the RGB controller. It
  does not touch the EC, BIOS, fan or power settings. The worst case is
  wrong colors, fixed with `./legion-rgb-cli hardware` or a reboot.
- Not affiliated with or endorsed by Lenovo. Use at your own risk.

## Credits and license

- Protocol and LED maps from [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB)'s
  `LenovoUSBController` (Lenovo Legion 7 Gen 6 / Y760 support).
- Early protocol hints from OpenRGB issue #1635 USB captures and
  [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit).

Licensed under **GPL-2.0-or-later** (see `LICENSE`), matching OpenRGB, from
which the LED tables are derived.
