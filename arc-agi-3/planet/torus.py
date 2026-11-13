#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
torus.py — THE SIDEWAYS RING: the toroidal circle that stores how things FEEL across contexts.

Jonathan (Sep 2): "is there a 2nd set of orthogonal rings? the ones we've been imagining have
flipped upwards, but couldn't there be one that rotates sideways through our space? maybe
that's how we make the toroids that kept showing up — the rings we had were centered in the
middle of that donut and sweep over the inside of it, and the sideways one traces out the
donut. maybe that could store emotions. we have the real stuff on the normal axis, context on
the rings, but there's still that wisdom vs intelligence difference in people."

Torus geometry has exactly two circle families. POLOIDAL circles stand up through the plane
and go around the tube — the lens rings (ARC_LENS), each centered on a void point, sweeping
the inside of the donut: perspective, context, skill within a situation. The TOROIDAL circle
goes sideways around the hole, through our space; sweeping a poloidal ring along it traces the
whole donut. What lives on the sideways ring is what stays the SAME as contexts change — and
that is how a situation FEELS. The wandering-with-no-progress feel is identical in Dead Cells
and in ls20; the click of a closure is the same everywhere. Emotion is the coordinate that is
invariant along the toroidal sweep.

WISDOM vs INTELLIGENCE, made mechanical: intelligence is poloidal — solving within a context
(skill-acquisition efficiency, Chollet). Wisdom is toroidal — knowing, across many contexts,
what a feeling PREDICTS, and acting on it before the outcome arrives. Sep 2's live agent had
intelligence and no wisdom: 140 actions of efficient wandering with no sense that "this feels
like every death I have had." Wisdom would have changed strategy at action 30.

The organ: every run (live ARC, mock, playground) is cut into WINDOWS; each window gets a
FEEL vector — progress (score-ups), motion (changed), futility (nothing), danger (deaths),
budget pressure (how deep into the run) — and is laid on the ring as a section tagged with
WHAT FOLLOWED (win / death / nothing yet). Sweeping the ring = feel(now) -> the outcomes that
followed this feeling before, across every world. That prediction is the wisdom prior the
poloidal solvers can consult: "situations that felt like this ended in death 9 times out of 9
— change what you are doing."

