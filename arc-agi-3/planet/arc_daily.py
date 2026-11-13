#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arc_daily.py — the DAILY ARC-AGI RITUAL: practice first, then try (Jonathan, Aug 29:
"do a practice run to see if anything's changed and then try").

1. PRACTICE (no key needed, Sep 4): the offline induction batch — induce.py over the 25 recorded
   public games (D:\\planet\\eye\\<game>.npz). The score is the number of action-operators that
   pass the gate, the vocabulary the live agent plays with, compared to the best earlier
   induction run in history.jsonl — the regression check: did anything we changed break the
   world model? (Until Sep 4 this step played a mock key-and-door maze no real game resembles.)
2. TRY (needs the live key): only if practice did not regress, the GENERAL AGENT (play.py: eye +
   induced operators + planner + touch-graph experiments + register budget + planned resets) plays
   the configured games on a live scorecard at three.arcprize.org. For ls20 the hand-written chain
   (ls20_chain.py) then runs as the ORACLE — a regression check of the game and the API, expected
   5/7, recorded on its own line, never the daily's score. Key from ARC_API_KEY or
   D:\\planet\\arc_key.txt. No key -> the try is skipped and the report says so.
3. RECORD: one row in D:\\planet\\arc_daily\\history.jsonl and a human-readable
   report_YYYYMMDD.txt. The trend across rows is the honest progress measure — including
   whether what the planet learns from watching and playing games ever transfers here.

Run:  python arc_daily.py            (the scheduled task runs this daily)
      python arc_daily.py --practice-only
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OUT = r"D:\planet\arc_daily" if os.name == "nt" else "/tmp/arc_daily"
OUT_EYE = r"D:\planet\eye" if os.name == "nt" else "/tmp/eye"
KEY_FILE = r"D:\planet\arc_key.txt"
LIVE_GAMES = ["ls20"]                 # default; the on-call board (oncall.py) may pick another game
try:
    import oncall
    LIVE_GAMES = [oncall.pick_game("ls20")]
except Exception: pass
REGRESS_MARGIN = 5                    # practice may lose this many gated operators (of ~53) before we call it a regression


def run_practice() -> dict:
    """PRACTICE (Sep 4): the offline induction batch — induce.py over the 25 recorded public games, no API,
    deterministic. The score is the number of action-operators that pass the gate (the world model's
    vocabulary), with the mean held-out accuracies alongside. That is what the live agent plays with, so a
    drop here is a real regression. The mock maze it replaces measured a key-and-door world no game has.
    A failed batch is reported as failed; mock wins cannot replace this evaluation."""
    try:
        return _induction_practice()
    except Exception as e:
        return {"agent": "induce.py", "status": "failed", "wins": None, "n": 0,
                "mean_steps": None, "error": f"induction batch failed: {str(e)[:240]}"}


def _induction_practice() -> dict:
    from uuid import uuid4
    from evaluation_batch import validate_completed
    run_id = uuid4().hex
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "induce.py"), "--run-id", run_id], capture_output=True, text=True, encoding="utf-8", timeout=1500,
                       cwd=HERE, creationflags=(0x08000000 if os.name == "nt" else 0))
    if r.returncode != 0:
        raise RuntimeError(f"induction exited {r.returncode}: {(r.stderr or r.stdout)[-240:]}")
    with open(os.path.join(OUT_EYE, "induce_results.json"), encoding="utf-8") as src:
        report = validate_completed(json.load(src), run_id)
    res = report["games"]
    gated = [(g, a, row["strict"]) for g, v in res.items() for a, row in v["actions"].items() if row["strict"] and row["strict"] != "restore"]
    best = [v["best"]["all"]["changed_acc"] for v in res.values() if v["best"]["all"]["changed_acc"] is not None]
    strict = [v["strict"]["all"]["changed_acc"] for v in res.values() if v["strict"]["all"]["changed_acc"] is not None]
    return {"agent": "induce.py", "status": "complete", "corpus_id": report["corpus_id"], "run_id": run_id,
            "wins": len(gated), "n": len(res), "games_with_operators": len(set(g for g, _, _ in gated)),
            "mean_best": round(sum(best) / len(best), 3) if best else None,
            "mean_strict": round(sum(strict) / len(strict), 3) if strict else None,
            "mean_steps": None}


