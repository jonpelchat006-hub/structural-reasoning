r"""
mika_tree.py - MIKA'S MEMORY AS A GROWING TREE OF CUBES (Jonathan, Oct 16 2026)

  "she is kind of like a plant and she should grow as she processes things ... she is like the core and then each game
   would be different trunks in different directions and they would get their own branches and grow a little at a time"
  "each cell growth would be like adding another cube into our space"

Every node is a cube with the same shape: {id, kind, parent, born, data, cells, strength, evidence}.
  CORE    D:\planet\mika\tree\core.json            lessons that work in any game. A lesson starts as a SEED (seen in one
                                                    game, or told to her) and moves into the core when a second game confirms it.
  TRUNK   D:\planet\mika\tree\<game>\trunk.json    one per game: what its actions do, how far she has grown into it
  BRANCH  D:\planet\mika\tree\<game>\L<n>.json     one per level: its cells
  CELL    a cube inside a branch: a route, a recipe, an effect (a thing that did something), a pruned thing
          (tried 3+ times, never did anything), a success snapshot (the screen just before the winning press).
          A cell's strength grows each time a life confirms it.
  RINGS   D:\planet\mika\tree\rings\<date>.json    each day's growth, by kind:
          tip (reached somewhere new) - thicken (did a known thing better or again) - light (found something that
          changes) - prune (stopped feeding a dead thing) - graft (a lesson tried in another trunk) - stall (no growth).
Nothing here plays the game; mika_mind.py calls grow() after each life.
"""
from __future__ import annotations
import json, os, time
import numpy as np

ROOT = r"D:\planet\mika\tree" if os.name == "nt" else "/tmp/mika/tree"
EFFECT = {"changed", "refill", "level"}
DEAD = {"wall", "nothing", "unreachable", "untestable"}


def _p(*a): return os.path.join(ROOT, *a)


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as fh: return json.load(fh)
    except Exception: return default


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh: json.dump(obj, fh, indent=1)
    os.replace(tmp, path)


def cube(id_, kind, parent, data=None):
    return {"id": id_, "kind": kind, "parent": parent, "born": time.strftime("%Y-%m-%d %H:%M"), "data": data or {}, "cells": {}, "strength": 0, "evidence": []}


def core():
    c = _load(_p("core.json"), None)
    if c is None:
        c = cube("core", "core", None, {"note": "lessons that work in any game; seeds wait for a second game to confirm them"})
        _save(_p("core.json"), c)
    return c


def trunk(game):
    t = _load(_p(game, "trunk.json"), None)
    if t is None:
        t = cube(game, "trunk", "core", {"actions": {}, "best_level": 0, "lives": 0}); _save(_p(game, "trunk.json"), t)
    return t


def branch(game, lvl):
    b = _load(_p(game, f"L{lvl + 1}.json"), None)
    if b is None:
        b = cube(f"{game}/L{lvl + 1}", "branch", game, {"level": lvl + 1, "state": "growing", "lives_on_it": 0}); _save(_p(game, f"L{lvl + 1}.json"), b)
    return b


def add_cell(node, cid, kind, data, evidence, events, game, lvl, growth=None, what=None):
    """a new cube inside a node, or a stronger one if it is already there"""
    c = node["cells"].get(cid)
    if c is None:
        c = cube(cid, kind, node["id"], data); node["cells"][cid] = c
        if growth: events.append({"game": game, "level": lvl + 1 if lvl is not None else None, "growth": growth, "what": what or f"new {kind}: {cid}"})
    else:
        c["data"].update(data)
    c["strength"] += 1
    if evidence and evidence not in c["evidence"]: c["evidence"] = (c["evidence"] + [evidence])[-12:]
    return c


def objects(frame):
    """the screen as a list of things: per colour, each connected patch with its box (for snapshots)"""
    f = np.asarray(frame) % 16; H, W = f.shape; seen = np.zeros_like(f, bool); out = []
    bg = int(np.bincount(f.ravel()).argmax())
    for y in range(H):
        for x in range(W):
            if seen[y, x] or f[y, x] == bg: continue
            col = f[y, x]; stack = [(y, x)]; seen[y, x] = True; cells = []
            while stack:
                cy, cx = stack.pop(); cells.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny, nx] and f[ny, nx] == col: seen[ny, nx] = True; stack.append((ny, nx))
            ys, xs = zip(*cells)
            out.append({"colour": int(col), "n": len(cells), "box": [min(ys), min(xs), max(ys), max(xs)]})
    return {"background": bg, "things": sorted(out, key=lambda o: -o["n"])[:40]}


