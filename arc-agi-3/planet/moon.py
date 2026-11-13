#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
moon.py — ARC GAMES ARE MOONS: too big to absorb, contacted at 7 points, rolled to be known.

Jonathan (Aug 31): "wouldn't the ARC games be like empty circles we have to fill out? or
anything that comes from above like you or me? this prompt would be you connecting to a WALL
instead of an active domain and its tunnel — like a void wall: the letters make up its outside
but you have to fill in everything inside, and you can wrap your tunnel outside your ring and
grab onto a new chunk to work through. the game would be a circle you can only contact from the
7 CONTROLS, but there's still a big unknown radius to it and we have to ROLL it around to
figure it out. but it would be really big too, so we probably couldn't absorb it into the
planet — it would have to be like building a MOON."

Three ideas, each mechanical:

  THE VOID WALL — an active domain has its own tunnel (Mika: instruments, §5-9 of the tunnel
      doc). A prompt from above, or an ARC game, has NO tunnel: only a boundary is given (the
      letters; the pixels) and everything inside is unfilled. The coupling is therefore not
      tunnel-to-tunnel but tunnel-to-WALL: the ring wraps its own tunnel OUTSIDE itself and
      engulfs a chunk. §8's pinch-off was endocytosis (pushed in from inside); this is the
      same membrane move run outward — phagocytosis: wrapping around foreign mass to work on
      it. The two are one mechanism in two directions.
  THE 7 CONTACTS AND THE ROLL — an ARC-AGI-3 game can be touched at exactly SEVEN points:
      RESET and ACTION1..ACTION6 (arcshim.GameAction.ALL — the count is the spec's, not a
      metaphor). Everything else is unknown radius. ROLLING = pressing each contact and
      recording what surface comes off on us: for every action taken, the observed effect
      class (win / game_over / score_up / changed / nothing). The rolled surface is the map
      of which contacts do what; the unknown radius is what has never come off on any roll.
  THE MOON — the game is too big to fold into a planet core, and it should not be: it is not
      the planet's own experience, it is a foreign body. So it ACCRETES AS A MOON in orbit:
      D:\\planet\\moons\\<game>\\moon.json, one LAYER added per orbit (the daily ARC ritual
      IS the orbit — the moon comes around once a day and gets rolled a little more). The
      moon keeps its own surface map and its own layer history; nothing from it enters the
      planet's cores, exactly as nothing from the planet dissolves into the moon.

Usage:  python moon.py --roll          (roll the mock surface: 3 seeds, per-action effects)
        python moon.py --status
        (arc_daily.py adds one layer per daily orbit automatically)
