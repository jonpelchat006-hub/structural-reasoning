#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo.py — write the planet's memories as .GEO V2 containers (the colony's own format,
D:/shovelcat-colony/app/src/geo/format-v2.ts + serialize-v2.ts), from Python.

The v2 idea, kept exactly: identity belongs to the full CLOSED PATH, not any point;
path SEGMENTS are quaternion deltas (w, x, y, z); BUBBLES are closure/keyframe points
inserted at thresholds; LAYERS project the same object into display / sound / text /
code / storage.

A LIFE is a loop:
  segments  : one per look — delta = (w: time, x: body dx, y: body dy, z: jump impulse)
              in world coordinates (camera compensated), dominantAxis by magnitude
  bubbles   : origin at birth; 'threshold' at real surprises; 'sync' when the map realigns
              or recognises; 'closure' at death (the loop closes — that is its identity)
  tracks    : display  = the atlas (external-ref .npz), text = the narration (inline),
              code = the laws (inline JSON), storage = the core (external-ref), sound =
              the border events (inline)
  closure   : closed=True with the checksum of the segment path

Envelope (serialize-v2.ts): 'GEO\\x02' | version u32 LE=2 | flags u32 LE | ivLen u32 LE=0
| payloadLen u32 LE | JSON payload. Unencrypted; flags = HAS_AI | HAS_COLONY.
"""
from __future__ import annotations
import hashlib, json, math, os, struct, time
from typing import Dict, List, Optional

MAGIC = b"GEO\x02"; VERSION = 2
FLAG_DORMANT, FLAG_HAS_AI, FLAG_HAS_COLONY, FLAG_ENCRYPTED = 1, 2, 4, 8
LAYERS = [  # ±π layer depth: 0 is the display surface; positive = matter (building up)
    {"id": "display", "depth": 0.0, "role": "display", "label": "display", "description": "the atlas — the map on the wall"},
    {"id": "sound", "depth": 0.618, "role": "sound", "label": "sound", "description": "border sounds: what crossed the window"},
    {"id": "text", "depth": 1.0, "role": "text", "label": "text", "description": "grounded narration (atoms only)"},
    {"id": "code", "depth": 1.618, "role": "code", "label": "code", "description": "the laws the species learned"},
    {"id": "storage", "depth": 2.718, "role": "storage", "label": "storage", "description": "the core: what survives death"},
]


def _q(w=0.0, x=0.0, y=0.0, z=0.0) -> Dict[str, float]:
    return {"w": float(w), "x": float(x), "y": float(y), "z": float(z)}


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def life_container(world: str, life_n: int, body_path: List[Dict], events: List[List[str]],
                   narration: str, laws: Dict, atlas_ref: str, core_ref: str, cause: str,
                   stats: Dict, open_end: Optional[Dict] = None) -> Dict:
    """body_path: per look {"t": seconds, "dx":.., "dy":.., "jump": 0/1} in world coords."""
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    loop_id = f"{world}-life-{life_n:03d}"
    segments, bubbles = [], []
    pos = _q(0, 0, 0, 0)
    bubbles.append({"id": "b-origin", "role": "origin", "label": "born", "position": pos, "layerDepth": 0.0,
                    "radius": 1.0, "hWindowIndex": 0})
    last_bubble = "b-origin"
    for i, (step, ev) in enumerate(zip(body_path, events)):
        d = _q(step.get("t", 0.0), step.get("dx", 0.0), step.get("dy", 0.0), step.get("jump", 0.0))
        nxt = _q(pos["w"] + d["w"], pos["x"] + d["x"], pos["y"] + d["y"], pos["z"] + d["z"])
        mags = {"w": abs(d["w"]), "x": abs(d["x"]), "y": abs(d["y"]), "z": abs(d["z"])}
        tot = sum(mags.values()) or 1.0
        dom = max(mags, key=mags.get)
        seg = {"id": f"s{i:05d}", "from": pos, "to": nxt, "delta": d,
               "magnitude": math.sqrt(sum(v * v for v in d.values())), "dominantAxis": dom,
               "axisDominance": mags[dom] / tot, "layerDepth": 0.0, "trackIds": ["t-display"],
               "bubbleStartId": last_bubble}
        role = None
        if "surprise.big" in ev: role, label = "threshold", "surprise"
        elif "wall.realigned" in ev or "wall.recognised" in ev: role, label = "sync", "map aligned"
        elif "body.confirmed" in ev: role, label = "projection", "body confirmed"
        if role:
            bid = f"b{i:05d}"
            bubbles.append({"id": bid, "role": role, "label": label, "position": nxt, "layerDepth": 0.0,
                            "radius": 1.0, "hWindowIndex": len(bubbles), "notes": "|".join(sorted(ev))[:200]})
            seg["bubbleEndId"] = bid; last_bubble = bid
        segments.append(seg); pos = nxt
    if open_end is None:
        bubbles.append({"id": "b-closure", "role": "closure", "label": f"died: {cause}", "position": pos,
                        "layerDepth": 0.0, "radius": 1.0, "hWindowIndex": len(bubbles)})
        if segments: segments[-1]["bubbleEndId"] = "b-closure"
    else:
        # an OPEN loop: the end sticks out — a dangling bond. The tip is INVERTED (the far end
        # presents its small seed), it attracts what would close it, and it is imagination until played.
        bubbles.append({"id": "b-tip", "role": "seed", "label": f"open: {open_end.get('seed', '?')}",
                        "position": pos, "layerDepth": 0.0, "radius": 0.5, "hWindowIndex": len(bubbles),
                        "notes": "inverted tip — attracts: " + ",".join(open_end.get("wants", [])[:8])})
        if segments: segments[-1]["bubbleEndId"] = "b-tip"
    path_hash = _hash(json.dumps([s["delta"] for s in segments]))
    laws_json = json.dumps(laws, sort_keys=True)
    sound = [e for ev in events for e in ev if e.startswith("window.")]
    tracks = [
        {"id": "t-display", "kind": "image", "label": "atlas", "mimeType": "application/x-npz", "encoding": "external-ref",
         "layerDepth": 0.0, "byteLength": _size(atlas_ref), "axisWeights": _q(0, 1, 1, 0), "contentRef": atlas_ref},
        {"id": "t-sound", "kind": "metadata", "label": "border sounds", "mimeType": "application/json", "encoding": "inline-text",
         "layerDepth": 0.618, "byteLength": len(json.dumps(sound)), "axisWeights": _q(1, 0, 0, 0), "inlineText": json.dumps(sound)},
        {"id": "t-text", "kind": "metadata", "label": "narration", "mimeType": "text/plain", "encoding": "inline-text",
         "layerDepth": 1.0, "byteLength": len(narration.encode("utf-8")), "axisWeights": _q(1, 0, 0, 0), "inlineText": narration},
        {"id": "t-code", "kind": "code", "label": "laws", "mimeType": "application/json", "encoding": "inline-text",
         "layerDepth": 1.618, "byteLength": len(laws_json), "axisWeights": _q(0, 1, 1, 1), "inlineText": laws_json,
         "contentHash": _hash(laws_json)},
        {"id": "t-storage", "kind": "metadata", "label": "core", "mimeType": "application/json", "encoding": "external-ref",
         "layerDepth": 2.718, "byteLength": _size(core_ref), "axisWeights": _q(1, 1, 1, 1), "contentRef": core_ref},
    ]
    manifest = {"id": _hash(loop_id + created)[:32], "name": loop_id, "createdAt": created, "schemaVersion": "2.0.0",
                "loopIdentity": path_hash, "primaryProjection": "image", "hWindow": 8,
                "thresholds": {"minBubbleSpacing": 1.0, "bubbleDistance": 8.0, "phaseThreshold": 0.5,
                               "curvatureThreshold": 1.2, "axisLockThreshold": 0.8},
                "layers": LAYERS, "tags": ["planet", world, "life", cause],
                "extensions": {"planet": {"world": world, "life": life_n, "stats": stats}}}
    now = created
    return {"manifest": manifest, "bubbles": bubbles, "segments": segments, "tracks": tracks,
            "ledger": {"earnedCredits": float(stats.get("drive", 0.0)), "lockedCredits": 0.0, "spentCredits": 0.0,
                       "availableCredits": float(stats.get("drive", 0.0)), "entries": []},
            "batteries": [],
            "timeline": {"id": f"tl-{loop_id}", "label": "life", "mode": "adaptive-pingpong", "createdAt": now,
                         "thresholds": {}, "memories": [], "stats": {}},
            "recognition": {"id": f"rf-{loop_id}", "label": "surface", "width": int(stats.get("W", 0)),
                            "height": int(stats.get("H", 0)), "hWindow": 8, "thresholds": {}, "cells": [], "probes": [],
                            "bundles": [], "stats": {}},
            "interfaceState": {"id": f"if-{loop_id}", "label": "player", "shellDepth": 1},
            "desktopState": {"id": f"dt-{loop_id}", "label": "game window", "hostPlatform": "windows"},
            "closure": ({"closed": True, "checksum": path_hash, "loopLength": len(segments), "reason": cause}
                        if open_end is None else
                        {"closed": False, "checksum": path_hash, "loopLength": len(segments), "reason": cause,
                         "openEnd": open_end})}


def _size(path: str) -> int:
    try: return os.path.getsize(path)
    except Exception: return 0


def write_geo(path: str, container: Dict, dormant: bool = False) -> str:
    payload = json.dumps(container, indent=2).encode("utf-8")
    flags = FLAG_HAS_AI | FLAG_HAS_COLONY | (FLAG_DORMANT if dormant else 0)
    header = MAGIC + struct.pack("<III", VERSION, flags, 0)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + struct.pack("<I", len(payload)) + payload)
    return path


def read_geo(path: str) -> Dict:
    with open(path, "rb") as f: buf = f.read()
    if buf[:4] != MAGIC: raise ValueError("bad magic")
    version, flags, ivlen = struct.unpack("<III", buf[4:16])
    if flags & FLAG_ENCRYPTED: raise ValueError("encrypted .geo — needs the colony key")
    n = struct.unpack("<I", buf[16 + ivlen:20 + ivlen])[0]
    return json.loads(buf[20 + ivlen:20 + ivlen + n].decode("utf-8"))


if __name__ == "__main__":
    c = life_container("dry", 1, [{"t": 0.16, "dx": 3, "dy": 0, "jump": 0}, {"t": 0.16, "dx": 3, "dy": -3, "jump": 1}],
                       [set(), {"surprise.big"}], "walked, jumped", {"mover": {"right": [0, 3]}}, "atlas.npz", "core.json",
                       "test", {"drive": 1.5, "W": 160, "H": 96})
    p = write_geo("/tmp/test_life.geo", c); back = read_geo(p)
    print(p, os.path.getsize(p), "bytes; segments", len(back["segments"]), "bubbles", [b["role"] for b in back["bubbles"]],
          "closed", back["closure"]["closed"])