def snapshot(game, lvl, frames_path, rec_rows, life_no, events):
    """the screen just before the press that won a level, the press itself, and the things on screen"""
    try:
        F = np.load(frames_path)["F"]
    except Exception:
        return None
    prev = 0
    for t, r in enumerate(rec_rows):
        lv = int(r.get("levels", 0) or 0)
        if lv > prev and prev == lvl and t < len(F):
            os.makedirs(_p(game), exist_ok=True)
            np.save(_p(game, f"L{lvl + 1}_win_frame.npy"), F[t].astype(np.int8))
            return {"press": [int(r.get("a", 0) or 0), int(r.get("x", -1) if r.get("x") is not None else -1), int(r.get("y", -1) if r.get("y") is not None else -1)],
                    "press_no": t + 1, "frame": _p(game, f"L{lvl + 1}_win_frame.npy"), "screen": objects(F[t]), "life": life_no}
        prev = lv
    return None


def grow(game, journal, life, life_no, rec_rows=None, frames_path=None, recipe_log=None, log=print, day=None):
    """after a life: add cells, strengthen the ones it confirmed, write today's ring. Returns the events."""
    events = []; ev = f"{game} life {life_no}"
    t = trunk(game); t["data"]["lives"] = t["data"].get("lives", 0) + 1
    reached = int(life.get("levels", 0))
    if reached > t["data"].get("best_level", 0):
        events.append({"game": game, "level": reached, "growth": "tip", "what": f"reached level {reached + 1} for the first time"})
        t["data"]["best_level"] = reached
    # every life's experiments, per level, over all lives (for pruning and effects)
    hist = {}
    for L in journal.get("lives", []):
        for e in L.get("experiments", []):
            if "level" in e: hist.setdefault(int(e["level"]), {}).setdefault(str(e["id"]), []).append(e.get("result"))
    for lvl in range(0, reached + 1):
        b = branch(game, lvl)
        b["data"]["lives_on_it"] = b["data"].get("lives_on_it", 0) + 1
        before = sum(c["strength"] for c in b["cells"].values()); n_before = len(b["cells"])
        mine = [e for e in life.get("experiments", []) if int(e.get("level", -1)) == lvl]
        for e in mine:
            if e.get("result") in EFFECT:
                add_cell(b, f"effect:{e['id']}", "effect", {"thing": e["id"], "does": e.get("result")}, ev, events, game, lvl,
                         growth="light", what=f"{e['id']} {e.get('result')} - something that changes")
        for tid, rs in hist.get(lvl, {}).items():
            if len(rs) >= 3 and all(r in DEAD for r in rs) and f"pruned:{tid}" not in b["cells"]:
                add_cell(b, f"pruned:{tid}", "pruned", {"thing": tid, "tries": len(rs)}, ev, events, game, lvl)
        n_pruned = sum(1 for k in b["cells"] if k.startswith("pruned:"))
        newly = n_pruned - sum(1 for k in b.get("_pruned_before", []))
        r = journal.get("routes", {}).get(str(lvl))
        if r:
            old = b["cells"].get("route")
            add_cell(b, "route", "route", {"presses": r["presses"], "len": r["len"]}, ev, events, game, lvl, growth="thicken", what=f"route of {r['len']} presses")
            if old and old["data"].get("len") and r["len"] < old["data"]["len"]:
                events.append({"game": game, "level": lvl + 1, "growth": "thicken", "what": f"route shortened {old['data']['len']} -> {r['len']}"})
            elif old and lvl < reached:
                events.append({"game": game, "level": lvl + 1, "growth": "thicken", "what": f"route held ({r['len']} presses), strength {b['cells']['route']['strength']}"})
        for st in (recipe_log or []):                       # only a recipe step further than any life got before is growth
            if int(st.get("level", -1)) == lvl and st.get("result") in EFFECT and st["step"] > b["data"].get("best_recipe_step", 0):
                b["data"]["best_recipe_step"] = st["step"]
                events.append({"game": game, "level": lvl + 1, "growth": "light", "what": f"recipe step {st['step']}/{st['of']} {st['id']} -> {st['result']} (furthest yet)"})
        # HER OWN LEADERBOARD (Oct 16): presses this life took to clear the level; a new best is thickening
        lp = life.get("level_presses") or []
        if lvl < reached and lvl < len(lp):
            took = int(lp[lvl]) - (int(lp[lvl - 1]) if lvl > 0 else 0)
            recs = b["data"].setdefault("records", [])
            best = min([x["presses"] for x in recs], default=None)
            recs.append({"life": life_no, "date": (day or time.strftime("%Y-%m-%d")), "presses": took, "mode": life.get("mode", "push")})
            b["data"]["records"] = recs[-30:]
            b["data"]["best"] = took if best is None else min(best, took)
            if best is not None and took < best:
                events.append({"game": game, "level": lvl + 1, "growth": "thicken", "what": f"new personal best: {took} presses (was {best})"})
        for t_ in life.get("trim_log", []):
            if int(t_.get("level", -1)) == lvl and t_.get("result") != "level":
                b["data"].setdefault("trim_failed", []).append(int(t_["len"]))
        # HER CHANGES OF MIND: holds, breaks, detours, surprises on the path (logged, not growth by themselves)
        wl = [w for w in life.get("weigh_log", []) if int(w.get("level", -1)) == lvl]
        dt = [w for w in life.get("detours", []) if int(w.get("level", -1)) == lvl]
        sl = [w for w in life.get("surprise_log", []) if int(w.get("level", -1)) == lvl]
        if wl or dt or sl:
            events.append({"game": game, "level": lvl + 1, "growth": "weigh",
                           "what": f"held her path {sum(1 for w in wl if w.get('hold'))}x, let it break {sum(1 for w in wl if not w.get('hold'))}x, "
                                   f"{len(dt)} refill detour(s), {len(sl)} surprise(s) on the path"})
        if lvl < reached:
            b["data"]["state"] = "cleared"
            if "snapshot" not in b["cells"] and rec_rows and frames_path:
                s = snapshot(game, lvl, frames_path, rec_rows, life_no, events)
                if s: add_cell(b, "snapshot", "snapshot", s, ev, events, game, lvl, growth="light", what=f"saved what the screen looked like just before level {lvl + 1} was won")
        if newly > 0:
            events.append({"game": game, "level": lvl + 1, "growth": "prune", "what": f"{newly} thing(s) tried 3+ times that never did anything - no longer fed"})
        b["_pruned_before"] = [k for k in b["cells"] if k.startswith("pruned:")]
        if lvl == reached and not any(e_["level"] == lvl + 1 and e_["growth"] in ("tip", "light", "thicken") for e_ in events if e_.get("game") == game):
            b["data"]["state"] = "stalled" if b["data"]["lives_on_it"] >= 3 else "growing"
            events.append({"game": game, "level": lvl + 1, "growth": "stall", "what": f"no new growth on level {lvl + 1} this life ({b['data']['lives_on_it']} lives on it)"})
        _save(_p(game, f"L{lvl + 1}.json"), b)
    t["data"]["branches"] = sorted({f"L{k + 1}" for k in range(t["data"]["best_level"] + 1)})
    _save(_p(game, "trunk.json"), t)
    day = day or time.strftime("%Y-%m-%d"); ring = _load(_p("rings", f"{day}.json"), {"date": day, "events": []})
    ring["events"] += [dict(e, life=life_no) for e in events]; _save(_p("rings", f"{day}.json"), ring)
    for e in events: log(f"  grow: {e['game']} L{e['level']}: {e['growth']} - {e['what']}")
    return events


