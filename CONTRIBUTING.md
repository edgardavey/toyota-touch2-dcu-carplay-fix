# Contributing

This project exists because the official community thread for this exact DCU/MEU
hardware family never fully resolved two things that turned out to matter a lot: a
hang that failed every attempt until `phaseup.dat` was removed, and an installer that
silently flashes the wrong (non-CarPlay) firmware file by filename match. If you hit
something similar on hardware not yet listed here, this project only gets more useful
by growing the compatibility data and the fix list.

## Reporting a new confirmed (or broken) variant

Open an issue or PR with:
- Exact **Model ID** and **Parts No.** for both DCU and MEU, read from the unit's own
  Model Information screen (Setup → Software Update → Model info), not guessed from a
  parts catalog.
- Audio build number **before and after** the DCU update.
- Whether CarPlay actually triggered on phone plug-in afterward (plug in, don't just
  check the Apps menu for an icon — see README's note on why).
- Which fixes from README.md you needed (maybe you only needed one, not both — that's
  useful data too).
- If something went differently than README describes: the exact on-screen error text
  and log lines, and what state the unit ended up in (did it recover with a power cycle?).

PRs adding an entry to `compatibility.json` are welcome — follow the existing schema.
Entries you're not fully sure about belong in `unconfirmed_or_open`, not
`confirmed_variants` — keep the distinction between "I tested this" and "I read this
somewhere" clear, the same way the README does.

## Working on `patcher.py`

Dependency-free standard library Python 3 only, on purpose — this needs to run on
whatever a random contributor happens to have installed, with nothing to trust besides
what's visible in the one file. Keep it that way: no pip packages, no network access,
no implicit destructive actions without a backup made first.

If you add a new subcommand, follow the existing pattern: back up before any write or
delete, log every action with a timestamp, and never silently overwrite an existing
backup (require `--force`).

## What this project will not do

- Host, link, or help source Toyota's actual firmware files. Describe the method,
  point to where the community already sources files, nothing more.
- Add anything that bypasses signature verification, forges Toyota's signing keys, or
  claims to produce "custom firmware." Everything here works by influencing which of
  Toyota's own already-signed files gets selected — that distinction matters and should
  stay true of anything added here.
- Encourage running untested code against a car that's someone's daily driver. The
  parked filesystem-scan research thread in README.md is intentionally left as
  "documented, not attempted" — if you pick it up, test on a bench/spare unit first and
  report back, don't just merge a script that was never run against the real hardware.
