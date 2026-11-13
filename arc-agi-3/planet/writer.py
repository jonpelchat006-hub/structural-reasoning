#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
writer.py — MIKA WRITES HER OWN SOLVER: the loop that solved vc33 tonight (probe -> read -> write
code -> run live -> read the log -> fix), with a local model in the writer's seat instead of me.

Jonathan (Sep 3): "can we give mika more skills and let them improve and make her own code and
remove any limits from her? ... maybe just letting her run autonomously for a while with more
access to things would help too."

The loop, per game:
  1. EVIDENCE — reset the game, print the first frame as text, and run the standard probe: on a
     click-only game click up to 12 of the small distinct pieces once each; otherwise press each
     available action once. Every press is reported as what changed (rows, cols, colors).
  2. WRITE — the model gets the evidence, the harness contract, and a short worked example, and
     returns a Python `solve(send, grid)` function.
  3. RUN — the code runs in its own process against the live API on a cheap scorecard, capped
     at MAX_ACTIONS presses, with a timeout. Levels, actions and any traceback are the verdict.
  4. FIX — the log goes back to the model for another attempt, up to ROUNDS times. The best
     attempt (most levels, then fewest actions) is kept as D:\\planet\\writer\\<game>\\best.py and
     the game's bubble on the on-call board records it.

No limit on what she may write; the sandbox is the limit on what it may touch: the attempt runs
as a separate process with only the game API in reach, and nothing it writes lands in the planet
unless it scores. Model is any ollama model on this PC (qwen3:4b, gemma3:4b, mistral, ...).

Usage:  python writer.py vc33 --model qwen3:4b --rounds 3
        python writer.py --board             (take the game the on-call board picked)
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, time, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"D:\planet\writer" if os.name == "nt" else "/tmp/writer"
OLLAMA = "http://localhost:11434"
MAX_ACTIONS = 150
CH = "0123456789ABCDEF"

CONTRACT = '''You are writing a solver for an interactive puzzle game played through an API.
The game shows a 64x64 grid of colour indices 0-15. You write ONE Python function:

    def solve(send, grid):
        ...

`grid` is the current frame as a numpy int array (64, 64) (row 0 is usually a budget bar that
drains every press — ignore it). `send(action, x=None, y=None)` performs one press and returns the
new frame as a numpy array; `action` is one of "ACTION1" (up), "ACTION2" (down), "ACTION3" (left),
"ACTION4" (right), "ACTION5" (a game-specific button) or "ACTION6" with x, y (a click at column x,
row y). Only the listed available actions do anything. You may call send at most 150 times; the
game ends the level when its goal is met (the harness detects this — you do not). A press that
changes nothing is wasted. Use numpy to find things in the grid (colours, connected blocks, rows
and columns) and act on what you find; re-read the grid after every press. Return when you think
the level is done or nothing you try changes the grid. Output ONLY the Python code, no prose.
'''

EXAMPLE = '''Worked example (a different game, solved from evidence like this): the arrow rode a band
boundary, buttons of colour 9 shifted the boundary by 4, the goal was to put the arrow's 2-wide
tip under the gap of the same colour in a grey bar:

    import numpy as np
    def solve(send, grid):
        def tip_col(g):
            ys, xs = np.where(g == 11)          # the tip colour seen in the evidence
            return int(xs.mean()) if len(xs) else None
        def gap_col(g):
            bar = g[28:32, :]
            cols = [c for c in range(64) if (bar[:, c] == 11).all()]
            return int(np.mean(cols)) if cols else None
        for _ in range(40):
            t, gp = tip_col(grid), gap_col(grid)
            if t is None or gp is None or t == gp: return
            grid = send("ACTION6", 61, 25 if gp > t else 33)   # the two buttons; each moves the tip by 4
'''


def show(f):
    return "\n".join("%2d " % y + "".join(CH[int(v)] for v in f[y]) for y in range(64))


