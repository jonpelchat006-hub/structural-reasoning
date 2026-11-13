"""mika_bridge.py - Mika's full inner core on any game an arc_agi environment serves (Oct 30 2026).

Her body (play.py) and her core (mika_core.CoreMind) talk to the game through one function, api(path, key, body), the
live ARC-AGI-3 REST API. This bridge answers those calls from an environment object instead (the offline engine on the
bench, or the competition runner's environment on Kaggle), so play.py and her core run unchanged: no rules are added,
only the wire is swapped.

    run_game(env_step, game_id, presses, lives, log)   env_step(GameAction, data) -> FrameDataRaw (or FrameData)

Everything she writes (journals, saved lives, logs) goes to a fresh folder per game under MIKA_TMP (default /tmp), so a
hidden game starts with a blank journal, and her own journals on the PC are never touched.
"""
from __future__ import annotations
import os, sys, time, json, tempfile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _state_name(s):
    n = getattr(s, "name", None) or getattr(s, "value", None) or str(s)
    return str(n).split(".")[-1]


def _frame_lists(raw):
    fr = getattr(raw, "frame", None)
    out = []
    for a in (fr or []):
        out.append(a.tolist() if hasattr(a, "tolist") else a)
    return out


def make_transport(env_step, counter=None):
    """api(path, key, body) answered by env_step(GameAction, data)."""
    from arcengine import GameAction
    last = {"frame": None}

    def api(path, key=None, body=None, method=None):
        if path.endswith("/scorecard/open"):
            return {"card_id": "bridge"}
        if path.endswith("/scorecard/close"):
            return {}
        if "/api/cmd/" in path:
            name = path.rsplit("/", 1)[1]
            act = GameAction.RESET if name == "RESET" else GameAction.from_name(name)
            data = {}
            if body and body.get("x") is not None:
                data = {"x": int(body["x"]), "y": int(body["y"])}
            raw = env_step(act, data)
            if raw is None:
                raise RuntimeError(f"environment returned nothing for {name}")
            if counter is not None:
                counter["n"] = counter.get("n", 0) + 1
            fr = _frame_lists(raw) or ([last["frame"]] if last["frame"] is not None else [])
            if fr:
                last["frame"] = fr[-1]
            return {"guid": getattr(raw, "guid", None) or "bridge", "frame": fr, "state": _state_name(raw.state),
                    "levels_completed": int(raw.levels_completed or 0), "win_levels": int(raw.win_levels or 0),
                    "available_actions": [int(a) for a in (raw.available_actions or [])], "score": int(raw.levels_completed or 0)}
        if path.endswith("/api/games"):
            return []
        raise RuntimeError(f"bridge: unsupported call {path}")
    return api


def _fresh_home(game):
    """point every place her modules write to at a fresh folder for this game"""
    import mika_mind as mm, mika_think as mt, mika_core as mc, play
    root = tempfile.mkdtemp(prefix=f"mika_{game}_", dir=os.environ.get("MIKA_TMP") or None)
    mm.HOME = os.path.join(root, "mika")
    mt.THINK = os.path.join(mm.HOME, "think")
    mc.CORE = os.path.join(mm.HOME, "core")
    mc.EYE = os.path.join(root, "eye")
    play.OUT = os.path.join(root, "eye")
    for d in (mm.HOME, mt.THINK, mc.CORE, play.OUT):
        os.makedirs(d, exist_ok=True)
    try:
        import mika_tree
        mika_tree.ROOT = os.path.join(mm.HOME, "tree")
    except Exception:
        pass
    return root


def _eye_scale():
    """MIKA_EYE_SCALE < 1 trains her eye less per press (only for CPU-only test benches; on a GPU it stays 1)"""
    import play
    sc = float(os.environ.get("MIKA_EYE_SCALE", "1") or 1)
    if sc >= 1 or getattr(play.Player, "_scaled", False):
        return
    orig = play.Player.learn
    def learn(s, steps, bs=16):
        return orig(s, max(1, int(round(steps * sc))), bs)
    play.Player.learn = learn
    play.Player._scaled = True


PHI = (1 + 5 ** 0.5) / 2                       # the most irrational number: worst approximated by any fraction
PLASTIC = 1.324717957244746                     # its two-dimensional cousin: the plastic number (the R2 point sequence)


