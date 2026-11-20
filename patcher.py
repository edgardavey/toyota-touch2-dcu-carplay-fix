#!/usr/bin/env python3
"""
toyota-touch2-dcu-carplay-fix patcher

A small, dependency-free toolkit for applying the two fixes documented in
README.md to an official Toyota USB3 retrofit drive (mounted volume or a
plain extracted folder - both work, since macOS/Linux expose a mounted USB
drive as an ordinary directory).

This tool never downloads, embeds, or redistributes any Toyota firmware.
It only inspects and rearranges files you already legally obtained yourself,
and it backs up everything before touching it.

Commands:
  scan          Report drive structure, flag files present, and the embedded
                version string of every .kwi firmware file found.
  remove-flags  Back up and delete phaseup.dat (the flag file behind the
                Error0128 / "Error code: 001" hang). Use --all to also
                remove force_clear_dcu.dat and forcevup.dat (NOT confirmed
                necessary - only phaseup.dat is confirmed required).
  swap-kwi      Back up TARGET, then replace its content with SOURCE's
                content while keeping TARGET's filename. This is how you
                get the installer (which selects firmware purely by
                filename match against the unit's current Model ID) to
                flash a different, higher-version payload.
  restore       Restore every file backed up in a given backup directory
                back to its original location.

Every destructive action is logged with a timestamp to patch-log.txt in
the backup directory, and nothing is ever deleted or overwritten without
a backup copy made first.

Example (matches the exact fix in README.md for DCU 17TDT2EU-DA01):
    python3 patcher.py scan /Volumes/USB3
    python3 patcher.py remove-flags /Volumes/USB3
    python3 patcher.py swap-kwi /Volumes/USB3 \\
        --target 17TDT2EU-DA01_7910.kwi --source 17TDT2EU-DA31_7910.kwi
    # ... flash the unit ...
    # if something looks wrong and you want the originals back:
    python3 patcher.py restore /Volumes/USB3 --backup-dir /Volumes/USB3/.patcher-backup
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys

FLAG_FILES = ["phaseup.dat", "force_clear_dcu.dat", "forcevup.dat"]
VERSION_RE = re.compile(rb"([0-9]{5})dummy signature")


def log(backup_dir: str, message: str) -> None:
    os.makedirs(backup_dir, exist_ok=True)
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {message}"
    print(line)
    with open(os.path.join(backup_dir, "patch-log.txt"), "a") as f:
        f.write(line + "\n")


def default_backup_dir(usb_path: str) -> str:
    return os.path.join(usb_path, ".patcher-backup")


def read_embedded_version(kwi_path: str) -> str | None:
    """Reads the 5-digit version string these Toyota .kwi containers embed
    in plaintext right before the repeated 'dummy signature' placeholder
    block in the header. Returns None if the pattern isn't found (older/
    different container format, or not actually a kwi of this family)."""
    try:
        with open(kwi_path, "rb") as f:
            head = f.read(4096)
    except OSError as e:
        return None
    m = VERSION_RE.search(head)
    return m.group(1).decode() if m else None


def cmd_scan(args: argparse.Namespace) -> int:
    path = args.path
    if not os.path.isdir(path):
        print(f"Error: {path} is not a directory (mount the USB drive or point at an extracted folder)")
        return 1

    print(f"Scanning {path}\n")

    # Free space, if this is a real mounted volume
    try:
        usage = shutil.disk_usage(path)
        gb = usage.total / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        print(f"Volume size: {gb:.1f} GB total, {free_gb:.1f} GB free")
        if gb < 15:
            print("  Warning: the official bulletin's USB3 drive is specced ~32GB. "
                  "This volume looks smaller than that - check it's the right drive.")
        print()
    except OSError:
        pass

    print("Flag files (presence of phaseup.dat is the one confirmed to cause Error0128 / 'Error code: 001'):")
    for name in FLAG_FILES:
        p = os.path.join(path, name)
        if os.path.isfile(p):
            size = os.path.getsize(p)
            note = "" if size == 0 else f"  (NOTE: non-zero size, {size} bytes - unexpected, inspect before removing)"
            print(f"  [present] {name}{note}")
        else:
            print(f"  [absent]  {name}")
    print()

    print("DCU firmware files found (.kwi), with embedded version if readable:")
    found_any = False
    for entry in sorted(os.listdir(path)):
        if entry.lower().endswith(".kwi") and not entry.startswith("._"):
            found_any = True
            full = os.path.join(path, entry)
            ver = read_embedded_version(full)
            size = os.path.getsize(full)
            ver_str = ver if ver else "(not found in header - different container format?)"
            print(f"  {entry:40s} {size:>12,} bytes   version: {ver_str}")
    if not found_any:
        print("  (none found at top level - check PreInstall/ or you're pointed at the wrong drive)")
    print()
    print("Tip: the file with the HIGHER embedded version number but a filename that does NOT match your "
          "unit's current Model ID (read from Setup -> Software Update -> Model info on the unit itself) "
          "is very likely the one you want 'swap-kwi' to inject under the currently-selected filename.")
    return 0


def cmd_remove_flags(args: argparse.Namespace) -> int:
    path = args.path
    backup_dir = args.backup_dir or default_backup_dir(path)
    targets = FLAG_FILES if args.all else ["phaseup.dat"]

    removed_any = False
    for name in targets:
        src = os.path.join(path, name)
        if not os.path.isfile(src):
            log(backup_dir, f"SKIP: {name} not present at {path}")
            continue
        os.makedirs(backup_dir, exist_ok=True)
        dst = os.path.join(backup_dir, name + ".bak")
        shutil.copy2(src, dst)
        log(backup_dir, f"BACKUP: {src} -> {dst}")
        os.remove(src)
        log(backup_dir, f"DELETE: {src}")
        removed_any = True

    if not removed_any:
        log(backup_dir, "Nothing to remove - none of the targeted flag files were present.")
    else:
        log(backup_dir, "Done. Backups saved; use 'restore' to undo if needed.")
    return 0


def cmd_swap_kwi(args: argparse.Namespace) -> int:
    path = args.path
    backup_dir = args.backup_dir or default_backup_dir(path)
    target = os.path.join(path, args.target)
    source = os.path.join(path, args.source)

    if not os.path.isfile(target):
        print(f"Error: target file not found: {target}")
        return 1
    if not os.path.isfile(source):
        print(f"Error: source file not found: {source}")
        return 1

    target_ver = read_embedded_version(target)
    source_ver = read_embedded_version(source)
    print(f"Target (will be overwritten, filename kept): {args.target}  current version: {target_ver}")
    print(f"Source (content copied in):                   {args.source}  version: {source_ver}")
    if target_ver and source_ver and target_ver == source_ver:
        print("Warning: both files report the same embedded version - this swap may not do anything useful. "
              "Double-check with 'scan' before proceeding.")
    if not args.yes:
        reply = input("Proceed with this swap? [y/N] ").strip().lower()
        if reply != "y":
            print("Aborted.")
            return 1

    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, os.path.basename(args.target) + ".bak")
    if os.path.exists(backup_path) and not args.force:
        print(f"Error: a backup already exists at {backup_path} (probably already patched once). "
              "Use --force to overwrite the existing backup, or 'restore' first.")
        return 1

    shutil.copy2(target, backup_path)
    log(backup_dir, f"BACKUP: {target} -> {backup_path}")
    shutil.copy2(source, target)
    log(backup_dir, f"SWAP: copied content of {source} into {target} (filename preserved)")
    log(backup_dir, "Done. Backup saved; use 'restore' to undo if needed.")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    path = args.path
    backup_dir = args.backup_dir or default_backup_dir(path)
    if not os.path.isdir(backup_dir):
        print(f"Error: no backup directory found at {backup_dir}")
        return 1

    restored_any = False
    for entry in sorted(os.listdir(backup_dir)):
        if not entry.endswith(".bak"):
            continue
        original_name = entry[: -len(".bak")]
        dst = os.path.join(path, original_name)
        src = os.path.join(backup_dir, entry)
        shutil.copy2(src, dst)
        log(backup_dir, f"RESTORE: {src} -> {dst}")
        restored_any = True

    if not restored_any:
        print(f"No .bak files found in {backup_dir}")
        return 1
    log(backup_dir, "Restore complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Report drive structure, flag files, and kwi versions")
    p_scan.add_argument("path", help="Path to the mounted USB3 drive or extracted folder")
    p_scan.set_defaults(func=cmd_scan)

    p_rm = sub.add_parser("remove-flags", help="Back up and delete phaseup.dat (fixes Error0128 / 'Error code: 001')")
    p_rm.add_argument("path")
    p_rm.add_argument("--backup-dir", help="Where backups go (default: <path>/.patcher-backup)")
    p_rm.add_argument("--all", action="store_true",
                       help="Also remove force_clear_dcu.dat and forcevup.dat (NOT confirmed necessary)")
    p_rm.set_defaults(func=cmd_remove_flags)

    p_swap = sub.add_parser("swap-kwi", help="Replace TARGET's content with SOURCE's, keeping TARGET's filename")
    p_swap.add_argument("path")
    p_swap.add_argument("--target", required=True, help="Filename the installer currently selects (lower version)")
    p_swap.add_argument("--source", required=True, help="Filename holding the version you actually want flashed")
    p_swap.add_argument("--backup-dir", help="Where backups go (default: <path>/.patcher-backup)")
    p_swap.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt")
    p_swap.add_argument("--force", action="store_true", help="Overwrite an existing backup for this target")
    p_swap.set_defaults(func=cmd_swap_kwi)

    p_restore = sub.add_parser("restore", help="Restore all files backed up in a backup directory")
    p_restore.add_argument("path")
    p_restore.add_argument("--backup-dir", help="Backup dir to restore from (default: <path>/.patcher-backup)")
    p_restore.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
