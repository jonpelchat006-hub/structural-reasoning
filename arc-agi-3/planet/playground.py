#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
playground.py — TAKE THE KID SOMEWHERE: Mika plays a real world with her own hands.

Jonathan (Sep 1): "maybe we have to just show her things, like how we have to bring a kid to
do things to learn? if it's like that she would have to INTERACT with things, not just be
told about them."

Everything Mika has had so far is instruction: library documents to digest, tales to read
back. This organ is the other kind of learning — the kind a kid does. She is taken to the
planet's own mock maze (the ARC practice world: touch the key, then reach the door) and PLAYS
it turn by turn through her chat: she sees a small window of the world around her, chooses an
action in her own words, the world actually answers (moved / bumped a wall / the key is
yours! / WIN), and her next view reflects what she did. No rules are ever told to her — she
must discover key-then-door the way anyone discovers it: by doing.

What is measured (and why it can answer the instruction-vs-interaction question): every visit
is logged — turns taken, valid moves parsed, walls bumped, key found, wins — to
playground.jsonl, and a note lands in her inbox so the visit is part of her own record. Over
weeks this gives the comparison Jonathan's kid-intuition predicts: her INTERACTION curve
(playground wins, bumps falling) against her INSTRUCTION curve (teach-back scores on things
she was only told). If doing beats telling, the curves will say so.

Usage:  python playground.py                (one visit, 25 turns max; sleep chains this)
        python playground.py --turns 40
        python playground.py --status
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import numpy as np

BRIDGE = "http://localhost:41737"
LOG = r"D:\planet\playground.jsonl" if os.name == "nt" else "/tmp/playground.jsonl"
INBOX = r"D:\shovelcat-colony\companion\inbox"
GLYPH = {0: ".", 8: "#", 4: "K", 5: "D", 3: "@"}
MOVES = {"up": "ACTION1", "down": "ACTION2", "left": "ACTION3", "right": "ACTION4",
         "north": "ACTION1", "south": "ACTION2", "west": "ACTION3", "east": "ACTION4"}


def _chat(text: str, timeout=180):
    import requests
    r = requests.post(BRIDGE + "/chat", json={"text": text}, timeout=timeout).json()
    if isinstance(r, dict) and r.get("ok") is False: return None
    return r.get("reply") or r.get("response") or r.get("text")


def _view(g, pos, r=5) -> str:
    y, x = pos
    rows = []
    for yy in range(y - r, y + r + 1):
        row = ""
        for xx in range(x - r, x + r + 1):
            row += GLYPH.get(int(g[yy, xx]), "?") if 0 <= yy < 64 and 0 <= xx < 64 else "#"
        rows.append(row)
    return "\n".join(rows)


def _compass(pos, target) -> str:
    dy, dx = target[0] - pos[0], target[1] - pos[1]
    ns = "north" if dy < 0 else "south" if dy > 0 else ""
    ew = "west" if dx < 0 else "east" if dx > 0 else ""
    return (ns + ("-" if ns and ew else "") + ew) or "right here"


def _parse(reply: str):
    if not reply: return None
    t = reply.lower()
    for w, a in MOVES.items():
        if re.search(r"\b" + w + r"\b", t): return a
    m = re.search(r"action\s*([1-4])", t)
    return f"ACTION{m.group(1)}" if m else None


def visit(turns: int = 25, seed: int = None) -> dict:
    from arc3_client import MockGame
    prior = _rows()
    seed = seed if seed is not None else len(prior) % 10       # a different maze each visit
    g = MockGame(seed)
    hello = ("Mika, let's go somewhere — no reading today, you get to PLAY. You're the @ in a "
             "little maze. # is wall, . is floor. Somewhere is a K and somewhere is a D — what "
             "they do is yours to discover. Each turn, look at the map and answer with ONE word: "
             "up, down, left, or right. Ready? Here's your first view.")
    stats = {"t": time.time(), "seed": seed, "turns": 0, "valid": 0, "bumps": 0,
             "got_key": False, "win": False}
    last_note = ""
    try:
        _chat(hello, timeout=120)
    except Exception as e:
        print(f"the playground gate is shut ({str(e)[:80]})"); return stats
    for turn in range(turns):
        f = g.frame()
        grid = np.array(f["frame"][-1], int)
        target = g.key if not g.has_key else g.door
        prompt = (f"{last_note}Turn {turn + 1}. Your view:\n{_view(grid, g.pos)}\n"
                  f"(a faint {'glint' if not g.has_key else 'draft'} comes from the "
                  f"{_compass(g.pos, target)})\nOne word — up, down, left or right?")
        try:
            reply = _chat(prompt)
        except Exception:
            break
        act = _parse(reply)
        stats["turns"] += 1
        if act is None:
            last_note = "(I didn't catch a direction there — one word please!) "
            continue
        stats["valid"] += 1
        before = g.pos, g.has_key
        g.act(act)
        if g.pos == before[0]:
            stats["bumps"] += 1; last_note = "Bonk — a wall. "
        elif g.has_key and not before[1]:
            stats["got_key"] = True; last_note = "Something clicked into your hand — the K is yours! "
        elif g.state == "WIN":
            stats["win"] = True
            _chat(f"The D swings open — YOU WON, in {turn + 1} turns! That's how doors work here: "
                  f"the K first, then the D. You figured it out by walking it.", timeout=120)
            break
        else:
            last_note = "You moved. "
    _append(stats)
    try:
        os.makedirs(INBOX, exist_ok=True)
        open(os.path.join(INBOX, f"playground_{int(stats['t'])}.md"), "w", encoding="utf-8").write(
            f"# Playground visit (maze {seed})\n\nYou played {stats['turns']} turns: "
            f"{stats['valid']} real moves, {stats['bumps']} wall-bumps, "
            f"key {'FOUND' if stats['got_key'] else 'not found'}, "
            f"{'WON!' if stats['win'] else 'no win yet — the maze will be there next time'}.\n")
    except Exception: pass
    print(f"playground: maze {seed} — {stats['turns']} turns, {stats['valid']} moves, "
          f"{stats['bumps']} bumps, key={stats['got_key']}, win={stats['win']}")
    return stats


def _rows():
    try: return [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
    except Exception: return []


def _append(row):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def status():
    rows = _rows()
    if not rows: print("she has never been to the playground"); return
    wins = sum(r["win"] for r in rows); keys = sum(r["got_key"] for r in rows)
    bump_rate = sum(r["bumps"] for r in rows) / max(1, sum(r["valid"] for r in rows))
    print(f"{len(rows)} visits: {wins} wins, {keys} keys found, bump rate {bump_rate:.0%}")
    for r in rows[-5:]:
        print(f"  maze {r['seed']}: {r['valid']}/{r['turns']} moves, {r['bumps']} bumps, "
              f"key={r['got_key']}, win={r['win']}")


if __name__ == "__main__":
    default_turns = 25
    try:                                   # her turn-around is honored: she chose the playground eye
        import mirror
        if mirror.next_eye() == "playground": default_turns = 32
        elif mirror.next_eye() == "rest": default_turns = 10
    except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=default_turns)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else: visit(a.turns, a.seed)