def _irrational():
    """THE MOST IRRATIONAL MOVE (Jonathan, Oct 30: "follow the theory and try the most irrational thing at the end").
    When she is stuck - the eye's best candidate was already tried twice from this very screen - she does not repeat it.
    She walks her candidates in golden-ratio order (each step a golden fraction of the list away from the last, so no
    rhythm ever repeats) and takes the first one never tried from here. When every candidate was tried and clicks are
    open, she clicks the next point of the plastic-number sequence, the most evenly spread points a square can hold.
    Switched on by MIKA_IRRATIONAL=1; her body and core are otherwise unchanged."""
    import play
    if os.environ.get("MIKA_IRRATIONAL", "0") != "1" or getattr(play.Player, "_irr", False):
        return
    orig = play.Player.choose

    def choose(s, f, cands, rise=None, approach=None, h=None, tick=None, ops=None):
        c, pred, why = orig(s, f, cands, rise, approach, h, tick, ops)
        try:
            key = s._key(f, tick)
            if s.tried.get((key, c), 0) < 2 or not cands:
                return c, pred, why
            s._irr_m = getattr(s, "_irr_m", 0) + 1
            m = s._irr_m; n = len(cands)
            pick = None
            i0 = int(((m * PHI) % 1.0) * n)
            step = max(1, int(round(n / PHI)))
            for j in range(n):
                cand = cands[(i0 + j * step) % n]
                if s.tried.get((key, cand), 0) == 0:
                    pick = cand; break
            if pick is None and any(cc[0] == 6 for cc in cands):
                x = int(((0.5 + m / PLASTIC) % 1.0) * f.shape[1]); y = int(((0.5 + m / PLASTIC ** 2) % 1.0) * f.shape[0])
                pick = (6, x, y)
            if pick is None:
                pick = cands[i0 % n]
            try:
                pred2 = s.imagine(f, [pick], h)[0][0]
            except Exception:
                pred2 = None
            return pick, pred2, "irrational eye"
        except Exception:
            return c, pred, why
    play.Player.choose = choose
    play.Player._irr = True


def run_game(env_step, game_id, presses=400, lives=1, log=None, shell=None, seed=0, device=None, mode="push"):
    """Play one game with her body and core; several lives share her journal (she learns between them).
    Returns a list of per-life rows (levels, presses, stop reason, seconds)."""
    import mika_mind as mm, mika_think as mt, mika_core as mc, play
    game = game_id.split("-")[0]
    _fresh_home(game)
    _eye_scale()
    _irrational()
    try:
        import mika_voice4; mika_voice4.install()                 # MIKA_VOICE4=1: a better job for her voice
    except Exception as e_:
        (log or (lambda s: None))(f"bridge: voice4 not installed ({str(e_)[:160]})")
    logf = log or (lambda s: None)
    try:
        import mika_voice5; mika_voice5.install(); logf = mika_voice5.tap(logf)   # MIKA_VOICE5=1: she briefs her voice first
        import mika_prism; mika_prism.install()                  # MIKA_PRISM=1: the tube and the prism
    except Exception as e_:
        logf(f"bridge: voice5 not installed ({str(e_)[:160]})")
    mt.ThinkingMind.shell = shell
    mt.ThinkingMind.tlog_path = os.environ.get("MIKA_THINK_LOG") or None   # every question, answer and result, kept
    mm.MikaMind = mc.CoreMind
    counter = {"n": 0}
    api = make_transport(env_step, counter)
    rows = []
    for k in range(lives):
        j = mm.load_journal(game)
        mind = mc.CoreMind(j, log=logf, mode=mode)
        mind.life_k = k
        t0 = time.time()
        try:
            row = play.play_game(game_id, "", presses, device, log=logf, mind=mind, seed=seed, transport=api,
                                 output_dir=play.OUT)
        except Exception as e:
            logf("bridge: life failed: " + "".join(traceback.format_exception(type(e), e, e.__traceback__))[-1500:])
            row = {"levels": None, "presses": None, "stop": "error: " + str(e)[:200]}
        life = {"levels": int(row.get("levels") or 0), "presses": row.get("presses"), "stop": row.get("stop"),
                "seconds": round(time.time() - t0, 1), "deaths": row.get("deaths"), "level_presses": row.get("level_presses"),
                "voluntary_resets": row.get("voluntary_resets")}
        rows.append(life)
        try:                                            # what a life leaves in her journal, as mika_mind.live() does it
            j["lives"].append(dict(life, t=time.time(), gid=game_id, mode=mode,
                                   experiments=[{k_: e.get(k_) for k_ in ("id", "result", "presses", "level", "rel", "open")
                                                 if e.get(k_) is not None} for e in row.get("experiments", []) or []],
                                   mind_moves=getattr(mind, "moves", [])))
            j["cleared"] = sorted(set(j.get("cleared", [])) | set(range(life["levels"])))
            j["best_levels"] = max(j.get("best_levels", 0), life["levels"])
            rec_path = os.path.join(play.OUT, f"play_{game}.jsonl")
            rec_rows = []
            if os.path.exists(rec_path):
                with open(rec_path, encoding="utf-8") as fh:
                    rec_rows = [json.loads(l) for l in fh if l.strip()]
            mm.learn_routes(j, rec_rows, len(j["lives"]), logf)
            m = mind                                    # this life's mind (CoreMind.last is shared by every game in a process)
            if m is not None:
                m.finish()
                for key_ in ("notes", "core_nodes", "core_book", "core_moves", "core_looks", "metal_notes", "core_tracks"):
                    if key_ in m.j:
                        j[key_] = m.j[key_]
            stuck = j["lives"][-1]["levels"]
            for lv, seen in getattr(mind, "seen", {}).items():
                j.setdefault("things", {}).setdefault(str(lv), {}).update(seen)
            if shell and k + 1 < lives:                 # her reflection between lives, in her own voice
                try:
                    things = list(getattr(mind, "seen", {}).get(stuck, {}).values())
                    refl = mm.reflect(j, j["lives"][-1], stuck, things, shell, logf)
                    j.setdefault("picks", {})[str(stuck)] = refl.get("try_first", [])
                    j["facts"] = (j.get("facts", []) + [f for f in refl.get("facts", []) if f not in j.get("facts", [])])[-30:]
                    j["questions"] = (j.get("questions", []) + [q for q in refl.get("questions", []) if q not in j.get("questions", [])])[-20:]
                    j["lives"][-1]["reflection"] = refl
                    logf(f"bridge: reflection after life {k + 1}: picks {refl.get('try_first')}")
                except Exception as e:
                    logf(f"bridge: reflection failed ({str(e)[:160]})")
            mm.save_journal(j)
        except Exception as e:
            logf(f"bridge: journal not saved after life {k + 1} ({str(e)[:160]})")
    rows.append({"actions": counter["n"]})
    return rows