"""
from __future__ import annotations
import argparse, json, os, sys, time
from typing import Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

MOONS = r"D:\planet\moons" if os.name == "nt" else "/tmp/moons"
CONTACTS = ["RESET", "ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6"]


def _path(game: str) -> str:
    return os.path.join(MOONS, game, "moon.json")


def load(game: str) -> Dict:
    try:
        m = json.load(open(_path(game), encoding="utf-8"))
        m.setdefault("shells", [])
        return m
    except Exception:
        return {"game": game, "born": time.time(),
                "contacts": {c: {"tried": 0, "effects": {}} for c in CONTACTS},
                "layers": [], "shells": []}


def save(game: str, m: Dict) -> None:
    os.makedirs(os.path.dirname(_path(game)), exist_ok=True)
    json.dump(m, open(_path(game), "w", encoding="utf-8"), indent=1)


def _effect(before, after) -> str:
    """What came off on this roll: the effect class of one press of one contact."""
    from arcshim import GameState
    if after.state == GameState.WIN: return "win"
    if after.state == GameState.GAME_OVER: return "game_over"
    if getattr(after, "score", 0) > getattr(before, "score", 0): return "score_up"
    return "changed" if after.frame != before.frame else "nothing"


def touch(m: Dict, action: str, effect: str) -> None:
    c = m["contacts"].setdefault(action, {"tried": 0, "effects": {}})
    c["tried"] += 1
    c["effects"][effect] = c["effects"].get(effect, 0) + 1


def rolled_fraction(m: Dict) -> float:
    """How much surface has come off: contacts pressed, weighted by having a NON-TRIVIAL
    dominant effect (a contact that only ever did nothing is still unknown radius)."""
    known = 0.0
    for c in CONTACTS:
        e = m["contacts"].get(c, {}).get("effects", {})
        if not e: continue
        known += 1.0 if max(e, key=e.get) != "nothing" else 0.4
    return round(known / len(CONTACTS), 3)


def roll_mocks(game: str = "ls20", seeds: int = 3, max_steps: int = 400) -> Dict:
    """Roll the moon against the mock surface: PriorAgent plays; every press is recorded."""
    from arc3_client import MockGame
    from arcshim import FrameData, GameState
    from prioragent import PriorAgent
    m = load(game)
    presses = shells = 0
    for seed in range(seeds):
        g = MockGame(seed)
        agent = PriorAgent(game_id=f"mock-{seed}")
        fr = FrameData.from_wire(g.frame()); frames = [fr]
        commands = []                      # the OUTPUT half: the string of commands being written
        for _ in range(max_steps):
            if agent.is_done(frames, fr): break
            act = agent.choose_action(frames, fr)
            wire = g.frame() if act.name == "RESET" else \
                g.act(act.name, act.data.get("x"), act.data.get("y")) if act.name == "ACTION6" else \
                g.act(act.name)
            nfr = FrameData.from_wire(wire)
            touch(m, act.name, _effect(fr, nfr)); presses += 1
            commands.append(act.name)
            fr = nfr; frames.append(fr)
            if len(frames) > 40: frames = frames[-40:]
            if fr.state in (GameState.WIN, GameState.GAME_OVER): break
        if fr.state == GameState.WIN:
            # the bubble came in empty; this is it FILLED, sent back up as the commands.
            # keep one shell per surface (seed), always the shortest string that wins.
            old = next((s for s in m["shells"] if s["surface"] == f"mock-{seed}"), None)
            if old is None or len(commands) < len(old["commands"]):
                m["shells"] = [s for s in m["shells"] if s["surface"] != f"mock-{seed}"]
                m["shells"].append({"t": time.time(), "surface": f"mock-{seed}",
                                    "steps": len(commands), "commands": commands})
                shells += 1
    save(game, m)
    return {"presses": presses, "rolled": rolled_fraction(m), "new_shells": shells,
            "shells": len(m["shells"])}


def roll_real(game: str, trans_file: str) -> Dict:
    """Roll the moon against the REAL game surface (the live run's actual contact->effect log),
    not the mock. This is the body we actually have to know — the live 0 showed the mock was a
    different planet."""
    m = load(game)
    m["real"] = True                            # this moon has felt the real game
    presses = 0
    try:
        for line in open(trans_file, encoding="utf-8"):
            if not line.strip(): continue
            r = json.loads(line)
            touch(m, r["action"], r["effect"]); presses += 1
    except Exception as e:
        return {"presses": 0, "error": str(e)[:80]}
    save(game, m)
    return {"presses": presses, "rolled": rolled_fraction(m), "real": True}


def orbit(game: str, kind: str, stats: Dict) -> Dict:
    """One pass of the orbit (the daily ritual): accrete a layer; the moon grows, the planet
    core stays untouched."""
    m = load(game)
    layer = {"t": time.time(), "date": time.strftime("%Y-%m-%d"), "kind": kind,
             "n": len(m["layers"]) + 1, "rolled": rolled_fraction(m), **stats}
    m["layers"].append(layer)
    save(game, m)
    return layer


def status() -> None:
    import glob
    paths = glob.glob(os.path.join(MOONS, "*", "moon.json"))
    if not paths: print("no moons — nothing from above has been wrapped yet"); return
    for p in sorted(paths):
        m = json.load(open(p, encoding="utf-8"))
        rolled = rolled_fraction(m)
        pressed = sum(1 for c in CONTACTS if m["contacts"].get(c, {}).get("tried"))
        print(f"moon {m['game']}: {pressed}/7 contacts pressed, surface rolled {rolled:.0%}, "
              f"{len(m['layers'])} layers accreted, {len(m.get('shells', []))} shells filled "
              f"(winning command strings, ready to send back up)")
        for c in CONTACTS:
            cc = m["contacts"].get(c, {})
            if not cc.get("tried"): print(f"  {c:8s}: unknown radius — never pressed"); continue
            eff = ", ".join(f"{k} x{v}" for k, v in
                            sorted(cc["effects"].items(), key=lambda x: -x[1])[:3])
            print(f"  {c:8s}: {cc['tried']} presses -> {eff}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--roll", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--game", default="ls20")
    a = ap.parse_args()
    if a.roll:
        r = roll_mocks(a.game)
        print(f"rolled the {a.game} moon against the mocks: {r['presses']} presses, "
              f"surface {r['rolled']:.0%} known")
    if a.status or not a.roll:
        status()
