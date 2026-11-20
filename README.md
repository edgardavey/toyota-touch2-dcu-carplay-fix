<div align="center">

# 🚗 OpenTouch2

### Reviving Toyota's Touch 2 head units — starting with CarPlay, aiming at a fully open OS

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CarPlay](https://img.shields.io/badge/CarPlay-confirmed%20working-brightgreen.svg)](#fix-2--the-installer-picks-the-wrong-firmware-file-by-filename-not-by-best-available)
[![Patcher](https://img.shields.io/badge/patcher-python%203%2C%20zero%20deps-blue.svg)](patcher.py)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](CONTRIBUTING.md)

</div>

---

**toyota-touch2-dcu-carplay-fix** — DIY writeup and tooling for getting Apple CarPlay working on a
**2020 Toyota RAV4 Hybrid FWD (EU)** with a Panasonic **DCU 17TDT2EU-DA01** (part `86140-42571`) and Harman
**MEU 17TMT2EU-FA00→FA10** (part `86840-06041`→`86840-K0010`), using Toyota's own official retrofit files — no
hex editing, no signature forging.

This covers the same DCU/MEU hardware family used across the **2019–2020 RAV4, Corolla, and Camry EU/Touch 2
line** (Panasonic 8" display, Harman MEU). If your unit matches the Model ID strings in `compatibility.json`,
this should apply to you too — and if it doesn't yet, that's exactly what this project wants PRs for.

**Result: full CarPlay, confirmed working.** Phone, Maps, Messages, Spotify, Podcasts, the works — no standing
CarPlay icon needed, it launches automatically when a phone is plugged in.

> ⚠️ **Disclaimer:** this modifies safety-adjacent vehicle electronics outside any Toyota-sanctioned process.
> It may void your warranty, may interact badly with a unit that doesn't exactly match the hardware below, and
> I am not responsible for anything that happens to your car. Back up your current state (photograph every
> version/model screen before touching anything) and don't attempt this if you're not comfortable debugging a
> stuck software update yourself. No units were bricked in the making of this guide, but recovery always meant
> following the official error-code table (power cycle, retry) — have that patience before you start.

## Hardware this applies to

| Field | Value |
|---|---|
| Model ID DCU | `17TDT2EU-DA01` |
| Model ID MEU | `17TMT2EU-FA00` (before) / `17TMT2EU-FA10` (after MEU update) |
| Parts No. DCU | `86140-42571` |
| Parts No. MEU | `86840-06041` → `86840-K0010` |
| Manufacturer | Panasonic (DCU) / Harman International (MEU) |
| Chassis codes in scope | RAV4 `AXAH52`, `AXAH54`, `MXAA52`, `MXAA54`; Corolla `ZRE210`, `ZWE211` |

The official Toyota Maintenance Bulletin covering this retrofit is **`BE-00439T-TME`, Version 4, 18 Sep 2020**
("Toyota RAV4 with navigation system, Corolla SD/HB/TS... (with Panasonic, Harman) - Retrofit"). It documents
converting CY17 → CY17Plus (17MM → 19MM) software via three USB drives, which is what actually enables
CarPlay/Android Auto — this isn't a hack of the hardware, it's Toyota's own real retrofit path, just without a
dealer in the loop.

## Credit where it's due

This build on top of community research, principally the Toyota Owners Club thread
["2020 Camry Software Update - Apple CarPlay in EU"](https://www.toyotaownersclub.com/forums/topic/193487-2020-camry-software-update-apple-carplay-in-eu/)
(user `Alcar` and many contributors across 27+ pages), which documents the equivalent process for the Camry
variant of this same DCU/MEU family. The two fixes below are things that thread didn't fully resolve for this
exact DCU model/part number — found by actually inspecting the files on the official USB packages rather than
just following the steps blind.

**I don't host or link the actual Toyota firmware files here.** They're Toyota's proprietary, signed firmware —
source them the way the community thread above describes (official bulletin links when live, or ask around in
that thread), then apply the fixes below.

## The process, in order

1. **USB1 → USB2 → USB1 again** (official MEU update sequence). Takes MEU from `FA00` → `FA10`. Don't skip or
   reorder — the unit holds its place in this sequence across power cycles.
2. **Fix #1 below**, applied to the USB3 drive.
3. **Fix #2 below**, applied to the same USB3 drive.
4. Insert USB3, go to Setup → Software Update, confirm. Let it run — it may restart multiple times, don't
   remove the USB or power off until it says the install is complete.
5. **Run "Delete personal data"** (Setup menu) — confirmed *required*, not just a formality (see below).
6. Test CarPlay with a cable that actually carries data (see cable note below).

## Using `patcher.py` instead of doing it by hand

Both fixes below can be applied with the included dependency-free Python 3 script, which
always backs up before touching anything and can undo itself:

```bash
python3 patcher.py scan /Volumes/USB3          # read-only - shows flag files and kwi versions
python3 patcher.py remove-flags /Volumes/USB3  # Fix #1
python3 patcher.py swap-kwi /Volumes/USB3 \
    --target 17TDT2EU-DA01_7910.kwi --source 17TDT2EU-DA31_7910.kwi   # Fix #2

# if you need to undo either step:
python3 patcher.py restore /Volumes/USB3
```

Run `python3 patcher.py --help` for full usage. `scan` is read-only and safe to run on
any drive just to see what's there. See `compatibility.json` for which filenames apply
to your exact hardware before running `swap-kwi`.

## Fix #1 — delete `phaseup.dat` from the USB3 drive root

Every attempt without this fix reached 99%, logged `Sequence/Dcu Commit finished` → `[REPRO]Vup Completed`,
then immediately failed with `DCU Error0128` and a red **"Update failed... Error code: 001"** screen. The main
firmware write always succeeded; the failure was always in the step right after — the vehicle-parameter commit.
Power-cycling always recovered the unit cleanly back to its pre-flash state — never bricked, but never
progressed either.

The Camry community thread has a note from `Alcar`: *"The first time I did not delete the phaseup.dat file and
it gave me the error with red screen error 01."* That "error 01" matches this unit's "Error code: 001" closely
enough to be the same thing.

`phaseup.dat` (and its siblings `force_clear_dcu.dat`, `forcevup.dat`) on the official USB3 package are **0-byte
empty files** — presence/absence flags, not data. Best working theory (not confirmed by any official Toyota
doc): the file's presence tells the installer "this is a staged/multi-phase update, expect a second phase" — a
phase a real dealer TechDoc tool supplies but a standalone USB flash never does, so the commit step hangs
waiting for it.

**Fix:** back up `phaseup.dat`, then delete it from the USB3 drive root. Result: the DCU update completes
cleanly — "New software installation is completed," no error.

## Fix #2 — the installer picks the wrong firmware file by filename, not by "best available"

After Fix #1, the DCU update completes with no error, but lands on **Audio build `1020`** — no CarPlay,
SmartDeviceLink still present. Checked the actual version strings embedded in the two DCU firmware files sitting
side by side on the official USB3 package:

| File | Size (bytes) | Embedded version |
|---|---|---|
| `17TDT2EU-DA01_7910.kwi` | 366,885,305 | `01020` |
| `17TDT2EU-DA31_7910.kwi` | 410,342,331 | `01023` |

This matches the community thread exactly: *"The version 1020 has no carplay. The version 1023 has carplay."*
Both files are present on the official package, but **the installer selects which one to flash purely by
matching the filename against the unit's current Model ID** (`17TDT2EU-DA01`) — so it always picks the `1020`
file and never touches the `1023` file sitting right next to it, because the unit never "becomes" `DA31` on its
own. (Checked `ModelIdList.xml` on the drive — it only governs MEU model selection, nothing about DCU, so this
isn't something that file controls.)

**Fix:** back up the original `17TDT2EU-DA01_7910.kwi`, then replace its content with the content of
`17TDT2EU-DA31_7910.kwi`, **keeping the original `DA01` filename**. Leave the real `DA31` file in place too,
untouched, as a reference copy. This is the same trick the community thread calls "rename DA31 → DA01" — done
here as a content swap so the original filename (which the installer actually keys off) ends up containing the
`1023` payload.

**Result:** full success — the most thorough install of the whole project, individually writing modules never
touched by the `1020`-only path (AMIGO, SYS, CAN, NOR, UBOOT, SECURE), committing MAIN in a 3-module pass, and
finishing clean with **`Audio: 1023`** confirmed.

## The step that's easy to skip but isn't optional: Delete personal data

After the flash, a phone plugged in **did not** trigger CarPlay. Only after running **Setup → Delete personal
data** (wipes paired Bluetooth/contacts/saved addresses, doesn't touch firmware) did CarPlay start working on
the very next plug-in.

**If CarPlay doesn't trigger right after the DCU flash, run this before concluding anything else is wrong.**
Likely explanation: stale pairing/device-recognition data left over from before the update was blocking CarPlay
from recognizing the phone as new.

## Cable note

Newer iPhones (15+) are USB-C; this generation of Toyota Touch 2 has a USB-A port. CarPlay requires an
MFi-certified connection (an authentication chip lives in the cable) — a charge-only or non-MFi adapter can
silently block CarPlay even with perfectly correct firmware. If you're bridging USB-C to USB-A, test the
adapter on a computer first (does Finder/Photos recognize the phone through it?) before concluding the firmware
is at fault.

## Other things that turned out *not* to matter

- `Model ID DCU` still reads `17TDT2EU-DA01` after the flash — expected, that field reflects the
  hardware/compatibility family, not the internal build number.
- No standing CarPlay/Android Auto icon ever appears in the Apps menu on this platform — it activates only on
  phone plug-in. Don't take its absence as a sign something's wrong.
- "Toyota Online is not enabled" in the Apps menu is unrelated — that's Toyota's separate telematics service
  needing an online account, nothing to do with CarPlay.
- Reinserting USB2 after the DCU update, chasing the bulletin's "RC 2002+ / removes SmartDeviceLink" step,
  turned out to be a dead end for this package — it only contains an already-superseded MEU file, no separate
  SDL-removal payload. SmartDeviceLink is still present and cosmetically harmless; what actually removes it (if
  anything in this exact package does) is still unresolved.

## Error-code quick reference

If you're mid-flash and hit a red screen, don't panic — check this first:

| Symptom | Likely cause / fix |
|---|---|
| `Error code: 001` right after `[REPRO]Vup Completed` at 99% | `phaseup.dat` still present on USB3 — delete it, retry (Fix #1) |
| Install completes clean but stuck on Audio `1020`, no CarPlay | Installer picked the wrong firmware file by filename — apply Fix #2 |
| Anything else, codes 001–008 | Official bulletin's own guidance: power cycle the engine off/on, retry; if unresolved, the bulletin indicates possible part replacement |

## Open research thread (not attempted, documented for whoever wants to pick it up)

While investigating the above, I found that `Full_upgrade_package_Toyota_USB1/intervention/intervention_script.sh`
— a file shipped in the official USB1 package — is a plain, **unsigned shell script that the DCU executes as
root directly off the USB drive** during the update flow. It only MD5-checks the *other* files it references,
never itself. This is genuine, confirmed root code execution on the live, already-running OS (no secure-boot
bypass needed — it rides on top of the OS's own already-verified boot).

Its real logic does actual disk surgery (partition deletion/recreation via `fdisk`, raw `dd` replication of
kernel+rootfs between A/B banks, a direct write to the eMMC's bootloader region) gated by on-device flag files
we can't inspect remotely — not something to experiment with on a working unit.

A **read-only** variant, that never calls any of that destructive logic and only reads/reports, would look
like this (untested — the one real unknown is whether the on-device launcher that detects a USB1-shaped drive
does anything independent of the script's own content, before even running it):

```sh
#!/bin/sh
mkdir -p /DCU/USB0/report
find / -xdev -maxdepth 8 > /DCU/USB0/report/filelist.txt 2>/dev/null
dmesg > /DCU/USB0/report/dmesg.txt 2>/dev/null
systemctl list-units --all > /DCU/USB0/report/services.txt 2>/dev/null
cp /etc/Toyota_CY17.XML /DCU/USB0/report/ 2>/dev/null
ls -la /etc /usr/bin > /DCU/USB0/report/dirs.txt 2>/dev/null
sync
```

If run, `dmesg` would likely settle whether NXP i.MX6 HABv4 secure boot is actually enforced on this unit
(confirmed hardware: i.MX6Q, SABRE-SD reference board, U-Boot 2009.08, Yocto/Automotive-Grade-Linux-based), and
the service/file listing could reveal SmartDeviceLink's actual service name (for a targeted removal) and
possibly other region-locked features unlockable the same way CarPlay was. If anyone with a spare/bench unit
wants to try this safely, PRs/issues welcome.

## Sources

- [Toyota Owners Club: "2020 Camry Software Update - Apple CarPlay in EU"](https://www.toyotaownersclub.com/forums/topic/193487-2020-camry-software-update-apple-carplay-in-eu/)
- [Toyota Owners Club: "Retro Fit Apple Carplay & Android Auto"](https://www.toyotaownersclub.com/forums/topic/195353-retro-fit-apple-carplay-android-auto/) (Corolla)
- Toyota Maintenance Bulletin `BE-00439T-TME`, Version 4, 18 Sep 2020

## Right to repair

This is Toyota's own official retrofit software, applied without a dealer in the loop.
Nothing here forges a signature, decrypts protected firmware, or writes code Toyota
didn't already write and sign themselves — the fixes are about *which* of Toyota's own
already-signed files gets selected, not about replacing them with something new. A device
you own, past its warranty, with a manufacturer-built upgrade path that a dealer visit
would otherwise gatekeep behind a fee, is a reasonable thing to be able to fix and improve
yourself. Contributions that grow the hardware-compatibility list (`compatibility.json`)
or make `patcher.py` more broadly useful are welcome — see `CONTRIBUTING.md`.

## The bigger goal: an open OS for these DCUs

CarPlay was the first concrete, achievable milestone — not the ceiling. The actual ambition behind this
project is bigger: **full control of this hardware, eventually running a community-built, open-source OS
instead of Toyota's own stack.** These are capable automotive-grade ARM boards (NXP i.MX6Q, confirmed) sitting
behind years of manufacturer bloat and feature-gating; stripped down and running something purpose-built, they're
very likely capable of a lot more than Toyota ever lets them do. Fully open firmware that anyone can read, audit,
extend, and flash — the same spirit as this project's CarPlay fix, just aimed much further out.

**Being honest about where that actually stands today — this is a real wall, not a small gap:** the DCU boots
via NXP's HABv4 secure boot, verified against an **OTPMK key physically fused into each individual chip's
silicon** at manufacture. Nobody can make this chip boot genuinely custom code unless it's signed with
Toyota/Panasonic's own private key, which isn't obtainable through anything short of compromising their
manufacturing infrastructure — a different problem than anything this project does or should pursue. Everything
achieved so far (CarPlay included) works by influencing *which of Toyota's own already-signed files* gets
selected, never by running unsigned code of our own.

**One thing that would genuinely change the picture, if it turned out to be true:** whether secure boot is
actually *enforced* (fused closed) on these specific units, versus left open on some production run — it varies
by manufacturer and isn't universal (a 2020 Lexus NX300 teardown by Tencent Keen Lab found no secure boot active
on a comparable-generation unit from a different maker, for reference — not evidence either way for this exact
hardware). **Nobody has checked this for the Panasonic Touch 2 DCU yet.** The parked research thread above (a
safe, read-only filesystem/`dmesg` scan via USB, never tested against real hardware) is the actual first step
toward finding out — not a custom OS itself, just the one piece of missing evidence that tells us whether that
door is closed for good or worth pursuing further. If you have embedded security, automotive ECU, or i.MX6
background and want to help answer that question on a bench unit, this is where to start.

## For AI agents

See [`llms.txt`](llms.txt) for a structured summary of this repo and guidance on how to
help someone apply this fix safely.
