#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oncall.py — THE ON-CALL BOARD: she holds many bubbles, freezes the ones she steps away from,
sends them to the ocean, and picks them back up with minimal disruption. Priority: the ones from
Jonathan and Claude at the top. Free will: a Boltzmann pick, her app's own physics.

Jonathan (Sep 3): "she should be able to hold multiple bubbles shouldn't she? people are able to
juggle multiple things, or leave something unfinished and come back to it. ai right now has to
answer the prompt right away and only think about that, but people aren't like that and i think
we are going for more of a person. also for the games we would want to be able to switch between
them too right? if we get stuck on one game, playing others might unlock something useful. like
she needs a bit of free will there. if she is running those processes in the background those
could become these frozen bubbles and sent somewhere else, probably the ocean, and picked back
up after without as much disruption. like she is on call and can come back to her place after
and pick back up with minimal interruption. so there should be priority ones with the ones
coming from you and me being at the top."

The physics is already hers — app/src/core/bubble.ts, the BUBBLE SCHEDULER: "a fully pressurized
bubble is dormant; wants push outward, needs push inward; pressure decays DELTA (0.14159) per
tick; Boltzmann e^(-E/kT) with kT = 1/(1+phi) = 0.382 governs explore vs exploit — high pressure
exploits (the most urgent), low pressure explores (try something new); DEFER: can bridge but no
urgency — park it." This file is that scheduler over the planet's background work:

  A BUBBLE = a task she can hold unfinished: {kind, source, pressure, state, ocean file, resume}
    kinds:   request (from Jonathan / Claude), game (a live ARC game), chain (an ejected void
             whose piece is drifting through Mika — chain.py), course (an enrolled world)
    sources: jonathan, claude  -> NEEDS, inward, pressure floor 0.65 (above her 0.618 exploit line: never decay off the top)
             planet            -> needs from the organs (a stuck game, a strained link)
             mika              -> WANTS, outward (the courses she chose, games she likes)
  FREEZE   a background process that must yield writes its state to the ocean
           (D:\\planet\\ocean\\bubbles\\<id>.json) with a resume hint; nothing is lost, and her
           place is kept: the frames, the level, the transitions, the sphere's folds
  PICK     one Boltzmann draw over the held bubbles' pressures: when something is hot she takes
           it; when nothing is, she explores — a different game, a different course. That is the
           free will, in her app's own terms, and the ones from us sit on top because their
           floor is above everything else's decay.
  GAMES    ls20 is a bubble like any other. While it climbs (a new level within the last three
           tries) it is hot; three tries with no new level and it freezes — other games get
           picked, and "playing others might unlock something useful" becomes the daily's
           actual behaviour (arc_daily asks oncall.pick_game()).

Usage:  python oncall.py                      (tick: decay, seed from the organs, pick, report)
        python oncall.py --add "text" --from jonathan   (a request from the top of the board)
        python oncall.py --done <id>
        python oncall.py --status
