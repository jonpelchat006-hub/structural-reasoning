#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive.py — the SPIRAL DRIVE's cold end: storage levels, like the theory's nautilus chambers.

The brain stays the same size because each level holds a more compressed past (the wake law):
  hot    raw npz lives + clips     (full footage — the current chamber)
  warm   .geo loops + panoramas    (compressed identity per life)
  cold   cores + library           (what recurred — the point; never leaves)

This organ moves the HOT layer's already-digested raw files outward when they age past KEEP_DAYS —
to an external drive or network share if one is configured (D:\\planet\\cold_path.txt, one line),
else to D:\\planet\\cold\\ on the same disk. Nothing compressed is ever moved or lost; a moved file
leaves a .moved stub naming its new home. The ocean stays skull-sized; the chambers spiral outward.

Usage:  python archive.py            (the sleep can chain this; safe to run any time)
        python archive.py --dry     (report only)
"""
from __future__ import annotations
import argparse, glob, os, shutil, sys, time

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean"
COLD_CFG = r"D:\planet\cold_path.txt"
DEFAULT_COLD = r"D:\planet\cold"
KEEP_DAYS = 14                     # raw footage younger than this stays in the current chamber
KEEP_MIN = 6                       # always keep at least this many newest raw files per world


def cold_root() -> str:
    try:
        p = open(COLD_CFG, encoding="utf-8").read().strip()
        if p and os.path.isdir(os.path.dirname(p) or p): return p
    except Exception: pass
    return DEFAULT_COLD


def digested(path: str) -> bool:
    """Only raw files whose compressed level already EXISTS may spiral outward."""
    if path.endswith(".npz") and os.sep + "lives" + os.sep in path:
        return os.path.exists(path.replace(".npz", ".geo"))
    if "clip_" in os.path.basename(path):
        return os.path.exists(path.replace(".npz", ".geo"))
    return False


def run(dry: bool = False) -> None:
    cold = cold_root()
    cutoff = time.time() - KEEP_DAYS * 86400
    moved = kept = 0; bytes_moved = 0
    for wdir in sorted(glob.glob(os.path.join(OCEAN, "*"))):
        if not os.path.isdir(wdir): continue
        world = os.path.basename(wdir)
        for sub in ("lives", "clips"):
            files = sorted(glob.glob(os.path.join(wdir, sub, "*.npz")), key=os.path.getmtime)
            old = [f for f in files[:-KEEP_MIN] if os.path.getmtime(f) < cutoff and digested(f)]
            for f in old:
                dst_dir = os.path.join(cold, world, sub)
                if dry:
                    moved += 1; bytes_moved += os.path.getsize(f); continue
                try:
                    os.makedirs(dst_dir, exist_ok=True)
                    dst = os.path.join(dst_dir, os.path.basename(f))
                    shutil.move(f, dst)
                    with open(f + ".moved", "w", encoding="utf-8") as s: s.write(dst)
                    moved += 1; bytes_moved += os.path.getsize(dst)
                except Exception: kept += 1
    print(f"spiral drive: {'would move' if dry else 'moved'} {moved} raw files "
          f"({bytes_moved / 1e6:.0f} MB) outward to {cold}" + (f"; {kept} failed" if kept else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    run(ap.parse_args().dry)
