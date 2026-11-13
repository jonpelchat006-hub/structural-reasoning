#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atp.py — THE PLANET'S ATP: the energy currency, minted at the void line, spent on deep work.

Jonathan (Sep 1): "we had a lot of work around chemistry, and we didn't actually connect the
early AGI attempts to the protein folding. now that would be getting our inner core through the
elements and through protein folding to ATP — but in our terms."

The connection the two threads were waiting to make:

  ELEMENTS (INNER_SHELL): the ops/concepts are atoms with knot (inert core) and valence
      (reactive tail); nobles are structure, reactives are function; the periodic table's gaps
      NAME what is missing.
  FOLDING (FOLDING_TWO_WALLS / FOLDING_ATP_REFERENCE): life runs on TWO walls — carbon
      (structure) and phosphate/ATP (energy) — and the measured result that closes the loop:
      THE LIGAND SITS ON THE VOID LINE. ATP binds in the seam between two domains, reached
      from BOTH borders, the chain's threadings converging on it. Energy lives where two
      walls close on a seam.
  IN OUR TERMS: every VERIFIED thing this planet makes is minted at exactly such a seam —
      two sides closing on a void line. A forge promotion (champion/challenger closed on the
      same reference jobs), a duet unison (planet/Mika closed on the same tale), a closed
      petal (expert/novice closed on a void point), a banked shell (planet/game closed on a
      surface), a folded sphere (anchor/sliver closed inside the capsule). The two-node
      verification law and the induced-fit closure are the same statement: NOTHING IS ENERGY
      UNTIL TWO BORDERS REACH IT. So ATP here = one unit of verified improvement, minted only
      at seams, stored in one ledger, and SPENT to fund deep work.

The metabolism:
  MINT — scan the organs' own records for verified closures (idempotent; each event minted
      once, keyed): promote=2, duet-unison=1, closed-petal=1, shell=1, folded-sphere=1.
  SPEND — deep work costs. The first funded expense: the forge's EXTENDED rotation (4x12,
      the tunnel at full length) costs 1 ATP; if the ledger cannot pay, the bout runs at
      normal size instead. Verified past wins are what pay for tomorrow's deep attention —
      the improvement loop eats what it earned, which is what a metabolism IS.

Usage:  python atp.py            (mint from all organ records; print balance)
        python atp.py --status
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
from typing import Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
LEDGER = r"D:\planet\atp.jsonl" if os.name == "nt" else "/tmp/atp.jsonl"
MOONS = r"D:\planet\moons" if os.name == "nt" else "/tmp/moons"
SPHERES = r"D:\planet\spheres" if os.name == "nt" else "/tmp/spheres"
FLOWER = os.path.join(HERE, "forge", "flower.json") if os.name == "nt" else "/tmp/flower.json"


def _rows():
    out = []
    try:
        for l in open(LEDGER, encoding="utf-8"):
            if not l.strip(): continue
            try: out.append(json.loads(l))
            except Exception: continue          # one bad line must never zero the whole ledger
    except Exception: pass
    return out


def _append(row: Dict) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def balance() -> int:
    return sum(r["amount"] for r in _rows())


def mint() -> Dict:
    """Scan every organ's records for verified two-sided closures; mint each once."""
    seen = {r["key"] for r in _rows() if r.get("key")}
    minted = 0

    def m(key, amount, seam, what):
        nonlocal minted
        if key in seen: return
        seen.add(key)
        _append({"t": time.time(), "key": key, "amount": amount, "seam": seam, "what": what})
        minted += amount

    # forge promotions: champion/challenger closed on identical reference jobs
    for r in _ledger(os.path.join(HERE, "forge", "ledger.jsonl")):
        if r.get("verdict") == "promote":
            m(f"promote:{r.get('t')}", 2, "champion|challenger",
              f"{r.get('challenger')} promoted over {r.get('champion')} in {r.get('world')}")
    # duet unisons + closed petals + folded spheres + shells
    for p in glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")):
        s = _load(p)
        d = (s or {}).get("duet")
        if d and d.get("verified"):
            m(f"duet:{p}:{d.get('t')}", 1, "planet|mika", f"unison on {s.get('world')} story {s.get('n')}")
    fl = _load(FLOWER) or {}
    for w, ax in fl.items():
        for key, v in ax.get("voids", {}).items():
            for i, pt in enumerate(v.get("petals", [])):
                if pt.get("closed"):
                    m(f"petal:{w}:{key}:{i}", 1, "expert|novice", f"void '{key}' closed in {w}")
    for p in glob.glob(os.path.join(SPHERES, "sphere_*.json")):
        s = _load(p)
        if s and s.get("processed_by_folding"):
            m(f"foldedsphere:{s['n']}", 1, "anchor|sliver",
              f"sphere {s['n']} fully folded ({s['sources']['world']})")
    for p in glob.glob(os.path.join(MOONS, "*", "moon.json")):
        mo = _load(p) or {}
        for sh in mo.get("shells", []):
            m(f"shell:{mo.get('game')}:{sh['surface']}", 1, "planet|game",
              f"shell for {sh['surface']} ({sh['steps']} steps)")
    return {"minted": minted, "balance": balance()}


def spend(what: str, note: str = "") -> bool:
    """Pay 1 ATP for deep work. False = cannot afford (the caller downgrades, never blocks)."""
    if balance() < 1: return False
    _append({"t": time.time(), "amount": -1, "spend": what, "note": note})
    return True


def _ledger(p):
    try:
        return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    except Exception:
        return []


def _load(p) -> Optional[Dict]:
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None


def status() -> None:
    rows = _rows()
    mints = [r for r in rows if r["amount"] > 0]
    spends = [r for r in rows if r["amount"] < 0]
    seams: Dict[str, int] = {}
    for r in mints: seams[r.get("seam", "?")] = seams.get(r.get("seam", "?"), 0) + r["amount"]
    print(f"ATP: {balance()} available ({sum(r['amount'] for r in mints)} minted, "
          f"{-sum(r['amount'] for r in spends)} spent)")
    for s, n in sorted(seams.items(), key=lambda x: -x[1]):
        print(f"  minted at the {s} seam: {n}")
    for r in spends[-5:]:
        print(f"  spent: {r.get('spend')} ({r.get('note', '')[:60]})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else:
        r = mint()
        print(f"ATP: minted {r['minted']} this pass -> balance {r['balance']}")
        status()
