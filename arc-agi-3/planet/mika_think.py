#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mika_think.py - HER DECISION LOOP WITH A MODEL AS THE MIDDLE SHELL (Oct 27 2026).

Jonathan, Oct 27: "our inner core was supposed to go inside the llm and have it wrap around us, it is supposed to be a
layer she can swap out. the llm was the middle shell and we have the inner one. she is supposed to make it work better or
more efficiently. she can use it but it should still be her deciding things."

The four roles of the old consciousness loop (Shovelcat-AI/lib/agents/consciousness-loop.ts, Mar 2026), updated with what
the ARC work found since (the core card, A=B=C, forge/review, +C bindings, the hybrid's token lesson):

  IMAGINATION  the only role the model plays. When she is stuck on a level she hands the shell her evidence in her own
               terms and asks for at most 3 claims: a thing to try, what it will do, and why. (The generated outer terms.)
  MEMORY       hers: her journal. Routes, recipes, relations, what every thing did in every life, claims that held.
  FACTS        hers, no model: every claim is checked against everything she has seen before it may become a press
               (forge: the thing must be on the screen, must not contradict 3+ tries that did nothing while nothing on the
               level changed, must not repeat a claim already tested). After the body tries it she checks the outcome
               against the prediction (review): held -> a proof she keeps; missed -> a question she keeps.
  PLANNER      hers: routes, recipes, detours, weighing (mika_mind) decide as before. A checked claim goes to the front of
               the frontier, after her own recipe steps.

The shell is called only when she is stuck (6 experiments on an uncleared level since she last asked, at most 3 calls per
level per life), so its thinking is spent where she cannot decide alone. It is swappable: --shell planet-voice (her own
LoRA voice, Qwen2.5-3B), --shell qwen2.5-coder:7b, or --shell none (the same mind with no shell, the baseline).

Every claim, check, outcome and shell call goes to D:\planet\mika\think\<game>_<stamp>.jsonl; every press is in the life
log as before. The shell's record (claims, held, missed, rejected) is kept per shell in her journal.

Usage:  python mika_think.py ls20 --presses 400 --shell planet-voice
        python mika_think.py sp80 --presses 300 --shell qwen2.5-coder:7b
        python mika_think.py --report ls20
"""
from __future__ import annotations
import argparse, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import mika_mind as mm

THINK = os.path.join(mm.HOME, "think")
STALL = 6                       # experiments on an uncleared level (this life) since she last asked, before she asks
CAP = 3                         # shell calls per level per life
MAXC = 3                        # claims per call
EXPECTS = {"changed", "refill", "level", "pass"}
EFFECTS = set(mm.EFFECT)        # changed, refill, level
RELCAP = 2                      # cycles of the body's carried relation loop she allows per life on an uncleared level
NOTRIED = {"unreachable", "untestable"}   # results that say the body never got to try the thing
EXPIRE = 6                     # experiments on the level after a claim was accepted; a claim the body has not tried by then
                                # lapses (run 2: open@35,34 dropped out of the frontier and blocked every later call)

SHELL_SYSTEM = """You are the imagination of Mika, a small mind learning a video game that has no instructions.
Mika's body walks to things on the screen and tries the buttons there or bumps into them. Each try ends with a result:
pass (walked through), wall (blocked), nothing (touched, nothing changed), changed (the board changed), refill (a bar refilled),
level (the level was won), unreachable, untestable.
Mika decides; you only propose. Each proposal must name one thing id from the list you are given, say what you expect it
to do, and say why, using what won the earlier levels. Mika checks every proposal against everything she has seen before
her body tries it, so do not propose things that already did nothing many times unless you say what is different now.
Answer only with JSON."""


def _now(): return time.strftime("%Y-%m-%d %H:%M:%S")


def _parse_claims(text):
    """The shell's answer -> list of claim dicts. Whole-JSON first; if the shell broke the JSON (sp80 run 5: a missing
    comma), each {...} that names a "try" is read on its own, so one bad claim does not lose the others."""
    try:
        out = json.loads(text)
        raw = out.get("claims") if isinstance(out, dict) else None
        if isinstance(raw, list): return raw, None
        return ([out] if isinstance(out, dict) and out.get("try") else []), None
    except Exception as e_:
        bad = str(e_)
    raw = []
    for m_ in re.finditer(r"\{[^{}]*\"try\"[^{}]*\}", text, re.S):
        try: raw.append(json.loads(m_.group(0)))
        except Exception:
            t_ = re.search(r"\"try\"\s*:\s*\"([^\"]+)\"", m_.group(0)); e2 = re.search(r"\"expect\"\s*:\s*\"([^\"]+)\"", m_.group(0))
            b_ = re.search(r"\"because\"\s*:\s*\"([^\"]*)", m_.group(0))
            if t_: raw.append({"try": t_.group(1), "expect": e2.group(1) if e2 else "", "because": b_.group(1) if b_ else ""})
    return raw, bad


class ThinkingMind(mm.MikaMind):
    shell = None                                   # set by main(); None = no shell (baseline)
    tlog_path = None

    def __init__(s, journal, log=print, mode="push"):
        super().__init__(journal, log=log, mode=mode)
        s.game = journal.get("game", "?")
        s.exp_since = {}; s.calls = {}; s.active = {}; s.tested = set(); s.life_res = {}
        s.j.setdefault("claims", []); s.j.setdefault("shells", {})
        s.held_before = [c for c in s.j["claims"] if c.get("outcome") == "held"]

    # ------------------------------------------------------------------------------------------- logging
    def _t(s, kind, **kw):
        if not s.tlog_path: return
        try:
            with open(s.tlog_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": _now(), "kind": kind, **kw}, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _stat(s, key, n=1):
        if not s.shell: return
        st = s.j["shells"].setdefault(s.shell, {"calls": 0, "claims": 0, "rejected": 0, "tried": 0, "held": 0, "missed": 0,
                                                "untried": 0, "seconds": 0.0, "tokens": 0})
        st[key] = st.get(key, 0) + n

    # ------------------------------------------------------------------------------------------- the body's hooks
    def observe(s, e):
        super().observe(e)
        lv = int(e.get("level", -1)); tid = str(e.get("id")); res = e.get("result")
        s.exp_since[lv] = s.exp_since.get(lv, 0) + 1
        s.exp_all = getattr(s, "exp_all", {}); s.exp_all[lv] = s.exp_all.get(lv, 0) + 1
        s.life_res.setdefault(lv, {}).setdefault(tid, []).append(res)
        c = s.active.get(lv, {}).pop(tid, None)
        s._lapse(lv)
        if c is None: return
        # REVIEW: the prediction against what the body saw
        exp = c["expect"]
        if res in NOTRIED:
            # the body never got to try it (run 3: five claims "missed" on unreachable) - no proof, no question
            c.update(outcome="untried", result=res, reviewed=_now()); s._stat("untried")
            s.j["claims"].append({k: c[k] for k in ("level", "try", "expect", "because", "shell", "outcome", "result", "made", "reviewed")})
            s.j["claims"] = s.j["claims"][-200:]
            s._t("review", level=lv, claim=c["try"], expect=exp, result=res, outcome="untried", shell=c["shell"])
            s.log(f"  think: level {lv + 1}: claim {c['try']} could not be tried ({res})")
            return
        held = (res == exp) or (exp in ("changed", "refill") and res in EFFECTS)
        c.update(outcome="held" if held else "missed", result=res, reviewed=_now())
        s._stat("held" if held else "missed"); s._stat("tried")
        s.j["claims"].append({k: c[k] for k in ("level", "try", "expect", "because", "shell", "outcome", "result", "made", "reviewed")})
        s.j["claims"] = s.j["claims"][-200:]
        if not held:
            q = f"Level {lv + 1}: {c['try']} was expected to give '{exp}' ({c['because']}) but gave '{res}'. What is different?"
            s.j.setdefault("questions", []).append(q[:300]); s.j["questions"] = s.j["questions"][-20:]
        s._t("review", level=lv, claim=c["try"], expect=exp, result=res, outcome=c["outcome"], shell=c["shell"])
        s.log(f"  think: level {lv + 1}: claim {c['try']} expected {exp}, the body saw {res} -> {c['outcome'].upper()}")

    def _lapse(s, lv):
        """A claim the body has not tried within EXPIRE experiments on its level lapses (it left the frontier or the body
        kept choosing other things); it is recorded as untried, not as a proof or a question, and she may ask again."""
        act = s.active.get(lv) or {}
        now = getattr(s, "exp_all", {}).get(lv, 0)
        for tid in [t for t, c in act.items() if now - c.get("at", now) >= EXPIRE]:
            c = act.pop(tid)
            c.update(outcome="untried", result=None, reviewed=_now()); s._stat("untried")
            s.j["claims"].append({k: c[k] for k in ("level", "try", "expect", "because", "shell", "outcome", "result", "made", "reviewed")})
            s.j["claims"] = s.j["claims"][-200:]
            s._t("lapse", level=lv, claim=tid, expect=c["expect"], after=EXPIRE, shell=c["shell"])
            s.log(f"  think: level {lv + 1}: claim {tid} lapsed - the body did not reach it in {EXPIRE} experiments")

    def order(s, goals, lvl, f):
        lvl = int(lvl)
        try: s._maybe_think(goals, lvl, f)
        except Exception as e_: s.log(f"  think: failed ({str(e_)[:120]})"); s._t("error", where="think", error=str(e_)[:300])
        new = super().order(goals, lvl, f)
        act = s.active.get(lvl, {})
        if not act or (lvl in s.routes and lvl not in s.route_off): return new
        # PLANNER: checked claims go to the front of the frontier, after her own recipe steps and cleared-level effects
        lead = [g for g in new if s.band(lvl, str(g["id"])) < 0]
        mine = [g for g in new if str(g["id"]) in act and g not in lead]
        mine.sort(key=lambda g: act[str(g["id"])]["rank"])
        rest = [g for g in new if g not in lead and g not in mine]
        out = lead + mine + rest
        if mine and (not new or str(out[0]["id"]) != str(new[0]["id"])):
            s.log(f"  think: level {lvl + 1}: her checked claim {mine[0]['id']} goes first (expects {act[str(mine[0]['id'])]['expect']})")
        return out

    def allow_relation(s, lvl, r, reset=False):
        """PLANNER over the body's relation loop. The body carries a 'touch X until the pattern matches Y' relation from the
        level before and restarts it after every reset (ls20 life 38: 6 cycles of 31 presses on level 3, every one ending in
        a budget reset). On a level she has never cleared she lets it run RELCAP cycles per life, then stops it, so the
        frontier (and her thinking) gets the presses. Cleared levels and levels with a route are left to the body."""
        lvl = int(lvl)
        if lvl in s.cleared or lvl in s.routes: return True
        s.rel_cycles = getattr(s, "rel_cycles", {})
        if reset: s.rel_cycles[lvl] = s.rel_cycles.get(lvl, 0) + 1
        # A cycle is a loop that ran until a reset or a death took it. Starts are not cycles: v5 counted them, and on
        # ls20 lives 39-43 two starts whose source was out of reach ("waits for the next sleep") were enough to veto the
        # loop before it touched the rotator once (0 rotator changes in 5 lives, against 10-11 in every push life before).
        n = s.rel_cycles.get(lvl, 0)
        if n >= RELCAP:
            if not getattr(s, "rel_vetoed", set()) & {lvl}:
                s.rel_vetoed = getattr(s, "rel_vetoed", set()) | {lvl}
                s.log(f"  think: level {lvl + 1}: she stops the body's relation loop after {n} cycles this life - it has never cleared this level")
                s._t("veto", level=lvl, what="relation loop", cycles=n)
            return False
        return True

    # ------------------------------------------------------------------------------------------- imagination + facts
    def _maybe_think(s, goals, lvl, f):
        if not s.shell or not goals: return
        if lvl in s.cleared or (lvl in s.routes and lvl not in s.route_off): return     # she knows what to do here
        if s.active.get(lvl): return                                                    # claims still being tried
        if s.exp_since.get(lvl, 0) < STALL or s.calls.get(lvl, 0) >= CAP: return
        s.calls[lvl] = s.calls.get(lvl, 0) + 1; s.exp_since[lvl] = 0
        on_screen = {str(g["id"]): g for g in goals}
        prompt = s._evidence(goals, lvl, f)
        t0 = time.time()
        r = mm._post(mm.OLLAMA + "/api/chat", {"model": s.shell, "stream": False, "format": "json",
                                               "options": {"temperature": 0.4, "num_ctx": 8192, "num_predict": 400},
                                               "messages": [{"role": "system", "content": SHELL_SYSTEM},
                                                            {"role": "user", "content": prompt}]}, timeout=300)
        secs = round(time.time() - t0, 1); text = (r.get("message") or {}).get("content", "")
        toks = int(r.get("eval_count") or 0) + int(r.get("prompt_eval_count") or 0)
        s._stat("calls"); s._stat("seconds", secs); s._stat("tokens", toks)
        raw, bad = _parse_claims(text)
        if bad: s._t("error", where="parse", error=bad[:300], answer=text[:2000])
        s._t("call", level=lvl, shell=s.shell, call=s.calls[lvl], seconds=secs, prompt_tokens=r.get("prompt_eval_count"),
             gen_tokens=r.get("eval_count"), prompt=prompt, answer=text[:2000])
        s.log(f"  think: level {lvl + 1}: stuck - she asks {s.shell} (call {s.calls[lvl]}/{CAP}, {secs}s, {len(raw)} claim(s))")
        rank = 0
        for c in raw[:MAXC]:
            if not isinstance(c, dict): continue
            claim = {"level": lvl, "try": str(c.get("try", "")).strip(), "expect": str(c.get("expect", "")).strip().lower(),
                     "because": str(c.get("because", "")).strip()[:240], "shell": s.shell, "made": _now()}
            s._stat("claims")
            why = s._check(claim, lvl, on_screen)
            if why:
                s._stat("rejected"); s._t("check", level=lvl, claim=claim["try"], expect=claim["expect"], because=claim["because"], verdict="rejected", why=why)
                s.log(f"  think: level {lvl + 1}: she rejects {claim['try'] or '?'} -> {claim['expect'] or '?'} ({why})")
                continue
            claim["rank"] = rank; rank += 1; claim["at"] = getattr(s, "exp_all", {}).get(lvl, 0)
            s.active.setdefault(lvl, {})[claim["try"]] = claim; s.tested.add((lvl, claim["try"]))
            s._t("check", level=lvl, claim=claim["try"], expect=claim["expect"], because=claim["because"], verdict="accepted")
            s.log(f"  think: level {lvl + 1}: she accepts {claim['try']} -> {claim['expect']} ({claim['because'][:120]})")

    def _check(s, c, lvl, on_screen):
        """FACTS (forge): the claim against everything she has seen. Returns the reason to reject, or None."""
        tid = c["try"]
        if not tid: return "names no thing"
        if tid not in on_screen: return "not on the screen now"
        if c["expect"] not in EXPECTS: return f"expects '{c['expect']}', which the body cannot see"
        if (lvl, tid) in s.tested: return "already tested this life"
        past = list(s.results.get(lvl, {}).get(tid, [])) + list(s.life_res.get(lvl, {}).get(tid, []))
        dead = [x for x in past if x in mm.DEAD]
        if c["expect"] in EFFECTS and len(past) >= 3 and len(dead) == len(past) and s.built.get(lvl, 0) == 0:
            return f"it did nothing in all {len(past)} tries and nothing on this level has changed since the last reset"
        if c["expect"] == "pass" and past and all(x == "wall" for x in past): return f"it was a wall in all {len(past)} tries"
        return None

    # ------------------------------------------------------------------------------------------- her evidence, her terms
    def _won_how(s, lv):
        r = s.recipes.get(lv)
        if not r: return None
        steps = []
        for t in r:
            res = [x for x in s.results.get(lv, {}).get(t, []) if x in EFFECTS]
            kind = "refill" if (lv, t) in s.refill_ids else (res[-1] if res else "changed")
            steps.append(f"{t} ({kind})")
        return " -> ".join(steps)

    def _evidence(s, goals, lvl, f):
        L = [f"Game {s.game}. Mika is on level {lvl + 1}. Levels she has won in earlier lives: "
             f"{', '.join(str(c + 1) for c in sorted(s.cleared)) or 'none'}."]
        won = []
        for lv in sorted(set(s.recipes) | set(s.routes)):
            h = s._won_how(lv)
            if h: won.append(f"- level {lv + 1} was won by doing, in order: {h}")
            elif lv in s.routes: won.append(f"- level {lv + 1}: she has a {len(s.routes[lv])}-press route through it")
        if won: L += ["", "How the earlier levels were won:"] + won
        rels, seen_r = [], set()                       # run 2's prompt listed the same relation 4 times
        for r_ in reversed(s.rel_mem + s.rel_new):
            k_ = (r_.get("src_colour"), r_.get("colour"), str(r_.get("target_colours")))
            if k_ not in seen_r: seen_r.add(k_); rels.insert(0, r_)
        rels = rels[-4:]
        if rels:
            L += ["", "Relations her body learned (touch one thing until a shown pattern matches another):"]
            L += [f"- on level {int(r_['learned_on']) + 1}: touching colour {r_['src_colour']} changes the pattern shown in colour "
                  f"{r_['colour']} until it matches colour {r_['target_colours']}" for r_ in rels]
        held = [c for c in s.held_before if c.get("level") == lvl][-4:]
        if held: L += ["", "Proposals that held on this level before:"] + [f"- {c['try']} gave {c['result']} ({c['because']})" for c in held]
        missed = [c for c in s.j["claims"] if c.get("level") == lvl and c.get("outcome") == "missed"][-4:]
        if missed: L += ["", "Proposals that did not hold on this level:"] + [f"- {c['try']} was expected to give {c['expect']} but gave {c['result']}" for c in missed]
        unt = [c for c in s.j["claims"] if c.get("level") == lvl and c.get("outcome") == "untried" and c.get("result")][-4:]
        if unt: L += ["", "Proposals the body could not get to (out of moves or no path):"] + [f"- {c['try']} ({c['result']})" for c in unt]
        L += ["", f"Things on the screen now on level {lvl + 1} (colour, size, box rows/cols) and what each did in all lives so far:"]
        # things before openings: run 2's first prompt was 28 openings and never showed the rotator, the rings or the changers
        objs = [g for g in goals if not str(g["id"]).startswith("open@")]
        opens = [g for g in goals if str(g["id"]).startswith("open@")]
        for g in (objs + opens)[:28]:
            d = mm.describe(g, f); tid = str(g["id"])
            past = list(s.results.get(lvl, {}).get(tid, [])) + list(s.life_res.get(lvl, {}).get(tid, []))
            desc = f"- {tid}"
            if "colour" in d: desc += f": colour {d['colour']}, {d['n']} cells, rows {d['box'][0]}-{d['box'][2]}, cols {d['box'][1]}-{d['box'][3]}"
            if past:
                cnt = {}
                for x in past: cnt[x] = cnt.get(x, 0) + 1
                desc += "; results: " + ", ".join(f"{k} x{v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]))
            else: desc += "; never tried"
            L.append(desc)
        ex = str((opens or goals)[min(1, len(opens or goals) - 1)]["id"])
        L += ["", f"Propose up to {MAXC} things for the body to try next on this level, best first.",
              "\"try\" must be one thing id copied exactly from the list above.",
              "\"expect\" must be exactly one word: changed, refill, level or pass.",
              "\"because\" must name the evidence above that makes you expect it (a result count, a relation, how a level was won).",
              "Example of the format only (not advice; write your own reason):",
              '{"claims": [{"try": "' + ex + '", "expect": "pass", "because": "<your reason from the evidence>"}]}']
        # runs 3 and 7: coder copied the old example's reason (near) word for word, and both shells picked openings over
        # things that had changed the board 80 times; the example now carries no reason and no effect to copy
        return "\n".join(L)


def report(game):
    j = mm.load_journal(game)
    print(f"{game}: {len(j.get('lives', []))} lives, best {j.get('best_levels', 0)}")
    for k, v in j.get("shells", {}).items(): print(f"  shell {k}: {v}")
    for c in j.get("claims", [])[-15:]:
        print(f"  L{c['level'] + 1} {c['try']} -> {c['expect']}: {c.get('outcome')} ({c.get('result')}) [{c.get('shell')}] {c.get('because', '')[:90]}")


def main():
    ap = argparse.ArgumentParser(description="Mika decides; a swappable model (the middle shell) proposes when she is stuck")
    ap.add_argument("game", nargs="?", default="ls20")
    ap.add_argument("--lives", type=int, default=1)
    ap.add_argument("--presses", default="400")
    ap.add_argument("--shell", default="planet-voice", help="an Ollama model name, or 'none' for the same mind without a shell")
    ap.add_argument("--no-reflect", action="store_true")
    ap.add_argument("--mode", default="push", choices=["push", "study"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report: report(a.game); return
    os.makedirs(THINK, exist_ok=True)
    ThinkingMind.shell = None if a.shell.lower() == "none" else a.shell
    ThinkingMind.tlog_path = os.path.join(THINK, f"{a.game}_{time.strftime('%Y%m%d_%H%M%S')}_{a.shell.replace(':', '-')}.jsonl")
    mm.MikaMind = ThinkingMind                       # mika_mind.live builds her mind through this name
    presses = 0 if str(a.presses).lower() == "auto" else int(a.presses)
    rows = mm.live(a.game, presses, a.lives, not a.no_reflect, None if ThinkingMind.shell is None else ThinkingMind.shell,
                   None, a.seed, mode=a.mode)
    print(f"think log: {ThinkingMind.tlog_path}")
    report(a.game)


if __name__ == "__main__":
    main()