def _prioragent_practice(seeds: int = 10, max_steps: int = 1500) -> dict:
    sys.path.insert(0, HERE)
    from arc3_client import MockGame
    from arcshim import FrameData, GameState
    from prioragent import PriorAgent
    wins, steps_all = 0, []
    for seed in range(seeds):
        game = MockGame(seed)
        agent = PriorAgent(game_id=f"mock-{seed}")
        fr = FrameData.from_wire(game.frame())
        frames = [fr]
        steps = 0
        while steps < max_steps and not agent.is_done(frames, fr):
            act = agent.choose_action(frames, fr)
            if act.name == "RESET":
                wire = game.frame()
            elif act.name == "ACTION6":
                wire = game.act("ACTION6", act.data.get("x"), act.data.get("y"))
            else:
                wire = game.act(act.name)
            fr = FrameData.from_wire(wire)
            frames.append(fr)
            if len(frames) > 40: frames = frames[-40:]
            steps += 1
            if fr.state in (GameState.WIN, GameState.GAME_OVER): break
        wins += fr.state == GameState.WIN
        steps_all.append(steps)
    return {"agent": "PriorAgent", "wins": wins, "n": seeds,
            "mean_steps": round(sum(steps_all) / len(steps_all), 1)}


def get_key() -> str:
    k = os.environ.get("ARC_API_KEY", "")
    if not k:
        try: k = open(KEY_FILE, encoding="utf-8").read()
        except Exception: k = ""
    # the file may carry extra lines (a KGAT_ scorecard token, blank lines); the API key is
    # the UUID (verified: it authenticates, the KGAT_ token 401s). Never return embedded
    # whitespace — it makes an invalid HTTP header.
    toks = [t for t in k.replace("\r", " ").replace("\n", " ").split() if t]
    uuid = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    for t in toks:
        if uuid.match(t): return t
    return toks[0] if toks else ""


ORACLE_EXPECTED = {"ls20": 5}         # what the hand-written chain is known to reach (5/7 at 217 actions, Sep 2)
PLAY_PRESSES = "auto"                 # Sep 4: the shape decides — run until the slice covers the model's closure, capped at 3x the human baseline per level


def _run(cmd: list, key: str, timeout: int = 1800) -> str:
    env = dict(os.environ, ARC_API_KEY=key)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=HERE,
                       creationflags=(0x08000000 if os.name == "nt" else 0))
    return (r.stdout or "") + (r.stderr or "")


