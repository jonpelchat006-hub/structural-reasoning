#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
darkplanet.py — the DARK PLANET: where fallen ring sections go to be compacted for another round.

Jonathan (Aug 31): "new pieces come out and make their way around the ring leaving sediment —
which causes older pieces to fall off. They go back to the dark planet where they get compacted
down further, which makes them easier to pass on another round. And that compaction provides the
same or better accuracy than the last form it was in."

The cycle (grounded in the dark-matter channeling work — SPARSE_VESICA_EXPANSION §27: dark matter
is the hidden bulk, dark channels move displaced products, the memory layer routes):

  1. The ring stays a bounded LIVE window (RING_CAP sections in circulation). New deposits push
     the oldest live sections off the edge — falling off is displacement, never deletion.
  2. Fallen sections travel the dark channel to this compactor, which works in the dark (the
     sleep): sections of the same kind and world are merged into ONE compact section — a denser
     piece carrying the union of what mattered, pointing to every member it holds.
  3. THE LAW: a compaction is accepted only if EVERY member remains findable through its compact
     (same retrieval rule the ring uses). Fails -> the group is split and retried; a member that
     cannot compact without loss simply stays live. Same-or-better accuracy, enforced, not hoped.
  4. Compacts are appended to the ring as new sections (generation+1) and circulate again —
     lighter for the next round. Compacts of compacts keep compounding; the full history stays
     in ring.jsonl forever (--deep searches it), and every artifact stays in the core/git.

Usage:  python darkplanet.py            (one compaction pass; the sleep chains this after ring --scan)
        python darkplanet.py --status