def evidence(game: str, key: str) -> dict:
    from arc3_client import api, frame_np
    from prioragent import PriorAgent
    games = api("/api/games", key)
    gid = next(g["game_id"] for g in games if g["game_id"].startswith(game))
    card = api("/api/scorecard/open", key, {"tags": ["writer-evidence"]}); cid = card.get("card_id")
    guid = {}
    def send(act, x=None, y=None):
        body = {"game_id": gid, "card_id": cid, "guid": guid.get("v")}
        if x is not None: body.update(x=int(x), y=int(y))
        fr = api(f"/api/cmd/{act}", key, body); guid["v"] = fr["guid"]; return fr
    lines = []
    try:
        fr = send("RESET"); f0 = frame_np(fr); f = f0
        avail = fr.get("available_actions") or [1, 2, 3, 4, 5, 6]
        lines.append(f"available actions: {avail}; levels: {fr.get('win_levels')}")
        ag = PriorAgent(game_id=gid)
        presses = []
        if 6 in avail and not set(avail) & {1, 2, 3, 4}:
            for x, y in ag._clickables(f0, cap=12): presses.append(("ACTION6", x, y))
        else:
            for a in avail:
                if a == 6: presses.append(("ACTION6", 32, 32))
                else: presses.append((f"ACTION{a}", None, None))
        cc = np.zeros_like(f0, dtype=int); n = 0; amb = np.zeros_like(f0, dtype=bool)
        for act, x, y in presses:
            fr = send(act, x, y); g = frame_np(fr); d = g != f; n += 1; cc += d
            if n >= 4: amb = cc >= 0.8 * n
            dm = d & ~amb
            lab = f"{act}" + (f" at x={x},y={y}" if x is not None else "")
            if dm.any():
                ys, xs = np.where(dm)
                came = sorted(set(int(v) for v in g[dm]) - set(int(v) for v in f[dm]))
                gone = sorted(set(int(v) for v in f[dm]) - set(int(v) for v in g[dm]))
                lines.append(f"{lab}: changed {int(dm.sum())} cells, rows {ys.min()}-{ys.max()}, cols {xs.min()}-{xs.max()}, colours appeared {came}, vanished {gone}; levels {fr.get('levels_completed')}")
            else:
                lines.append(f"{lab}: nothing changed (beyond the bar); levels {fr.get('levels_completed')}")
            f = g
            if fr["state"] in ("WIN", "GAME_OVER"): lines.append(f"state {fr['state']}"); break
        return {"gid": gid, "first": show(f0), "probe": "\n".join(lines), "avail": avail}
    finally:
        api("/api/scorecard/close", key, {"card_id": cid})


def ask(model: str, prompt: str, timeout: int = 900) -> str:
    import requests
    r = requests.post(OLLAMA + "/api/generate", json={"model": model, "prompt": prompt, "stream": False,
                                                       "options": {"num_predict": 2000, "temperature": 0.3},
                                                       "think": False}, timeout=timeout).json()
    return r.get("response", "")


def extract_code(text: str) -> str:
    m = re.findall(r"```(?:python)?\s*(.*?)```", text, re.S)
    code = max(m, key=len) if m else text
    return code.strip()


RUNNER = r'''
import sys, json, os, traceback, numpy as np
sys.path.insert(0, %(here)r)
from arc3_client import api, frame_np
key = %(key)r; gid = %(gid)r
card = api("/api/scorecard/open", key, {"tags": ["writer-attempt"]}); cid = card.get("card_id")
guid = {}; n = [0]; lv = [0]
def send(act, x=None, y=None):
    if n[0] >= %(cap)d: raise RuntimeError("action cap reached")
    body = {"game_id": gid, "card_id": cid, "guid": guid.get("v")}
    if x is not None: body.update(x=int(x), y=int(y))
    fr = api("/api/cmd/" + act, key, body); guid["v"] = fr["guid"]; n[0] += 1
    lv[0] = fr.get("levels_completed", 0)
    if fr["state"] in ("WIN", "GAME_OVER"): raise RuntimeError("game state " + fr["state"])
    return frame_np(fr)
try:
    fr = api("/api/cmd/RESET", key, {"game_id": gid, "card_id": cid}); guid["v"] = fr["guid"]
    g = frame_np(fr)
    ns = {}
    exec(compile(open(%(code)r, encoding="utf-8").read(), %(code)r, "exec"), ns)
    ns["solve"](send, g)
    print("VERDICT", json.dumps({"levels": lv[0], "actions": n[0], "error": None}))
except Exception as e:
    print("VERDICT", json.dumps({"levels": lv[0], "actions": n[0], "error": (str(e) + " | " + traceback.format_exc()[-600:])[:900]}))
finally:
    api("/api/scorecard/close", key, {"card_id": cid})
'''