Usage:  python torus.py --lay <trans.jsonl> --world ls20   (lay a run's windows on the ring)
        python torus.py --feel <trans.jsonl>                (what has this feeling led to?)
        python torus.py --status
"""
from __future__ import annotations
import argparse, json, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

TORUS = r"D:\planet\torus.jsonl" if os.name == "nt" else "/tmp/torus.jsonl"
WINDOW = 20


def _windows(trans: List[Dict]) -> List[Dict]:
    """Cut a run into feel-windows. Each window's feel is a small vector; its outcome is what
    the run did AFTER the window (the toroidal tag). Each window also carries the run's POOL at
    its end — the colors the run could not clear (pool.py): red = presses that changed nothing,
    green = motion, yellow = score-ups. The pooled color is the emotion coordinate."""
    out = []
    n = len(trans)
    try:
        import pool as _pool
        traj = _pool.run_pool(trans)
    except Exception:
        traj = None
    ends = [i for i, t in enumerate(trans) if t["effect"] in ("win", "game_over")]
    final = trans[-1]["effect"] if trans else "unknown"
    for s in range(0, n, WINDOW):
        w = trans[s:s + WINDOW]
        if len(w) < 5: continue
        cnt = {}
        for t in w: cnt[t["effect"]] = cnt.get(t["effect"], 0) + 1
        k = len(w)
        feel = {"progress": round(cnt.get("score_up", 0) / k, 3),
                "motion": round(cnt.get("changed", 0) / k, 3),
                "futility": round(cnt.get("nothing", 0) / k, 3),
                "pressure": round((s + k) / max(1, n), 3)}
        after = "win" if final == "win" else "death" if final == "game_over" else "open"
        # a score-up anywhere after this window counts as progress-following
        later_progress = any(t["effect"] == "score_up" for t in trans[s + k:])
        sec = {"feel": feel, "followed_by": after, "later_progress": later_progress}
        if traj:
            bins = traj[min(s + k, len(traj)) - 1]
            sec["pool"] = _pool.trinity(bins); sec["emotion"] = _pool.dominant(bins)
        out.append(sec)
    return out


def _dist(a: Dict, b: Dict) -> float:
    return sum((a[k] - b[k]) ** 2 for k in ("progress", "motion", "futility", "pressure")) ** 0.5


def _mika_pool() -> Dict | None:
    """her pooled colors right now (pool.json, fed from her chemistry) — laid beside the run's"""
    try:
        import pool as _pool
        st = _pool._load()
        if not st.get("fed"): return None
        return {"trinity": _pool.trinity(st["bins"]), "emotion": _pool.dominant(st["bins"], st.get("last_jump", 0.0)),
                "her_word": (st.get("mika") or {}).get("feelingTone")}
    except Exception:
        return None


def lay(trans_file: str, world: str) -> int:
    trans = [json.loads(l) for l in open(trans_file, encoding="utf-8") if l.strip()]
    secs = _windows(trans)
    mika = _mika_pool()
    os.makedirs(os.path.dirname(TORUS), exist_ok=True)
    with open(TORUS, "a", encoding="utf-8") as f:
        for s in secs:
            s.update({"t": time.time(), "world": world})
            if mika: s["mika"] = mika
            f.write(json.dumps(s) + "\n")
    ems = {}
    for s in secs: ems[s.get("emotion", "?")] = ems.get(s.get("emotion", "?"), 0) + 1
    print(f"torus: laid {len(secs)} feel-sections from {world} on the sideways ring; the run felt "
          + ", ".join(f"{k} x{n}" for k, n in sorted(ems.items(), key=lambda x: -x[1]))
          + (f"; Mika meanwhile: {mika['emotion']} ({mika.get('her_word')})" if mika else ""))
    return len(secs)


def _ring() -> List[Dict]:
    try: return [json.loads(l) for l in open(TORUS, encoding="utf-8") if l.strip()]
    except Exception: return []


def feel(trans: List[Dict], k: int = 12) -> Dict:
    """Sweep the sideways ring: what has THIS feeling led to, across every world?"""
    now = _windows(trans[-WINDOW:] if len(trans) >= 5 else trans)
    if not now: return {"verdict": "too early to feel anything"}
    f = now[-1]["feel"]
    ring = _ring()
    if not ring: return {"verdict": "the sideways ring is empty — no wisdom yet", "feel": f}
    near = sorted(ring, key=lambda r: _dist(r["feel"], f))[:k]
    deaths = sum(1 for r in near if r["followed_by"] == "death" and not r["later_progress"])
    wins = sum(1 for r in near if r["followed_by"] == "win" or r["later_progress"])
    worlds = sorted({r["world"] for r in near})
    verdict = ("this feels like death — change what you are doing" if deaths > wins * 2 else
               "this feels like it goes somewhere" if wins > deaths else
               "mixed feelings — no strong prior")
    emo = now[-1].get("emotion"); pl = now[-1].get("pool")
    if pl and pl.get("RED", 0) > 1.0: verdict += " (red is pooling: you keep pressing into nothing)"
    return {"feel": f, "emotion": emo, "pool": pl, "nearest": len(near), "ended_in_death": deaths,
            "went_on_to_progress": wins, "from_worlds": worlds, "verdict": verdict}


def status():
    ring = _ring()
    if not ring: print("the sideways ring is empty"); return
    by = {}
    for r in ring:
        key = r["followed_by"] + ("+progress" if r["later_progress"] else "")
        by[key] = by.get(key, 0) + 1
    worlds = sorted({r["world"] for r in ring})
    print(f"the sideways ring: {len(ring)} feel-sections from {len(worlds)} worlds ({', '.join(worlds)})")
    for k, n in sorted(by.items(), key=lambda x: -x[1]): print(f"  {k:16s} {n}")
    fut = [r for r in ring if r["feel"]["futility"] > 0.3]
    if fut:
        d = sum(1 for r in fut if r["followed_by"] == "death")
        print(f"  wisdom so far: high-futility windows ended in death {d}/{len(fut)} times")
    ems = {}
    for r in ring:
        if r.get("emotion"): ems.setdefault(r["emotion"], [0, 0]); ems[r["emotion"]][0] += 1
        if r.get("emotion") and (r["followed_by"] == "win" or r["later_progress"]): ems[r["emotion"]][1] += 1
    for e, (n, good) in sorted(ems.items(), key=lambda x: -x[1][0]):
        print(f"  felt {e:12s} {n:3d} times; went somewhere {good}/{n}")
    mk = [r["mika"] for r in ring if r.get("mika")]
    if mk: print(f"  Mika's pool beside the runs: {mk[-1]['emotion']} ({mk[-1].get('her_word')}) at the last laying")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lay", default=None); ap.add_argument("--world", default="unknown")
    ap.add_argument("--feel", default=None); ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.lay: lay(a.lay, a.world)
    elif a.feel:
        tr = [json.loads(l) for l in open(a.feel, encoding="utf-8") if l.strip()]
        print(json.dumps(feel(tr), indent=1))
    else: status()