# ---------------------------------------------------------------- one game in its own process (Kaggle: real parallelism)
class _Raw:
    """the frame a remote step returns, with the attributes make_transport reads"""
    def __init__(self, d):
        self.frame = d.get("frame") or []
        self.state = d.get("state") or "NOT_FINISHED"
        self.levels_completed = d.get("levels_completed") or 0
        self.win_levels = d.get("win_levels") or 0
        self.available_actions = d.get("available_actions") or []
        self.guid = d.get("guid")


def raw_to_dict(raw):
    """what crosses the pipe: plain lists and ints"""
    return {"frame": _frame_lists(raw), "state": _state_name(raw.state), "levels_completed": int(raw.levels_completed or 0),
            "win_levels": int(raw.win_levels or 0), "available_actions": [int(a) for a in (raw.available_actions or [])],
            "guid": getattr(raw, "guid", None)}


def worker_main(conn, game_id, presses, lives, log_path, env):
    """child process: her body and core play game_id; every press is a request over conn ("step", name, data) that the
    parent performs on the real environment and answers with raw_to_dict(frame), or None to stop"""
    os.environ.update({k: str(v) for k, v in (env or {}).items()})
    if log_path and os.environ.get("MIKA_VOICE4", "0") == "1":
        os.environ["MIKA_THINK_LOG"] = os.path.splitext(log_path)[0] + "_think.jsonl"
    lf = open(log_path, "a", encoding="utf-8") if log_path else None

    def log(s):
        if lf:
            try:
                lf.write(str(s) + "\n"); lf.flush()
            except Exception:
                pass
    from arcengine import GameAction  # noqa: F401

    def env_step(act, data):
        conn.send(("step", act.name, data or {}))
        d = conn.recv()
        if d is None:
            raise SystemExit("stopped by the parent")
        return _Raw(d)
    rows = None
    try:
        rows = run_game(env_step, game_id, presses=presses, lives=lives, log=log, shell=(os.environ.get("MIKA_SHELL") or None))
        log(f"MIKA DONE {game_id}: {rows}")
    except SystemExit as e:
        log(f"MIKA STOPPED {game_id}: {e}")
    except Exception as e:
        log("MIKA ERROR " + "".join(traceback.format_exception(type(e), e, e.__traceback__))[-3000:])
    try:
        conn.send(("done", rows, None))
    except Exception:
        pass
    if lf:
        lf.close()


def play_in_process(env_step, game_id, presses, lives, log_path=None, env=None, deadline=None):
    """parent side: run worker_main in a spawned process and perform its presses with env_step"""
    import multiprocessing as mp
    from arcengine import GameAction
    ctx = mp.get_context("spawn")
    a, b = ctx.Pipe()
    p = ctx.Process(target=worker_main, args=(b, game_id, presses, lives, log_path, env), daemon=True)
    p.start()
    rows = None
    try:
        while True:
            if not a.poll(600):                          # ten minutes without a request: the child is stuck
                break
            try:
                msg = a.recv()
            except EOFError:
                break
            if msg[0] == "done":
                rows = msg[1]; break
            if deadline is not None and time.time() > deadline:
                a.send(None); continue
            try:
                raw = env_step(GameAction.from_name(msg[1]), msg[2])
                a.send(raw_to_dict(raw) if raw is not None else None)
            except Exception:
                a.send(None)
    finally:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    return rows