"""
from __future__ import annotations
import argparse, json, os, sys, time
from collections import Counter
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import ring as R

RING_CAP = 96                  # sections in live circulation
DP_STATE = R.RING.replace("ring.jsonl", "darkplanet.json")
MAX_ATOMS = 24                 # a compact section's atom budget (same as any section)


BURN_AFTER = 3                 # rounds a fallen section may refuse compaction before the heat ring takes it


def _state() -> Dict:
    st = {"compacted": [], "rounds": 0, "kept_live": [], "stuck": {}, "burned": 0}
    try: st.update(json.load(open(DP_STATE, encoding="utf-8")))
    except Exception: pass
    return st


def _findable(member: Dict, compact: Dict) -> bool:
    """The ring's own retrieval rule: would a query made of this member's atoms surface the compact?"""
    ma = set(member.get("atoms", []))
    need = min(2, max(1, len(ma)))
    return len(ma & set(compact.get("atoms", []))) >= need


def _make_compact(members: List[Dict]) -> Dict:
    cnt = Counter(a for m in members for a in m.get("atoms", []))
    atoms = [a for a, _ in cnt.most_common(MAX_ATOMS)]
    gen = max(m.get("gen", 0) for m in members) + 1
    kinds = Counter(m["kind"] for m in members)
    t0, t1 = min(m.get("t", 0) for m in members), max(m.get("t", 0) for m in members)
    label = (f"compact g{gen}: {sum(kinds.values())} pieces ({', '.join(f'{v} {k}' for k, v in kinds.most_common(3))}) "
             f"{time.strftime('%b %d', time.localtime(t0))}-{time.strftime('%b %d', time.localtime(t1))}"
             f" — {members[0]['label'][:60]}")
    return {"t": time.time(), "kind": "compact", "gen": gen, "label": label[:180],
            "pointer": {"members": [m["n"] for m in members],
                        "sample": [m.get("pointer", {}) for m in members[:3]]},
            "atoms": atoms}


def _compact_group(members: List[Dict]) -> List[Dict]:
    """Compact a group under the law: every member must stay findable, else split and retry."""
    if len(members) == 1:
        return []                          # a singleton gains nothing; it stays live
    c = _make_compact(members)
    if all(_findable(m, c) for m in members):
        return [c]
    if len(members) == 2:
        return []                          # cannot compact without loss — they stay live
    mid = len(members) // 2
    return _compact_group(members[:mid]) + _compact_group(members[mid:])


def _make_roof(members: List[Dict]) -> Dict:
    """The HEAT RING (Erdős work): what circulates too long refusing to compact is USELESS heat —
    it gets burned into a new ROOF that curls back in. Burning is honestly lossy: the roof keeps
    only the strongest shared atoms and says how many pieces went into the fire. --deep still
    reads every burned piece forever; the ring never deletes."""
    cnt = Counter(a for m in members for a in m.get("atoms", []))
    atoms = [a for a, _ in cnt.most_common(MAX_ATOMS)]
    kinds = Counter(m["kind"] for m in members)
    return {"t": time.time(), "kind": "roof", "gen": max(m.get("gen", 0) for m in members) + 1,
            "label": f"roof: {len(members)} pieces burned by the heat ring "
                     f"({', '.join(f'{v} {k}' for k, v in kinds.most_common(3))}) — curled back in",
            "pointer": {"members": [m["n"] for m in members]},
            "atoms": atoms}


def one_pass() -> Dict:
    rows = R._tail_jsonl(R.RING, 200000)
    st = _state()
    gone = set(st["compacted"])
    live = [r for r in rows if r["n"] not in gone]
    if len(live) <= RING_CAP:
        return {"live": len(live), "fell": 0, "compacts": 0, "note": "ring under capacity — nothing falls"}
    over = len(live) - RING_CAP
    falling = sorted(live, key=lambda r: r["n"])[:over]      # the oldest circulate off the edge
    # group by kind (and world where present) — like compacts with like
    groups: Dict[str, List[Dict]] = {}
    for m in falling:
        key = m["kind"] + ":" + str(m.get("pointer", {}).get("world", ""))
        groups.setdefault(key, []).append(m)
    compacts, absorbed = [], []
    for g in groups.values():
        cs = _compact_group(g)
        compacts += cs
        for c in cs:
            absorbed += c["pointer"]["members"]
    # the heat ring: fallen pieces that refused compaction again heat up; at BURN_AFTER they burn
    stuck = {int(k): v for k, v in st.get("stuck", {}).items()}
    kept_members = [m for m in falling if m["n"] not in set(absorbed)]
    burned_rows = []
    for m in kept_members:
        stuck[m["n"]] = stuck.get(m["n"], 0) + 1
    hot = [m for m in kept_members if stuck.get(m["n"], 0) >= BURN_AFTER]
    roofs = []
    if len(hot) >= 2:
        roof = _make_roof(hot)
        roofs.append(roof)
        burned_rows = hot
        absorbed += roof["pointer"]["members"]
        for m in hot: stuck.pop(m["n"], None)
    if compacts or roofs:
        rst = R._load_state()
        R._append(compacts + roofs, rst)                      # compacts and the roof rejoin the ring
    st["compacted"] = sorted(set(st["compacted"]) | set(absorbed))
    gone_now = set(st["compacted"])
    st["stuck"] = {str(k): v for k, v in stuck.items() if v > 0 and k not in gone_now}
    st["burned"] = st.get("burned", 0) + len(burned_rows)
    st["rounds"] += 1
    json.dump(st, open(DP_STATE, "w", encoding="utf-8"), indent=1)
    kept = over - len(absorbed)
    return {"live": len(live) - len(absorbed) + len(compacts) + len(roofs), "fell": over,
            "compacts": len(compacts), "absorbed": len(absorbed), "burned": len(burned_rows),
            "stayed_live_uncompactable": kept, "rounds": st["rounds"]}


def status() -> None:
    rows = R._tail_jsonl(R.RING, 200000)
    st = _state()
    gone = set(st["compacted"])
    live = [r for r in rows if r["n"] not in gone]
    gens = Counter(r.get("gen", 0) for r in live if r["kind"] == "compact")
    roofs = sum(1 for r in live if r["kind"] == "roof")
    print(f"ring: {len(rows)} total sections, {len(live)} live (cap {RING_CAP}), "
          f"{len(gone)} absorbed into compacts, {st['rounds']} dark-planet rounds, "
          f"{st.get('burned', 0)} pieces burned into {roofs} live roofs "
          f"({len(st.get('stuck', {}))} heating up)")
    if gens: print(f"compact generations in circulation: {dict(gens)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else:
        r = one_pass()
        print("dark planet:", json.dumps(r, ensure_ascii=False))
