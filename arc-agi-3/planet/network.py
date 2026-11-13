#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
network.py — the STITCH: the planet's deposits flow into the shovelcat-network container
(D:\\shovelcat-network — the main-brain/mini-brain ocean built in March, zones L0..L7,
empty until now because there was nothing to pass around). Now there is: the core.

Zone mapping (the container's own purposes, from container.json):
  L7-imagination  incoming unverified          → (left to rain/foreign content; not written here)
  L6-memory       process recordings           → lives as .geo loops:      L6-memory/planet/<world>/
  L5-facts        shovelcat-exclusive data     → cores + stats sessions:   L5-facts/planet/
  L4-spacetime    pattern signatures           → models, panoramas:        L4-spacetime/planet/<world>/
  L2-plane        living work                  → (the running session stays local)
  L1-time         work orders, trust           → work-orders written/claimed here too (mirror of L0)
  L0-origin       main brain index, profiles   → node profile:             L0-origin/profiles/planet-<host>.json
                                                 work orders:              L0-origin/work-orders/

Work orders are the mini brains' food: {"job": digest|train|stats|distill, "root": ..., "status":
"open"|"claimed"|"done", "node": ..., ...}. publish() copies small durable artifacts (never the
big npz frame stores — those are referenced by path); poll() lets any node with the planet code
claim and run a job in its sleep. Everything is append-only and best-effort: a missing network
drive degrades to "not stitched", never to a crash.
"""
from __future__ import annotations
import glob, json, os, shutil, socket, sys, time
from typing import Dict, List, Optional

NETWORK = os.environ.get("SHOVELCAT_NETWORK", r"D:\shovelcat-network")   # a node points this at the share
HOST = socket.gethostname().lower()
NOWIN = 0x08000000 if os.name == "nt" else 0        # CREATE_NO_WINDOW: sleep jobs must not flash consoles


def available(network: str = NETWORK) -> bool:
    return os.path.isdir(os.path.join(network, "L0-origin"))


def _copy(src: str, dst_dir: str) -> Optional[str]:
    try:
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(src))
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src): return None
        shutil.copy2(src, dst); return dst
    except Exception:
        return None


def publish(ocean_root: str, world: Optional[str] = None, network: str = NETWORK) -> Dict:
    """Copy a world's durable sediment into the zones (or every world when world is None)."""
    out = {"copied": 0, "worlds": []}
    if not available(network): return out
    worlds = [world] if world else [os.path.basename(os.path.dirname(p))
                                    for p in glob.glob(os.path.join(ocean_root, "*", "core_*.json"))]
    for w in sorted(set(worlds)):
        wroot = os.path.join(ocean_root, w); n = 0
        for p in glob.glob(os.path.join(wroot, "lives", "*.geo")):
            if _copy(p, os.path.join(network, "L6-memory", "planet", w)): n += 1
        for p in glob.glob(os.path.join(wroot, "core_*.json")) + glob.glob(os.path.join(wroot, "stats", "sessions.json")):
            d = os.path.join(network, "L5-facts", "planet", w) if p.endswith("sessions.json") else os.path.join(network, "L5-facts", "planet")
            if _copy(p, d): n += 1
        for p in glob.glob(os.path.join(wroot, "models", "*.pkl")) + glob.glob(os.path.join(wroot, "panorama_*")):
            if _copy(p, os.path.join(network, "L4-spacetime", "planet", w)): n += 1
        # open ends + stories are imagination sediment — L7 is their natural zone (ARC_OPEN_ENDS §6)
        for p in glob.glob(os.path.join(wroot, "ends", "*.geo")) + \
                 glob.glob(os.path.join(wroot, "stories", "story_*.json")) + \
                 glob.glob(os.path.join(wroot, "stories", "story_*.geo")):
            if _copy(p, os.path.join(network, "L7-imagination", "planet", w)): n += 1
        if n: out["worlds"].append(w); out["copied"] += n
    for p in (os.path.join(ocean_root, "core_library.json"),):
        if os.path.exists(p) and _copy(p, os.path.join(network, "L5-facts", "planet")): out["copied"] += 1
    # node profile in L0 (the main brain's index of who exists and what they hold)
    try:
        prof_dir = os.path.join(network, "L0-origin", "profiles"); os.makedirs(prof_dir, exist_ok=True)
        prof = {"node": f"planet-{HOST}", "kind": "planet-spore", "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "ocean": os.path.abspath(ocean_root),
                "worlds": sorted({os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ocean_root, "*", "core_*.json"))}),
                "jobs": ["digest", "train", "stats", "distill", "story"], "published": out["copied"]}
        with open(os.path.join(prof_dir, f"planet-{HOST}.json"), "w", encoding="utf-8") as f:
            json.dump(prof, f, indent=1)
    except Exception: pass
    return out


# ----------------------------------------------------------------------------- work orders
def order_path(network: str = NETWORK) -> str:
    return os.path.join(network, "L0-origin", "work-orders")


def post(job: str, root: str, note: str = "", network: str = NETWORK) -> Optional[str]:
    """Anyone (Claude, Jonathan, another node) posts work; a sleeping spore picks it up."""
    if not available(network): return None
    d = order_path(network); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"wo_{int(time.time())}_{job}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"job": job, "root": root, "note": note, "status": "open",
                   "postedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "postedBy": HOST}, f, indent=1)
    return p


def poll_and_run(planet_dir: str, network: str = NETWORK, limit: int = 2) -> List[str]:
    """Claim up to `limit` open orders this node can run (its jobs), run them, mark done.
    Claim = rewrite with status claimed+node (last writer wins; jobs are idempotent, so a rare
    double run wastes time, never correctness)."""
    import subprocess
    done = []
    if not available(network): return done
    RUN = {"digest": ["digester.py", "--root"], "train": ["train.py", "--root"],
           "stats": ["stats.py", "--root"], "distill": ["distill.py", "--root"],
           "story": ["storyteller.py", "--root"]}
    EXTRA = {"distill": ["--ask"]}
    for p in sorted(glob.glob(os.path.join(order_path(network), "wo_*.json"))):
        if len(done) >= limit: break
        try:
            with open(p, "r", encoding="utf-8") as f: o = json.load(f)
            if o.get("status") != "open" or o.get("job") not in RUN: continue
            if not os.path.isdir(o.get("root", "")): continue
            o["status"] = "claimed"; o["node"] = HOST; o["claimedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with open(p, "w", encoding="utf-8") as f: json.dump(o, f, indent=1)
            script, flag = RUN[o["job"]][0], RUN[o["job"]][1]
            cmd = [sys.executable, os.path.join(planet_dir, script), flag, o["root"]] + EXTRA.get(o["job"], [])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, creationflags=NOWIN)
            o["status"] = "done" if r.returncode == 0 else "failed"
            o["tail"] = (r.stdout or r.stderr or "")[-400:]
            o["doneAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with open(p, "w", encoding="utf-8") as f: json.dump(o, f, indent=1)
            done.append(f"{o['job']} -> {o['status']}")
        except Exception:
            continue
    return done


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocean", default=r"D:\planet\ocean")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--post", default=None, help="job name to post (digest|train|stats|distill)")
    ap.add_argument("--root", default=None, help="root for the posted job")
    ap.add_argument("--poll", action="store_true")
    a = ap.parse_args()
    if a.publish: print(json.dumps(publish(a.ocean), indent=1))
    if a.post: print(post(a.post, a.root or a.ocean))
    if a.poll: print(poll_and_run(os.path.dirname(os.path.abspath(__file__))))
