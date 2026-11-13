#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fuse.py — THE FUSION REACTOR, ported home (Shovelcat-DNA/fusion_reactor.py, Feb 2026):
contained heat turns light rules into heavier elements.

The February reactor's law, kept whole: a candidate enters a CONTAINED space (entry minimum,
capacity, walls that hide the process from outside), HEATS by real activity and COOLS by
neglect, and exits ONLY when the BEC threshold is firmly crossed — Tokamak (slow, steady,
mentor-guided x0.8), NIF (intense burst, multiple validators x2.0), Stellarator (twisted
path, self-sustaining x1.0). What it levels up here is not users but RULES: the abundance
measurement (ARC_ATP §2 follow-up) gave the planet its hydrogen — counter.up at 48.5% — but
no pathway for light species to become heavy ones. This is that pathway.

  COLLISION — two concepts in the same world's core that SHARE AN ATOM are touching; sharing
      is the only place fusion can start (nuclei must contact).
  WARMING (outside the walls) — a touching pair seen again on a later scan warms toward the
      entry minimum (0.3). Transient contact cools back to nothing.
  ADMISSION — costs 1 ATP: containment is paid for with verified past work (the metabolism
      closes: seam-minted energy funds element-building). No ATP -> the pair waits outside.
      Routing keeps the February taxonomy, measured: overlap >= 2 atoms = TOKAMAK (close kin,
      slow and safe); overlap == 1 = STELLARATOR (a bridge between families, twisted path);
      and a pair whose BOTH parents were recovered in a stored teach-back = NIF (two
      validators already reached it — the burst is earned, x2.0).
  HEATING / COOLING — each sleep the pair's BOTH parents still stand in the live core: heat
      (0.1 x reactor multiplier). A parent gone from the core: cool (0.04). Cooled to zero:
      the reactor aborts the pair (logged, never punished).
  THE WALLS — the whole process lives in forge/reactor.json. Nothing is visible to the
      witness, the storyteller, or the ring until the threshold is crossed: failures in the
      reactor are private, exactly as the February design demanded.
  BEC CROSSED (temp >= 1.0) — FUSION: the union of the parents' atoms exits as ONE heavier
      species. It lands where all durable things land: on the RING as a section (kind
      "fusion", golden-angle placement, pointer to world + parents) and in forge/fused.json.
      Parents are never deleted — fusion adds mass; forgetting stays the dark planet's job.
      The same-or-better law holds by construction (the fusion carries every parent atom, so
      anything findable through a parent is findable through it) plus the cap: a fusion
      exceeding MAX_ATOMS atoms is too heavy to bind and is rejected (the iron line — beyond
      it, fusion costs instead of pays; iron_terminus.md's attractor, honored).

Usage:  python fuse.py             (one reactor pass; the sleep chains this after the mint)
        python fuse.py --status
"""
from __future__ import annotations
import argparse, glob, itertools, json, os, sys, time
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
STATE = os.path.join(HERE, "forge", "reactor.json")
FUSED = os.path.join(HERE, "forge", "fused.json")

BEC_THRESHOLD = 1.0
ENTRY_MIN = 0.3                # warming needed before admission (2 sightings + 1)
WARM_STEP = 0.15
HEATING_RATE = 0.1
COOLING_RATE = 0.04
MAX_ATOMS = 5                  # the iron line: heavier than this, fusion stops paying
CAPACITY = 12                  # contained pairs at once, facility-wide
MULT = {"tokamak": 0.8, "nif": 2.0, "stellarator": 1.0}


def _load(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default


def _save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), indent=1)


def _cores() -> Dict[str, List[str]]:
    """world -> current concept keys."""
    out = {}
    for p in glob.glob(os.path.join(OCEAN, "*", "core_*.json")):
        w = os.path.basename(os.path.dirname(p))
        c = _load(p, {})
        ks = list(c.get("concepts", {}).keys())
        if ks: out[w] = sorted(set(out.get(w, []) + ks))
    return out


def _validated_keys() -> set:
    """Concept keys a stored teach-back RECOVERED — two validators already reached them."""
    try:
        from storyteller import score_extraction
    except Exception:
        return set()
    ok = set()
    for p in glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")):
        s = _load(p, {})
        blk = s.get("mika_teach_back") or {}
        ans = blk.get("answer")
        if not ans: continue
        invs = [{"key": i.get("key", i["text"][:30]), "kind": i.get("kind", "concept"),
                 "atoms": i.get("key", "").split("+") if i.get("kind") == "concept" else [],
                 "text": i["text"]} for i in s.get("invariants", [])]
        for pi in score_extraction(ans, invs)["per_invariant"]:
            if pi["recovered"]: ok.add(pi["key"])
    return ok


def _route(a: str, b: str, validated: set) -> str:
    if a in validated and b in validated: return "nif"
    overlap = len(set(a.split("+")) & set(b.split("+")))
    return "tokamak" if overlap >= 2 else "stellarator"


def one_pass() -> Dict:
    st = _load(STATE, {"warming": {}, "reactor": {}, "aborted": 0})
    fused = _load(FUSED, {"species": []})
    cores = _cores()
    validated = _validated_keys()
    already = {f["key"] for f in fused["species"]}
    report = {"warmed": 0, "admitted": 0, "heated": 0, "cooled": 0, "fused": 0, "aborted": 0}

    # 1. collisions outside the walls: touching pairs warm toward the entry minimum
    for w, keys in cores.items():
        for a, b in itertools.combinations(sorted(keys), 2):
            atoms = sorted(set(a.split("+")) | set(b.split("+")))
            if not (set(a.split("+")) & set(b.split("+"))): continue      # no contact, no fusion
            if len(atoms) > MAX_ATOMS: continue                           # beyond the iron line
            key = w + "|" + "+".join(atoms)
            if key in st["reactor"] or key in already: continue
            st["warming"][key] = round(st["warming"].get(key, 0.0) + WARM_STEP, 3)
            report["warmed"] += 1
            # 2. admission: entry minimum reached AND containment paid for
            if st["warming"][key] >= ENTRY_MIN and len(st["reactor"]) < CAPACITY:
                paid = True
                try:
                    import atp
                    paid = atp.spend("fusion-containment", key[:80])
                except Exception: pass
                if paid:
                    st["reactor"][key] = {"world": w, "a": a, "b": b,
                                          "type": _route(a, b, validated),
                                          "temp": st["warming"].pop(key),
                                          "admitted": time.time(), "history": []}
                    report["admitted"] += 1

    # 3. inside the walls: heat while both parents stand, cool when one is gone
    for key, r in list(st["reactor"].items()):
        live = cores.get(r["world"], [])
        if r["a"] in live and r["b"] in live:
            r["temp"] = round(r["temp"] + HEATING_RATE * MULT[r["type"]], 3)
            r["history"].append({"t": time.time(), "temp": r["temp"], "event": "heat"})
            report["heated"] += 1
        else:
            r["temp"] = round(r["temp"] - COOLING_RATE, 3)
            r["history"].append({"t": time.time(), "temp": r["temp"], "event": "cool"})
            report["cooled"] += 1
            if r["temp"] <= 0:
                st["reactor"].pop(key); st["aborted"] += 1; report["aborted"] += 1
                continue
        # 4. BEC crossed: fusion exits the walls
        if r["temp"] >= BEC_THRESHOLD:
            atoms = "+".join(sorted(set(r["a"].split("+")) | set(r["b"].split("+"))))
            sp = {"t": time.time(), "key": atoms, "world": r["world"],
                  "fused_from": [r["a"], r["b"]], "type": r["type"],
                  "weight": len(atoms.split("+")),
                  "passes": len(r["history"]) }
            fused["species"].append(sp)
            st["reactor"].pop(key)
            report["fused"] += 1
            try:                                      # the new element lands on the ring
                import ring as R
                rst = R._load_state()
                R._append([{"t": sp["t"], "kind": "fusion",
                            "label": f"fused element ({sp['type']}): {atoms} in {r['world']} "
                                     f"from {r['a']} + {r['b']}",
                            "pointer": {"world": r["world"], "parents": sp["fused_from"]},
                            "atoms": R._atoms(atoms.replace('+', ' '))}], rst)
            except Exception: pass

    # transient contacts cool back toward nothing
    for key in list(st["warming"]):
        st["warming"][key] = round(st["warming"][key] - 0.05, 3)
        if st["warming"][key] <= 0: st["warming"].pop(key)

    _save(STATE, st); _save(FUSED, fused)
    return report


def status():
    st = _load(STATE, {"warming": {}, "reactor": {}, "aborted": 0})
    fused = _load(FUSED, {"species": []})
    print(f"reactor: {len(st['reactor'])}/{CAPACITY} pairs contained, "
          f"{len(st['warming'])} warming outside, {st.get('aborted', 0)} aborted, "
          f"{len(fused['species'])} elements fused")
    for key, r in sorted(st["reactor"].items(), key=lambda x: -x[1]["temp"])[:8]:
        bar = "#" * int(r["temp"] * 20)
        print(f"  [{r['type']:11s}] {bar:20s} {r['temp']:.2f}  {r['world']}: "
              f"{r['a'][:34]} + {r['b'][:34]}")
    for sp in fused["species"][-5:]:
        print(f"  FUSED ({sp['type']}, weight {sp['weight']}): {sp['key'][:70]} [{sp['world']}]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else:
        r = one_pass()
        print("fusion reactor:", json.dumps(r))
        status()