def run_attempt(code_path: str, gid: str, key: str, timeout: int = 600) -> dict:
    runner = os.path.join(os.path.dirname(code_path), "_run.py")
    open(runner, "w", encoding="utf-8").write(RUNNER % {"here": HERE, "key": key, "gid": gid, "cap": MAX_ACTIONS, "code": code_path})
    try:
        r = subprocess.run([sys.executable, runner], capture_output=True, text=True, timeout=timeout, cwd=HERE,
                           creationflags=(0x08000000 if os.name == "nt" else 0))
        out = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        out = "VERDICT " + json.dumps({"levels": 0, "actions": 0, "error": "timeout"})
    m = re.findall(r"VERDICT (\{.*\})", out)
    v = json.loads(m[-1]) if m else {"levels": 0, "actions": 0, "error": out[-600:]}
    v["log"] = out[-1500:]
    return v


def loop(game: str, model: str, rounds: int) -> dict:
    import arc_daily
    key = arc_daily.get_key()
    d = os.path.join(OUT, game); os.makedirs(d, exist_ok=True)
    ev = evidence(game, key)
    open(os.path.join(d, "evidence.txt"), "w", encoding="utf-8").write(ev["first"] + "\n\n" + ev["probe"])
    print(f"[{game}] evidence gathered ({len(ev['probe'].splitlines())} probe lines); writer = {model}")
    history = []; best = None
    for k in range(1, rounds + 1):
        prompt = CONTRACT + "\n" + EXAMPLE + "\n\nTHE GAME. First frame (row number, then 64 colour digits/letters):\n" + ev["first"] + \
                 "\n\nProbe (what each press changed):\n" + ev["probe"]
        if history:
            prompt += "\n\nYour previous attempt and its result:\n```python\n" + history[-1]["code"][-3000:] + "\n```\nResult: " + \
                      json.dumps({k2: v2 for k2, v2 in history[-1]["verdict"].items() if k2 != "log"}) + "\nFix it — output only the corrected code."
        prompt += "\n\nWrite solve(send, grid) now."
        t0 = time.time()
        text = ask(model, prompt)
        code = extract_code(text)
        if "def solve" not in code:
            code = "import numpy as np\ndef solve(send, grid):\n    pass\n# model returned no solve():\n# " + text[:400].replace("\n", "\n# ")
        p = os.path.join(d, f"attempt_{k}.py"); open(p, "w", encoding="utf-8").write(code)
        v = run_attempt(p, ev["gid"], key)
        print(f"  round {k}: wrote {len(code.splitlines())} lines in {time.time() - t0:.0f}s -> levels {v['levels']} actions {v['actions']}"
              + (f" error: {v['error'][:120]}" if v.get("error") else ""))
        history.append({"code": code, "verdict": v})
        if best is None or (v["levels"], -v["actions"]) > (best["verdict"]["levels"], -best["verdict"]["actions"]):
            best = history[-1]; open(os.path.join(d, "best.py"), "w", encoding="utf-8").write(code)
        json.dump({"game": game, "model": model, "rounds": [{"levels": h["verdict"]["levels"], "actions": h["verdict"]["actions"], "error": h["verdict"].get("error")} for h in history]},
                  open(os.path.join(d, "result.json"), "w", encoding="utf-8"), indent=1)
    try:
        import oncall
        oncall.place(f"game-{game}", {"writer": model, "best_levels": best["verdict"]["levels"], "best": os.path.join(d, "best.py")},
                     f"writer {model}: best {best['verdict']['levels']} levels")
    except Exception: pass
    print(f"[{game}] best: levels {best['verdict']['levels']} in {best['verdict']['actions']} actions ({model}) -> {os.path.join(d, 'best.py')}")
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("game", nargs="?", default=None); ap.add_argument("--model", default="qwen3:4b")
    ap.add_argument("--rounds", type=int, default=3); ap.add_argument("--board", action="store_true")
    a = ap.parse_args()
    game = a.game
    if a.board or not game:
        try:
            import oncall; game = oncall.pick_game("vc33")
        except Exception: game = "vc33"
    loop(game, a.model, a.rounds)