def run_live(key: str) -> list:
    """The live try (Sep 4): THE GENERAL AGENT plays — play.py, the eye plus the induced operators, the
    planner, the touch-graph experiments, the register budget and the planned resets. On Sep 4 it cleared
    ls20 level 1 on its own (press 115, zero deaths), the first ls20 level not won by the hand-written chain.
    The chain (ls20_chain.py) still runs after it as the ORACLE: a regression test of the live game and the
    API, expected 5/7; it is recorded on its own line and never counts as the daily's score."""
    rows = []
    for g in LIVE_GAMES:
        try:
            out = _run([sys.executable, os.path.join(HERE, "play.py"), g, "--presses", str(PLAY_PRESSES)], key)
            done = re.search(r"done: levels (\d+) presses (\d+)", out)
            comp = re.findall(r">>> LEVEL (\d+) at press (\d+)", out)
            wm = re.search(r"world model: (.*)", out); seg = re.search(r"segments: (.*)", out); ex = re.search(r"experiments: (.*)", out)
            deaths = re.search(r"deaths (\d+), voluntary resets (\d+)", out)
            row = {"game": g, "player": "play.py", "levels": int(done.group(1)) if done else None,
                   "presses": int(done.group(2)) if done else None,
                   "completions": [{"level": int(a), "press": int(b)} for a, b in comp],
                   "deaths": int(deaths.group(1)) if deaths else None, "resets": int(deaths.group(2)) if deaths else None,
                   "world_model": wm.group(1).strip()[:300] if wm else None,
                   "segments": seg.group(1).strip()[:200] if seg else None,
                   "experiments": ex.group(1).strip()[:300] if ex else None,
                   "final_state": "NOT_FINISHED" if done else None,
                   "tail": out.strip().splitlines()[-4:]}
            rows.append(row)
            try:                       # keep her place: the run's state goes to the ocean under the game's bubble
                import oncall
                oncall.place(f"game-{g}", {"levels": row["levels"], "completions": row["completions"],
                                           "frames": os.path.join(OUT_EYE, f"play_{g.split('-')[0]}.npz"),
                                           "trans": None, "played_by": "play.py"},
                             f"resume {g} at level {(row['levels'] or 0) + 1}; play.py frames saved")
            except Exception: pass
        except Exception as e:
            rows.append({"game": g, "player": "play.py", "error": str(e)[:200]})
        # THE ORACLE: the hand-written chain, run for the regression check only
        chain = os.path.join(HERE, "ls20_chain.py")
        if g.startswith("ls20") and os.path.exists(chain):
            try:
                out = _run([sys.executable, chain], key)
                lv = re.findall(r"levels=(\d+)", out)
                comp = re.findall(r">>> LEVEL (\d+) COMPLETE at action (\d+)", out)
                levels = int(lv[-1]) if lv else None
                rows.append({"game": g, "player": "oracle:ls20_chain.py", "levels": levels,
                             "completions": [{"level": int(a), "actions": int(b)} for a, b in comp],
                             "expected": ORACLE_EXPECTED["ls20"],
                             "regressed": (levels is None or levels < ORACLE_EXPECTED["ls20"]),
                             "tail": out.strip().splitlines()[-3:]})
            except Exception as e:
                rows.append({"game": g, "player": "oracle:ls20_chain.py", "error": str(e)[:200], "regressed": True})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--practice-only", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    hist_p = os.path.join(OUT, "history.jsonl")
    hist = []
    try:
        hist = [json.loads(l) for l in open(hist_p, encoding="utf-8") if l.strip()]
    except Exception: pass
    practice = run_practice()
    # the baseline is the best earlier run OF THE SAME PRACTICE (mock wins and operator counts must not be compared)
    from evaluation_batch import practice_verdict
    baseline, verdict = practice_verdict(practice, hist, REGRESS_MARGIN)

    live = None
    key = get_key()
    if not a.practice_only and verdict not in ("REGRESSED", "FAILED"):
        live = run_live(key) if key else "no-key (drop it in D:\\planet\\arc_key.txt to enable the live try)"
    elif verdict == "REGRESSED":
        live = "skipped — practice regressed; fix before spending a live scorecard"
    elif verdict == "FAILED":
        live = "skipped — practice failed; no valid evaluation result"

    # the moon accretes: this daily ritual IS the orbit — one layer per pass, and a fresh roll
    # of the mock surface so the 7 contacts' map keeps filling in (moon.py; the game is a moon:
    # too big to absorb into the planet, contacted only at the 7 controls, rolled to be known)
    moon_note = None
    try:                               # the sideways ring: how this run FELT, laid across contexts
        import torus
        tf = os.path.join(HERE, "arc3_trans.jsonl")
        if isinstance(live, list) and os.path.exists(tf):
            torus.lay(tf, LIVE_GAMES[0])
            try:
                import pool
                pr = pool.feed_run(tf); print("pool (run):", pool.line(pr["bins"]))
            except Exception: pass
    except Exception:
        pass
    try:
        import moon
        # roll the REAL game surface if a live run just left its transition log (the true body);
        # else fall back to the mock roll. The live 0 proved the mock and the real game differ.
        real_trans = os.path.join(HERE, "arc3_trans.jsonl")
        if isinstance(live, list) and os.path.exists(real_trans):
            rr = moon.roll_real(LIVE_GAMES[0], real_trans)
            kind = "live-real"
        else:
            moon.roll_mocks(LIVE_GAMES[0]); kind = "practice"
        layer = moon.orbit(LIVE_GAMES[0], kind,
                           {"wins": practice["wins"], "n": practice["n"], "verdict": verdict,
                            "live": (live if isinstance(live, list) else None)})
        moon_note = {"layer": layer["n"], "rolled": layer["rolled"], "kind": kind}
    except Exception:
        pass

    row = {"t": time.time(), "date": time.strftime("%Y-%m-%d"), "practice": practice,
           "baseline_wins": baseline, "verdict": verdict, "live": live, "moon": moon_note}
    with open(hist_p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if practice.get("status") == "failed":
        pline = f"practice FAILED: {practice['error']} (not a score)"
    elif practice.get("agent") == "induce.py":
        pline = (f"practice (offline induction): {practice['wins']} gated operators in {practice.get('games_with_operators')} of {practice['n']} games, "
                 f"mean held-out acc best {practice.get('mean_best')} / gated {practice.get('mean_strict')} (baseline {baseline}) -> {verdict}")
    else:
        pline = f"practice: {practice['wins']}/{practice['n']} wins (baseline {baseline}), mean steps {practice['mean_steps']} -> {verdict}"
    rep = [f"ARC daily — {row['date']}", pline]
    if isinstance(live, list):
        for r in live:
            if r.get("player", "").startswith("oracle"):
                rep.append(f"oracle ({r['game']}, {r['player'][7:]}): levels {r.get('levels')} expected {r.get('expected')}"
                           f"{' REGRESSED' if r.get('regressed') else ' ok'}" + (f"; error {r['error']}" if r.get("error") else ""))
            else:
                rep.append(f"live ({r['game']}, {r.get('player')}): levels {r.get('levels')} in {r.get('presses')} presses, "
                           f"completions {r.get('completions')}, deaths {r.get('deaths')}, resets {r.get('resets')}"
                           + (f"; error {r['error']}" if r.get("error") else ""))
                if r.get("experiments"): rep.append(f"  experiments: {r['experiments'][:200]}")
    else:
        rep.append(f"live: {json.dumps(live, ensure_ascii=False)[:400]}")
    rep.append(f"moon: {json.dumps(moon_note) if moon_note else 'no accretion this orbit'}")
    rp = os.path.join(OUT, f"report_{time.strftime('%Y%m%d')}.txt")
    open(rp, "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