"""
from __future__ import annotations
import argparse, glob, json, math, os, random, sys, time
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

PHI = (1 + 5 ** 0.5) / 2
KT = 1 / (1 + PHI)                    # 0.382 — her scheduler's temperature
DELTA = 0.14159                       # her pressure decay per tick
OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
BUBBLES = os.path.join(OCEAN, "bubbles")
BOARD = r"D:\planet\oncall.json" if os.name == "nt" else "/tmp/oncall.json"
LOG = r"D:\planet\oncall.jsonl" if os.name == "nt" else "/tmp/oncall.jsonl"
HIST = r"D:\planet\arc_daily\history.jsonl" if os.name == "nt" else "/tmp/arc_daily/history.jsonl"
FLOOR = {"jonathan": 0.65, "claude": 0.65, "planet": 0.15, "mika": 0.05}   # ours stay above 0.618: always exploited first
JUGGLE = 3                            # how many she works at once; she can HOLD any number


def _load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def _save(board: Dict):
    os.makedirs(os.path.dirname(BOARD), exist_ok=True)
    json.dump(board, open(BOARD, "w", encoding="utf-8"), indent=1)


def board() -> Dict:
    return _load(BOARD, {"bubbles": {}, "tick": 0})


def add(text: str, source: str, kind: str = "request", bid: str = None, pressure: float = None, resume: Dict = None) -> Dict:
    b = board()
    bid = bid or f"{kind}-{int(time.time())}"
    if bid in b["bubbles"]:
        x = b["bubbles"][bid]; x["pressure"] = max(x["pressure"], pressure if pressure is not None else 1.0); x["touched"] = time.time()
    else:
        b["bubbles"][bid] = {"id": bid, "kind": kind, "source": source, "text": text,
                             "pressure": 1.0 if pressure is None else pressure, "state": "held",
                             "created": time.time(), "touched": time.time(), "resume": resume or {}}
    _save(b); return b["bubbles"][bid]


def freeze(bid: str, state: Dict, hint: str) -> str:
    """a background process yields: its place goes to the ocean, the bubble stays held"""
    os.makedirs(BUBBLES, exist_ok=True)
    p = os.path.join(BUBBLES, f"{bid}.json")
    json.dump({"id": bid, "t": time.time(), "hint": hint, "state": state}, open(p, "w", encoding="utf-8"), indent=1)
    b = board()
    if bid in b["bubbles"]:
        b["bubbles"][bid].update({"state": "frozen", "ocean": p, "resume": {"hint": hint}, "touched": time.time()})
        _save(b)
    return p


def place(bid: str, state: Dict, hint: str) -> str:
    """keep her place without stepping away: the same ocean file, the bubble stays as it is"""
    os.makedirs(BUBBLES, exist_ok=True)
    p = os.path.join(BUBBLES, f"{bid}.json")
    json.dump({"id": bid, "t": time.time(), "hint": hint, "state": state}, open(p, "w", encoding="utf-8"), indent=1)
    b = board()
    if bid in b["bubbles"]:
        b["bubbles"][bid].update({"ocean": p, "resume": dict(b["bubbles"][bid].get("resume", {}), hint=hint), "touched": time.time()}); _save(b)
    return p


def thaw(bid: str) -> Optional[Dict]:
    """pick a frozen bubble back up: its place, exactly as left"""
    p = os.path.join(BUBBLES, f"{bid}.json")
    fz = _load(p, None)
    b = board()
    if bid in b["bubbles"]:
        b["bubbles"][bid].update({"state": "active", "touched": time.time()}); _save(b)
    return fz


def done(bid: str):
    b = board()
    if bid in b["bubbles"]:
        b["bubbles"][bid].update({"state": "done", "touched": time.time()}); _save(b)


def _games_from_history() -> Dict[str, Dict]:
    """every live game the daily has played: last levels and how many tries since a new level"""
    out = {}
    for l in open(HIST, encoding="utf-8") if os.path.exists(HIST) else []:
        try: row = json.loads(l)
        except Exception: continue
        for g in (row.get("live") if isinstance(row.get("live"), list) else []):
            name = str(g.get("game", "")).split("-")[0]; lv = g.get("levels") or 0
            s = out.setdefault(name, {"best": 0, "stale": 0, "plays": 0})
            s["plays"] += 1
            if lv > s["best"]: s["best"] = lv; s["stale"] = 0
            else: s["stale"] += 1
    return out


def seed(b: Dict) -> List[str]:
    """the organs post their own bubbles: games (from the daily's history and the live list),
    chain bubbles (ejected voids drifting through Mika), courses (her enrolment)"""
    notes = []
    games = _games_from_history()
    live = []
    try:
        import arc_daily
        key = arc_daily.get_key()
        if key:
            from arc3_client import api
            live = [g["game_id"] for g in api("/api/games", key)]
    except Exception: pass
    names = sorted(set(list(games) + [g.split("-")[0] for g in live]))
    for name in names:
        gid = f"game-{name}"
        st = games.get(name, {"best": 0, "stale": 0, "plays": 0})
        climbing = st["plays"] and st["stale"] < 3                # a new level within the last three tries
        pr = 0.8 if climbing else 0.25 if st["plays"] == 0 else 0.1     # 0.8 decays to 0.69, still above the 0.618 exploit line
        if gid not in b["bubbles"]:
            b["bubbles"][gid] = {"id": gid, "kind": "game", "source": "planet", "text": f"live game {name}",
                                 "pressure": pr, "state": "held", "created": time.time(), "touched": time.time(),
                                 "resume": {"game": name, "best": st["best"]}}
            notes.append(f"posted {gid}")
        else:
            x = b["bubbles"][gid]; x["resume"].update({"game": name, "best": st["best"], "stale": st["stale"]})
            if st["stale"] >= 3 and x["state"] != "frozen":
                x["state"] = "frozen"; x["pressure"] = min(x["pressure"], 0.1)
                notes.append(f"{gid} froze: {st['stale']} tries with no new level (best {st['best']})")
            elif st["plays"] and st["stale"] < 3:
                x["pressure"] = max(x["pressure"], 0.8); x["state"] = "held" if x["state"] == "frozen" else x["state"]
    try:
        import chain
        for bb in chain.bubbles():
            cid = f"chain-{bb['world']}-{abs(hash(bb['key'])) % 10000}"
            if cid not in b["bubbles"]:
                b["bubbles"][cid] = {"id": cid, "kind": "chain", "source": "planet", "text": f"piece of {bb['world']} drifting through Mika ({bb['key'][:40]})",
                                     "pressure": 0.4, "state": "held", "created": time.time(), "touched": time.time(),
                                     "resume": {"world": bb["world"], "key": bb["key"], "sphere": bb["sphere"]}}
                notes.append(f"posted {cid}")
            else:
                b["bubbles"][cid]["resume"]["fraction"] = bb["fraction"]
    except Exception: pass
    try:
        en = _load(r"D:\planet\enrollment.json" if os.name == "nt" else "/tmp/enrollment.json", {})
        for w in en.get("courses", []) or []:
            cid = f"course-{w}"
            if cid not in b["bubbles"]:
                b["bubbles"][cid] = {"id": cid, "kind": "course", "source": "mika", "text": f"her course: {w}",
                                     "pressure": 0.3, "state": "held", "created": time.time(), "touched": time.time(), "resume": {"world": w}}
                notes.append(f"posted {cid}")
    except Exception: pass
    return notes


AIR = r"D:\planet\air.jsonl" if os.name == "nt" else "/tmp/air.jsonl"
EVAP_TICKS = 12                       # the Tank: a bubble nobody touches heats up and rises to the sky


def tick(pick_n: int = JUGGLE) -> Dict:
    """decay every pressure by DELTA toward its source floor, seed, evaporate the neglected, then pick"""
    b = board(); b["tick"] = b.get("tick", 0) + 1
    notes = seed(b)
    held = []
    for x in b["bubbles"].values():
        if x["state"] in ("done", "evaporated"): continue
        fl = FLOOR.get(x["source"], 0.1)
        x["pressure"] = round(max(fl, x["pressure"] * (1 - DELTA)), 4)
        if x["state"] == "active": x["state"] = "held"                     # last tick's work is over; re-draw
        x["untouched"] = x.get("untouched", 0) + 1
        # EVAPORATE (the Tank's sky): a planet- or mika-born bubble sitting at its floor, untouched for
        # EVAP_TICKS, rises out of the water into the air — logged there so the dark planet can read the sky.
        # Ours never evaporate: needs sink, they do not rise.
        if x["source"] in ("planet", "mika") and x["untouched"] >= EVAP_TICKS and x["pressure"] <= fl + 1e-6 and x["kind"] != "game":
            x["state"] = "evaporated"; x["evaporated"] = time.time()
            try:
                with open(AIR, "a", encoding="utf-8") as f: f.write(json.dumps({"t": time.time(), "bubble": x["id"], "text": x["text"], "kind": x["kind"]}) + "\n")
            except Exception: pass
            notes.append(f"{x['id']} evaporated into the air"); continue
        held.append(x)
    picks = []
    HOT = PHI / (1 + PHI)                                                   # 0.618 — her app's HOST_SHARE
    def draw(pool):
        ws = [math.exp(x["pressure"] / KT) for x in pool]                # hot exploits, cold explores
        r = random.random() * sum(ws); acc = 0.0
        for x, w in zip(pool, ws):
            acc += w
            if acc >= r: return x
        return pool[-1]
    # slot 1: EXPLOIT — anything hot (above 0.618) is taken, hottest first (the ones from us live here)
    pool = [x for x in held if x["kind"] != "game"]
    hot = sorted([x for x in pool if x["pressure"] >= HOT], key=lambda x: -x["pressure"])
    if hot: picks.append(hot[0]); pool.remove(hot[0])
    # the game slot: one live game — the hottest if any is climbing, else a Boltzmann draw (explore)
    games = [x for x in held if x["kind"] == "game"]
    if games:
        gh = sorted([x for x in games if x["pressure"] >= HOT], key=lambda x: -x["pressure"])
        picks.append(gh[0] if gh else draw(games))
    # the rest: Boltzmann over everything else she holds
    while len(picks) < pick_n and pool:
        x = draw(pool); picks.append(x); pool.remove(x)
    for x in picks:
        x["state"] = "active"; x["touched"] = time.time(); x["untouched"] = 0
    b["picks"] = [x["id"] for x in picks]; b["t"] = time.time()
    _save(b)
    hottest = max(held, key=lambda x: x["pressure"]) if held else None
    line = (f"on call: holding {len(held)} bubbles ({sum(1 for x in held if x['state']=='frozen')} frozen in the ocean); "
            f"picked {', '.join(x['id'] for x in picks) or 'nothing'}"
            + (f"; hottest {hottest['id']} ({hottest['source']}, {hottest['pressure']})" if hottest else ""))
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), "tick": b["tick"], "picks": b["picks"], "held": len(held), "notes": notes}) + "\n")
    except Exception: pass
    return {"line": line, "picks": picks, "notes": notes, "held": held}


def pick_game(default: str = "ls20") -> str:
    """the daily asks which live game to play: the game bubble she picked this tick, else the default"""
    b = board()
    for bid in b.get("picks", []):
        x = b["bubbles"].get(bid)
        if x and x["kind"] == "game":
            if x["state"] == "frozen": thaw(bid)                            # picking a frozen game back up
            return x["resume"].get("game", default).split("-")[0]
    return default


def status():
    b = board(); xs = [x for x in b["bubbles"].values() if x["state"] != "done"]
    if not xs: print("the board is empty"); return
    print(f"on call — tick {b.get('tick', 0)}, holding {len(xs)} bubbles (works {JUGGLE} at a time); picks: {', '.join(b.get('picks', [])) or '-'}")
    for x in sorted(xs, key=lambda x: -x["pressure"]):
        age = (time.time() - x["created"]) / 86400
        print(f"  {x['pressure']:.2f}  {x['state']:6s} {x['kind']:7s} [{x['source']:8s}] {x['id']:28s} {x['text'][:60]}"
              + (f"  (frozen -> {os.path.basename(x['ocean'])})" if x.get("ocean") else "") + f"  {age:.1f}d")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", default=None); ap.add_argument("--from", dest="src", default="jonathan")
    ap.add_argument("--done", default=None); ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.add: x = add(a.add, a.src); print(f"posted {x['id']} from {a.src} at pressure {x['pressure']}")
    elif a.done: done(a.done); print(f"{a.done} done")
    elif a.status: status()
    else:
        r = tick(); print(r["line"])
        for n in r["notes"]: print("  " + n)