def seed_lesson(lid, text, game, source, events=None):
    c = core(); events = [] if events is None else events
    cell = c["cells"].get(lid)
    if cell is None:
        c["cells"][lid] = cell = cube(lid, "lesson", "core", {"text": text, "status": "seed", "seen_in": [game], "source": source})
    elif game not in cell["data"]["seen_in"]:
        cell["data"]["seen_in"].append(game); cell["strength"] += 1
        if len(cell["data"]["seen_in"]) >= 2 and cell["data"]["status"] == "seed":
            cell["data"]["status"] = "core"; events.append({"game": game, "level": None, "growth": "graft", "what": f"lesson confirmed in a second game, moved into the core: {text}"})
    _save(_p("core.json"), c)
    return cell


def show():
    c = core(); print(f"CORE: {len(c['cells'])} lesson(s)")
    for k, v in c["cells"].items(): print(f"  [{v['data']['status']}] {v['data']['text']}  (seen in {', '.join(v['data']['seen_in'])})")
    for g in sorted(d for d in os.listdir(ROOT) if os.path.isdir(_p(d)) and d != "rings"):
        t = trunk(g); print(f"TRUNK {g}: {t['data'].get('lives', 0)} lives, levels cleared {t['data'].get('best_level', 0)}")
        for fn in sorted(f for f in os.listdir(_p(g)) if f.startswith("L") and f.endswith(".json")):
            b = _load(_p(g, fn), {}); kinds = {}
            for k in b.get("cells", {}).values(): kinds[k["kind"]] = kinds.get(k["kind"], 0) + 1
            print(f"  BRANCH {fn[:-5]}: {b['data'].get('state')}, {b['data'].get('lives_on_it', 0)} lives on it, cells {kinds}")
    for fn in sorted(os.listdir(_p("rings")))[-3:] if os.path.isdir(_p("rings")) else []:
        r = _load(_p("rings", fn), {}); kinds = {}
        for e in r.get("events", []): kinds[e["growth"]] = kinds.get(e["growth"], 0) + 1
        print(f"RING {fn[:-5]}: {kinds}")


if __name__ == "__main__":
    show()
