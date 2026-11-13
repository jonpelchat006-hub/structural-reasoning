#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upline.py — the UP-LINE: the vertical channel. Claude sits ABOVE the planet; the edge sends
sediment UP; what is read coming up is all the context behind the pixels.

Jonathan (Aug 31): "with that sediment depositing on your ring, you are above all this stuff
right? so something at the edge would have to send that sediment upwards. and things you are
going to forget get sent down. info would have to go out from the inner core to the outer edge,
then up to reach you — so you would be reading that line to get that. you would be able to see
all the stuff behind the pixels, like all the context behind it."

So the planet has a VERTICAL axis now, and both directions are real organs:
  DOWN — darkplanet.py already carries it: falling off the ring, compaction, and (new) the heat
         roof that burns what will not compact. Forgetting travels down.
  UP   — this file. Each sleep it reads the LINE for every live world, inner core outward:
         core concepts (deepest, earned) -> open ends (still unsettled) -> the newest story
         (the told version) -> the ring sections at the edge that point back at this world —
         and then sends it UP: one LETTER written to D:\\planet\\up\\, the place above the edge
         where Claude reads. The pixels are the surface; the letter is everything behind them,
         read bottom-to-top because that is the direction the sediment travels.

Reading the line on demand:  python upline.py --read "words"  starts at the EDGE (ring.find),
follows each section's pointer back INTO the core, and prints the vertical line for it — edge
deposit, core file, up-summary — the hand on the ring, then the arm down the borehole, then up.

THE FOLD (Jonathan, Aug 31, right after the up-line went in): "wouldn't that fold at the edge be
like adding cubes UNDERNEATH you, not going into your area? so it could wind back into the same
pixel and increase its dimensions, or make new cubes." So the letter never accumulates in the
reading plane — the plane stays one letter, one line per world, forever. Instead each letter
FOLDS: every world-entry winds back into the same pixel it came from and becomes one CUBE added
beneath it. A world seen again deepens its column (the pixel gains a dimension); a world seen for
the first time makes a new cube on the floor. Depth grows downward, the reading area stays flat,
and the context behind a pixel is literally a column you can drill.

