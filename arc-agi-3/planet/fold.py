#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fold.py — the DRIFT AND FOLD: a pinched sphere floats inside the domain, fills in from another
side, and the novice ring expands until the void point is reachable.

Jonathan (Aug 31): "if that mass is made from being pushed in I don't think it would go right
back in — it would float to somewhere else inside that domain and have to connect to somewhere
else to fill it in. We would have the void point the novice is trying to reach, the area in the
expert, where the tunnel touches the ring and the midpoint — so there could be a missing piece
between the tunnel end and the novice point. When it breaks off and closes there would be
SLIVERS OF NOTHING in that circle. So the novice would have to go to another side and do its
self-improvement loop somewhere else. And that would be like folding it into other things to
get it into a form we can process — which could expand the novice ring until it can reach that
void point."

Every phrase, made mechanical:

  SLIVERS OF NOTHING — computable, not poetic. The capsule carries every failed attempt, so
      the slivers are exactly the PIECES OF THE RULE THE NOVICE NEVER ONCE MATCHED (per-atom
      for concept rules, per-token for laws, using the storyteller's own matchers). The sealed
      circle contains the void point, the tunnel walls, and these gaps — the missing piece
      between the tunnel end and the novice point, named.
  FLOATS SOMEWHERE ELSE INSIDE THE DOMAIN — the sphere does not go back down the tunnel that
      made it. It drifts to wherever the novice is already STRONG: rules she has measurably
      recovered (re-scored from stored answers, any story, any world — the whole domain is
      open to the drift).
  ANOTHER SIDE / FOLDING INTO OTHER THINGS — one sliver at a time is FOLDED onto an anchor the
      novice already holds: "you know THIS well; here is one new piece that belongs beside
      it." The unteachable whole was indigestible; the sliver folded into known material is a
      form she can process.
  THE RING EXPANDS — each folded sliver she can now say back is recorded in the capsule. When
      every sliver is filled, her ring has grown to where the void point sits: the flower's
      ejection is lifted and the bell may ring there again — the retry that tests whether the
      expanded ring truly reaches.

Usage:  python fold.py             (drift every unanswered sphere; fold up to 3 slivers each)
        python fold.py --status
        python fold.py --demo     (whole cycle against a stub novice)
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
FLOWER = os.path.join(HERE, "forge", "flower.json") if os.name == "nt" else "/tmp/flower.json"
SPHERES = r"D:\planet\spheres" if os.name == "nt" else "/tmp/spheres"
BRIDGE = "http://localhost:41737"
FOLDS_PER_RUN = 3


def _load(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default


def slivers_of(rule: Dict, attempts: List[Dict]) -> List[str]:
    """The pieces of the rule never once matched across every failed attempt."""
    from storyteller import _tokens, _match_atom
    lines = [_tokens(l) for a in attempts for l in (a.get("answer") or "").splitlines() if l.strip()]
    if rule.get("kind") == "concept" and rule.get("key"):
        return [a for a in rule["key"].split("+") if not _match_atom(a, lines)]
    have = set().union(*lines) if lines else set()
    return sorted(_tokens(rule.get("text", "")) - have)


def anchors_of(exclude_key: str) -> List[Dict]:
    """Where the novice is STRONG: rules she measurably recovered, anywhere in the domain."""
    from storyteller import score_extraction
    out = []
    for p in sorted(glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")),
                    key=os.path.getmtime)[::-1][:20]:
        s = _load(p, None)
        if not s: continue
        invs = [{"key": i.get("key", i["text"][:30]), "kind": i.get("kind", "concept"),
                 "atoms": i.get("key", "").split("+") if i.get("kind") == "concept" else [],
                 "text": i["text"]} for i in s.get("invariants", [])]
        for side in ("mika_teach_back", "duet"):
            blk = s.get(side) or {}
            ans = blk.get("answer") or (blk.get("answers", {}) or {}).get("mika")
            if not ans: continue
            for pi in score_extraction(ans, invs)["per_invariant"]:
                if pi["recovered"] and pi["key"] != exclude_key:
                    txt = next((v["text"] for v in invs if v["key"] == pi["key"]), "")
                    out.append({"key": pi["key"], "text": txt, "world": s.get("world")})
            break
    return out


def fold_lesson(anchor: Dict, sliver: str, rule: Dict, world: str) -> str:
    from storyteller import _phrase
    piece = _phrase(sliver) if "." in sliver or ":" in sliver else sliver
    return (f"You already know this rule well: \"{anchor['text']}\".\n"
            f"Here is ONE new piece from the world '{world}' that belongs beside it: "
            f"in the rule \"{rule.get('text', '')}\", the part that matters now is \"{piece}\".\n"
            f"Say one line of your own that uses \"{piece}\" correctly in that world.")


def drift(sphere_path: str, ask=None) -> Optional[Dict]:
    """One sphere floats: fold up to FOLDS_PER_RUN slivers onto anchors; lift ejection when full."""
    from storyteller import _tokens, _match_atom
    sp = _load(sphere_path, None)
    if not sp or sp.get("answer") or sp.get("processed_by_folding"): return None
    rule = sp["contents"]["rule"]
    world = sp["sources"]["world"]
    folds = sp.setdefault("folds", [])
    filled = {f["sliver"] for f in folds if f["filled"]}
    todo = [s for s in slivers_of(rule, sp["contents"].get("attempts", [])) if s not in filled]
    if not todo:
        return _ring_expanded(sp, sphere_path)
    anchors = anchors_of(rule.get("key", ""))
    if not anchors:
        print(f"sphere {sp['n']}: nowhere to drift — the novice holds no recovered rules yet")
        return None
    if ask is None:
        def ask(t):
            import requests
            r = requests.post(BRIDGE + "/chat", json={"text": t}, timeout=300).json()
            if isinstance(r, dict) and r.get("ok") is False: return None
            return r.get("reply") or r.get("response") or r.get("text")
    done = 0
    for i, sliver in enumerate(todo):
        if done >= FOLDS_PER_RUN: break
        anchor = anchors[i % len(anchors)]                 # drift: a different side each time
        try:
            answer = ask(fold_lesson(anchor, sliver, rule, world))
        except Exception as e:
            print(f"sphere {sp['n']}: the novice tunnel is closed ({str(e)[:60]})"); break
        if not answer: break
        lines = [_tokens(l) for l in answer.splitlines() if l.strip()]
        ok = _match_atom(sliver, lines) if ("." in sliver or ":" in sliver) else \
            any(sliver in l for l in lines)
        folds.append({"t": time.time(), "sliver": sliver, "anchor": anchor["key"],
                      "anchor_world": anchor["world"], "filled": bool(ok),
                      "said": (answer or "")[:300]})
        if ok: filled.add(sliver)
        done += 1
    json.dump(sp, open(sphere_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    remaining = [s for s in slivers_of(rule, sp["contents"].get("attempts", [])) if s not in filled]
    print(f"sphere {sp['n']} drifted: {done} folds, {len(filled)} slivers filled, "
          f"{len(remaining)} still nothing")
    if not remaining:
        return _ring_expanded(sp, sphere_path)
    return {"n": sp["n"], "filled": len(filled), "remaining": len(remaining)}


def _ring_expanded(sp: Dict, sphere_path: str) -> Dict:
    """Every sliver filled: the novice ring reaches the void point — lift the ejection."""
    sp["processed_by_folding"] = {"t": time.time(), "folds": len(sp.get("folds", []))}
    json.dump(sp, open(sphere_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    fl = _load(FLOWER, {})
    world, key = sp["sources"]["world"], sp["contents"]["rule"].get("key", "")
    v = fl.get(world, {}).get("voids", {}).get(key)
    if v and v.get("ejected"):
        v["reopened"] = {"t": time.time(), "by": f"sphere {sp['n']} folding", "was": v.pop("ejected")}
        json.dump(fl, open(FLOWER, "w", encoding="utf-8"), indent=1)
    print(f"sphere {sp['n']}: every sliver filled — the ring expanded; "
          f"'{key}' reopened for the bell")
    return {"n": sp["n"], "ring_expanded": True}


def status() -> None:
    for p in sorted(glob.glob(os.path.join(SPHERES, "sphere_*.json"))):
        sp = _load(sp_p := p, {})
        folds = sp.get("folds", [])
        filled = sum(1 for f in folds if f["filled"])
        state = ("ring expanded" if sp.get("processed_by_folding")
                 else "answered from outside" if sp.get("answer") else "drifting")
        print(f"sphere {sp.get('n')}: {sp.get('sources', {}).get('world')} / "
              f"'{sp.get('contents', {}).get('rule', {}).get('key', '?')}' — {state} "
              f"({filled}/{len(folds)} folds filled)")
    if not glob.glob(os.path.join(SPHERES, "sphere_*.json")):
        print("no spheres to drift")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.status:
        status()
    elif a.demo:
        def stub(t):                                   # a novice who can use a piece shown beside an anchor
            piece = t.split('the part that matters now is "')[1].split('"')[0]
            return f"in that world, {piece} is how it works"
        for p in sorted(glob.glob(os.path.join(SPHERES, "sphere_*.json"))):
            while True:
                r = drift(p, ask=stub)
                if not r or r.get("ring_expanded"): break
    else:
        for p in sorted(glob.glob(os.path.join(SPHERES, "sphere_*.json"))):
            drift(p)