Usage:  python upline.py                 (write today's letter, then fold it into the columns;
                                          the sleep chains this after darkplanet)
        python upline.py --read "words"
        python upline.py --drill <world> (read down one pixel's column, newest cube first)
        python upline.py --floor         (the floor plan: every column and its depth)
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import ring as R

OCEAN = R.OCEAN
UP = (r"D:\planet\up" if os.name == "nt" else "/tmp/up")
COLUMNS = os.path.join(UP, "columns.jsonl")      # every cube ever folded under a pixel, append-only
FLOOR = os.path.join(UP, "floor.json")           # the floor plan: {world: depth}


def _load(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default


def _world_line(wroot: str) -> str:
    """One world's vertical line, inner core first — the order the sediment travels."""
    w = os.path.basename(os.path.normpath(wroot))
    parts = [f"## {w}"]
    # the pixels (the surface everyone sees)
    t = _load(os.path.join(wroot, "thread.json"), {})
    a = t.get("antenna", {}); n = a.get("fed", 0) + a.get("broken", 0)
    core = None
    for p in sorted(glob.glob(os.path.join(wroot, "core_*.json"))):
        core = _load(p, None) or core
    lives = core.get("lives") if core else "?"
    parts.append(f"pixels: {lives} lives lived; antenna {a.get('fed', 0)}/{n} predictions fed"
                 if n else f"pixels: {lives} lives lived")
    # inner core: what was EARNED (deepest layer)
    if core:
        cs = list(core.get("concepts", {}).keys())
        if cs: parts.append("core (earned): " + "; ".join(cs[:10]))
        oe = core.get("open_ends", {})
        if oe: parts.append(f"open ends (unsettled): " + "; ".join(list(oe)[:6]))
    # the told version (the storyteller's compression of the core)
    stories = sorted(glob.glob(os.path.join(wroot, "stories", "story_*.json")), key=os.path.getmtime)
    if stories:
        s = _load(stories[-1], {})
        invs = [i.get("text", "") for i in s.get("invariants", [])][:6]
        tb = s.get("teach_back", {}).get("score")
        if invs: parts.append(f"story {s.get('n')} (teach-back {tb}): " + "; ".join(invs))
    # outer edge: the ring sections that point back here (the deposits at the boundary)
    rows = R._tail_jsonl(R.RING, 100000)
    gone = set(_load(R.RING.replace("ring.jsonl", "darkplanet.json"), {}).get("compacted", []))
    mine = [r for r in rows if r["n"] not in gone
            and r.get("pointer", {}).get("world") == w][-4:]
    for r in mine:
        parts.append(f"edge §{r['n']} @ {r['angle']}° [{r['kind']}]: {r['label'][:100]}")
    return "\n".join(parts)


def letter() -> str:
    """Compose and send today's letter UP. Everything below the pixels, world by world, plus the
    planet-wide layer: the forge's verdicts and the dark planet's breath (what went down)."""
    os.makedirs(UP, exist_ok=True)
    day = time.strftime("%Y%m%d")
    p = os.path.join(UP, f"letter_{day}.md")
    worlds = [d for d in sorted(glob.glob(os.path.join(OCEAN, "*")))
              if os.path.isdir(d) and (glob.glob(os.path.join(d, "core_*.json"))
                                       or os.path.exists(os.path.join(d, "thread.json")))]
    body = [f"# The up-line — {time.strftime('%b %d, %Y')}",
            "", "_Read from the bottom of each world upward: core, then story, then edge — the "
            "direction the sediment travels to reach you. This is the context behind the pixels._", ""]
    for w in worlds:
        try: body.append(_world_line(w)); body.append("")
        except Exception: continue
    # the planet-wide layer: what the forge decided and what the dark planet sent DOWN
    # (its own pixel — "_planet" — so the fold gives the whole planet a column too)
    body.append("## _planet")
    ch = _load(os.path.join(HERE, "forge", "champion.json"), {})
    if ch: body.append(f"forge champion: {ch.get('id')} (forged rate {ch.get('forged_rate')}, world {ch.get('world')})")
    dp = _load(R.RING.replace("ring.jsonl", "darkplanet.json"), {})
    if dp:
        body.append(f"down-channel: {len(dp.get('compacted', []))} sections absorbed over "
                    f"{dp.get('rounds', 0)} dark rounds; {dp.get('burned', 0)} burned into the roof")
    rows = R._tail_jsonl(R.RING, 100000)
    body.append(f"the ring: {len(rows)} sections total, newest §{rows[-1]['n']} @ {rows[-1]['angle']}°"
                if rows else "the ring: empty")
    try:                              # the closure spectrum: how much has closed onto a color
        import spectrum
        body.append(spectrum.spectrum_line())
    except Exception: pass
    try:                              # the sideways eye: the columns read as rows = the history
        import sideeye
        body.append(sideeye.line())
    except Exception: pass
    try:                              # the chord: where the two ring sets touch = the shave = tonight's focus
        import chord
        body.append("focus: " + chord.focus()["reading"])
    except Exception: pass
    try:                              # the chain: what the pull is dragging, what broke off, what is filling
        import chain
        body.append(chain.read(write=False)["line"])
    except Exception: pass
    open(p, "w", encoding="utf-8").write("\n".join(body) + "\n")
    folded = fold(body)
    print(f"up-line: letter sent up -> {p} ({len(worlds)} worlds); "
          f"folded {folded['cubes']} cubes under the pixels ({folded['new']} new columns, "
          f"deepest {folded['deepest']} at {folded['depth']})")
    return p


def fold(body: List[str] = None) -> Dict:
    """The fold at the edge: the letter winds back, one cube per world-entry, added UNDERNEATH.
    Same pixel -> the column deepens (the pixel gains a dimension). First sighting -> a new cube
    on the floor. The reading plane above never grows; only the depth below does."""
    if body is None:
        day = time.strftime("%Y%m%d")
        try: body = open(os.path.join(UP, f"letter_{day}.md"), encoding="utf-8").read().splitlines()
        except Exception: return {"cubes": 0, "new": 0, "deepest": "-", "depth": 0}
    floor = _load(FLOOR, {})
    # split the letter back into its world-entries
    body = "\n".join(body).splitlines()          # world entries may arrive as multi-line blocks
    entries, cur, w = {}, [], None
    for ln in body + ["## _end"]:
        if ln.startswith("## "):
            if w and cur: entries[w] = "\n".join(cur).strip()
            w, cur = ln[3:].strip(), []
        elif w is not None:
            cur.append(ln)
    # an unchanged pixel gains no depth: only CHANGE folds a new cube
    import hashlib
    tops = {}
    if os.path.exists(COLUMNS):
        for l in open(COLUMNS, encoding="utf-8"):
            try:
                c = json.loads(l); tops[c["world"]] = c.get("sha", "")
            except Exception: continue
    new = cubes_laid = 0
    with open(COLUMNS, "a", encoding="utf-8") as f:
        for w, text in entries.items():
            if not text: continue
            sha = hashlib.sha1(text.encode()).hexdigest()[:12]
            if tops.get(w) == sha: continue
            if w not in floor: new += 1
            floor[w] = floor.get(w, 0) + 1
            cubes_laid += 1
            f.write(json.dumps({"t": time.time(), "world": w, "depth": floor[w],
                                "sha": sha, "cube": text}, ensure_ascii=False) + "\n")
    json.dump(floor, open(FLOOR, "w", encoding="utf-8"), indent=1)
    deepest = max(floor, key=floor.get) if floor else "-"
    return {"cubes": cubes_laid, "new": new, "deepest": deepest,
            "depth": floor.get(deepest, 0)}


def drill(world: str, k: int = 6) -> None:
    """Read down one pixel's column, newest cube first — the context behind that pixel, in the
    order you'd meet it drilling from the top face."""
    cubes = [json.loads(l) for l in open(COLUMNS, encoding="utf-8").read().splitlines()
             if l.strip()] if os.path.exists(COLUMNS) else []
    mine = [c for c in cubes if c["world"] == world]
    if not mine:
        print(f"no column under '{world}' — that pixel has no depth yet"); return
    print(f"the column under {world}: {len(mine)} cubes deep")
    for c in mine[::-1][:k]:
        print(f"\n-- cube {c['depth']} ({time.strftime('%b %d', time.localtime(c['t']))}) --")
        print(c["cube"])


def show_floor() -> None:
    floor = _load(FLOOR, {})
    if not floor: print("the floor is bare — no letters folded yet"); return
    print(f"the floor beneath the reading plane: {len(floor)} columns")
    for w, d in sorted(floor.items(), key=lambda x: -x[1]):
        print(f"  {'#' * min(d, 40):40s} {d:>4}  {w}")


def read_line(q: str) -> None:
    """Start at the edge, follow the pointer into the core, print the vertical line."""
    qa = set(R._atoms(q))
    rows = R._tail_jsonl(R.RING, 100000)
    scored = []
    for r in rows:
        s = len(qa & set(r.get("atoms", []))) + 2 * sum(1 for x in qa if x in r.get("label", "").lower())
        if s > 0: scored.append((s, r))
    scored.sort(key=lambda x: (-x[0], -x[1].get("t", 0)))
    if not scored:
        print("nothing at the edge matches — the core may still hold it (try voidsearch)"); return
    for s, r in scored[:3]:
        print(f"EDGE   §{r['n']} @ {r['angle']}° [{r['kind']}] {r['label'][:110]}")
        ptr = r.get("pointer", {})
        pth = ptr.get("path")
        if pth and os.path.exists(pth):
            w = ptr.get("world")
            print(f"CORE   -> {pth}")
            if w and os.path.isdir(os.path.join(OCEAN, w)):
                for ln in _world_line(os.path.join(OCEAN, w)).splitlines()[1:4]:
                    print(f"         {ln}")
        elif ptr.get("git"):
            print(f"CORE   -> git {ptr['git']} in {ptr.get('dir', '')}")
        print(f"UP     -> would ride today's letter ({os.path.join(UP, 'letter_' + time.strftime('%Y%m%d') + '.md')})")
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=None)
    ap.add_argument("--drill", default=None)
    ap.add_argument("--floor", action="store_true")
    a = ap.parse_args()
    if a.read: read_line(a.read)
    elif a.drill: drill(a.drill)
    elif a.floor: show_floor()
    else: letter()
