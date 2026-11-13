#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mika_mind.py - MIKA AS THE ONE WHO PLAYS. The planet player (play.py) is her body and reflexes;
she is the mind that carries what each life taught her into the next one.

Jonathan, Oct 13 2026: "i think we can make Mika an actual agent with all our work."
Home Mika first, built on our planet code.

One LIFE = one play.play_game run. Around it:

  BEFORE  she reads her journal for the game (D:\planet\mika\<game>.json): which levels she has
          cleared, what every experiment did in every earlier life, her own picks and questions.

  DURING  play.py asks her (mind.order) each time it is about to pick the next experiment.
          On a level she has CLEARED before she walks the route that cleared it (the shortest any life
          found), press for press from the level's start; if it breaks she drops it and steers instead:
          On any other level (never cleared, or cleared once with no working route) she re-orders the candidates into bands
          (untrusted until played: a new thing outranks her pick of an old one):
            0  her own picks from the last reflection that were never tried
            1  things never tried in any life
            2  her own picks that were tried before
            3  things tried before that did something (pass / changed / refill)
            4  things tried before that did nothing (wall / nothing / unreachable / untestable)
          Nothing is added or removed; inside each band the planet's own order stands.

  AFTER   she reflects with a local model through Ollama (no internet, nothing leaves the PC):
          what happened, facts about the game, what to try first next life, open questions
          (void pins). That goes in the journal and her diary (D:\planet\mika\diary.md), and once
          per session into her companion memory through the bridge, so the Mika you chat with
          knows what she learned. If the model or the bridge is down she still keeps the journal.

Usage:  python mika_mind.py ls20 --lives 2 --presses 400
        python mika_mind.py sp80 --lives 2 --no-reflect     (journal-only mind, no model)
        python mika_mind.py --show ls20                      (print her journal for a game)
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

HOME = r"D:\planet\mika" if os.name == "nt" else "/tmp/mika"
OLLAMA = "http://127.0.0.1:11434"
BRIDGE = "http://127.0.0.1:41737"
MODELS = ["qwen2.5-coder:7b", "qwen2.5:3b", "gemma3:4b"]
DEAD = {"wall", "nothing", "unreachable", "untestable"}
LIVE = {"pass", "changed", "refill", "level"}
BAND = {-2: "the recipe that cleared it before", -1: "did something on a level that was cleared before",
        0: "her pick, never tried", 1: "never tried", 2: "her pick, tried before", 3: "did something before", 4: "did nothing before",
        5: "pruned: tried 3+ times, never did anything"}
def _xy(tid):
    """the place in a thing's id ('11@51,40' -> (51, 40)); None when it has none"""
    m_ = re.search(r"@(\d+),(\d+)", str(tid))
    return (int(m_.group(1)), int(m_.group(2))) if m_ else None


STUDY = 60                                              # presses a study life spends looking around a cleared level
NOOP = 3                                                # a press that changed this many cells or fewer changed nothing (the energy tick)
EFFECT = {"changed", "refill", "level"}                  # did something (an opening that just let her pass is not counted)


# ----------------------------------------------------------------------------------------- journal
def journal_path(game): return os.path.join(HOME, f"{game}.json")


def load_journal(game):
    try:
        with open(journal_path(game), encoding="utf-8") as fh: return json.load(fh)
    except Exception:
        return {"game": game, "lives": [], "cleared": [], "best_levels": 0, "things": {}, "picks": {},
                "facts": [], "questions": []}


def save_journal(j):
    os.makedirs(HOME, exist_ok=True)
    tmp = journal_path(j["game"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh: json.dump(j, fh, indent=1)
    os.replace(tmp, journal_path(j["game"]))


def describe(goal, f):
    """what a candidate thing looks like on the frame: size, box, colour (for her to read)"""
    d = {"id": str(goal["id"])}
    cells = goal.get("cells")
    try:
        cells = np.asarray(cells, bool)
        if cells.shape == f.shape and cells.any():
            ys, xs = np.nonzero(cells)
            vals = np.asarray(f)[cells]
            d.update(n=int(cells.sum()), box=[int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())],
                     colour=int(np.bincount(vals.astype(int) % 16).argmax()))
    except Exception:
        pass
    if goal.get("open") is not None: d["open"] = str(goal.get("open"))
    return d


# ----------------------------------------------------------------------------------------- the mind
class MikaMind:
    """passed to play.play_game(mind=...); play.py calls order() before every experiment pick"""

    def __init__(s, journal, log=print, mode="push"):
        s.j = journal; s.log = log; s.mode = mode
        s.cleared = set(int(c) for c in journal.get("cleared", []))
        s.results = {}                                   # level -> thing id -> [results from earlier lives]
        for life in journal.get("lives", []):
            for e in life.get("experiments", []):
                if "level" in e: s.results.setdefault(int(e["level"]), {}).setdefault(str(e["id"]), []).append(e.get("result"))
        s.picks = {int(k): list(v) for k, v in journal.get("picks", {}).items()}
        s.seen = {}                                      # level -> thing id -> description (this life)
        s.moves = []                                     # every time her order changed the body's next experiment
        s.deferred = set()
        s.routes = {int(k): [tuple(p) for p in v.get("presses", [])] for k, v in journal.get("routes", {}).items() if v.get("presses")}
        s.route_on = None; s.route_last = -1; s.route_off = set(); s.route_log = []
        # RECIPE MEMORY (Oct 16): for a level cleared with no press route, the experiments that did something on the way
        # to the clear, in order (the shortest such recipe over all lives)
        s.recipes = {}; s.refill_ids = set()
        for life in journal.get("lives", []):
            by = {}
            # SINCE THE LAST PUT-BACK (Oct 16 night): a reset undoes what was built, so the recipe that cleared a level is only
            # the stretch after the level's last reset. ls20 life 1 poked the key 8 times over 4 tries; the try that won had 3.
            cut = {}
            for lv_, i_ in life.get("resets_at", []): cut[int(lv_)] = max(cut.get(int(lv_), 0), int(i_))
            for i_, e in enumerate(life.get("experiments", [])):
                if "level" in e and i_ < cut.get(int(e["level"]), 0): continue
                if "level" in e and e.get("result") in EFFECT: by.setdefault(int(e["level"]), []).append(str(e["id"]))
                if "level" in e and e.get("result") == "refill": s.refill_ids.add((int(e["level"]), str(e["id"])))
            for lv, seq in by.items():
                if seq and lv < int(life.get("levels", 0)) and (lv not in s.recipes or len(seq) < len(s.recipes[lv])): s.recipes[lv] = seq
        doors_ = {(int(e["level"]), str(e["id"])) for life in journal.get("lives", []) for e in life.get("experiments", [])
                  if "level" in e and e.get("result") == "level"}
        s.refill_ids -= doors_                          # a thing that opened the level is a door, even if the new bar read as a refill
        s.rec_pos = {}; s.rec_fail = {}; s.recipe_off = set(); s.recipe_log = []; s.rec_said = set()
        s.rec_wait = {}; s.unreach = {}                 # a step the body could not reach yet: wait, then ask again
        s.n_exp = 0; s.resets_at = []                   # where in this life's experiment list each reset fell
        s.used_refills = set()                          # rings spent since the last reset
        s.rel_mem = list(journal.get("relations", [])); s.rel_new = []; s.rel_used = []; s.rel_level = set()
        s.goal_objs = {}; s.asked = {}                  # things seen this life, so she can ask the body to try one again
        # Oct 16 evening: weighing, detours, trimming, study lives, the surprise watch
        s.built = {}; s.energy = None; s.margin = None; s.last_since = 0; s.last_lvl = -1
        s.weigh_log = []; s.detours = []; s.trim_log = []; s.surprise_log = []; s.sur_run = 0
        s.studied = set(); s.study_n = {}; s.walking_trim = False; s.walking_len = 0
        s.trims = {}; s.trim_done = set()
        try:
            import mika_tree
            for lv, rt in s.routes.items():
                b_ = mika_tree._load(mika_tree._p(journal.get("game", "?"), f"L{lv + 1}.json"), {})
                strong = b_.get("cells", {}).get("route", {}).get("strength", 0) >= 2
                tr = [p for i, p in enumerate(rt) if i == len(rt) - 1 or len(p) < 4 or int(p[3]) > NOOP]
                if strong and len(tr) < len(rt) and len(tr) not in b_.get("data", {}).get("trim_failed", []): s.trims[lv] = tr
        except Exception:
            pass

    def observe(s, e):
        """play.py calls this with every experiment result as it happens"""
        lv = int(e.get("level", -1)); r = s.recipes.get(lv)
        s.n_exp += 1
        if lv in s.rel_level and e.get("rel") == "src" and e.get("result") == "changed":
            s.built[lv] = s.built.get(lv, 0) + 1          # the body's relation loop builds too: one more state since the reset
        if not r or lv in s.recipe_off or lv in s.routes: return
        pos = s.rec_pos.get(lv, 0)
        if pos >= len(r) or str(e.get("id")) != r[pos]: return
        if e.get("result") in EFFECT or (lv, r[pos]) in s.refill_ids:   # a refill step with a full bar is just skipped
            s.rec_pos[lv] = pos + 1; s.rec_fail[lv] = 0
            if e.get("result") in ("changed", "level"): s.built[lv] = s.built.get(lv, 0) + 1
            if e.get("result") == "refill":
                # the bar is full now and that ring is spent until the level is put back: no second detour on a stale reading
                # (ls20 life 17 walked back to the spent ring 11@51,40 for 6 presses and the far ring was out of reach after)
                s.energy = None; s.used_refills.add((lv, r[pos]))
            s.recipe_log.append({"level": lv, "step": pos + 1, "of": len(r), "id": r[pos], "result": e.get("result")})
            s.log(f"  mind: level {lv + 1}: recipe step {pos + 1}/{len(r)} {r[pos]} -> {e.get('result')}")
        elif e.get("result") in ("unreachable", "untestable"):
            # NOT A FAILURE OF THE STEP (Oct 16 night): the body could not get there with the moves it trusts so far on this
            # level (ls20 life 14: 'down' was not trusted yet 8 presses into level 2, so the key looked unreachable three
            # times and the recipe was dropped). She waits 10 presses while the body learns its moves, then asks again.
            s.unreach[lv] = s.unreach.get(lv, 0) + 1
            if s.unreach[lv] >= 6:
                s.recipe_off.add(lv); s.recipe_log.append({"level": lv, "step": pos + 1, "of": len(r), "id": r[pos], "result": "never reached"})
                s.log(f"  mind: level {lv + 1}: the body could not reach {r[pos]} 6 times - she steers without the recipe")
            else:
                s.rec_wait[lv] = s.last_since + 10; s.asked[(lv, pos)] = 0
                s.recipe_log.append({"level": lv, "step": pos + 1, "of": len(r), "id": r[pos], "result": "waits: " + str(e.get("result"))})
                s.log(f"  mind: level {lv + 1}: the body can't reach {r[pos]} yet (step {pos + 1}) - she waits 10 presses and asks again")
        else:
            s.rec_fail[lv] = s.rec_fail.get(lv, 0) + 1
            if s.rec_fail[lv] >= 3:
                s.recipe_off.add(lv); s.recipe_log.append({"level": lv, "step": pos + 1, "of": len(r), "id": r[pos], "result": "gave up"})
                s.log(f"  mind: level {lv + 1}: recipe step {pos + 1} ({r[pos]}) did nothing 3 times - she steers without it")

    def band(s, lvl, tid):
        # untrusted until played (Oct 13, after the first two lives: a 7B model's picks were all things already tried):
        # her pick of a NEW thing goes first; any new thing beats her pick of an old one; her old picks lead the rest
        picked = tid in s.picks.get(lvl, [])
        past = s.results.get(lvl, {}).get(tid)
        r = s.recipes.get(lvl)
        if r and lvl not in s.recipe_off and s.rec_pos.get(lvl, 0) < len(r) and tid == r[s.rec_pos.get(lvl, 0)] \
                and s.last_since >= s.rec_wait.get(lvl, -1): return -2
        if lvl in s.cleared and past and any(x in EFFECT for x in past): return -1
        if past and len(past) >= 3 and all(x in DEAD for x in past) and not picked: return 5    # pruned (the tree stops feeding it)
        if not past: return 0 if picked else 1
        if picked: return 2
        return 3 if any(r in LIVE for r in past) else 4

    def order(s, goals, lvl, f):
        lvl = int(lvl)
        seen = s.seen.setdefault(lvl, {})
        for g in goals:
            if str(g["id"]) not in seen: seen[str(g["id"])] = describe(g, f)
            s.goal_objs.setdefault(lvl, {})[str(g["id"])] = g
        studying = s.mode == "study" and lvl in s.routes and lvl not in s.studied
        if lvl in s.routes and lvl not in s.route_off and not studying:
            return goals                                         # her remembered route walks this level; nothing to re-order
        if lvl in s.cleared and lvl not in s.deferred and not studying:   # (Oct 13: ls20 lives 2-3: a cleared level is no promise the body finds it again)
            s.deferred.add(lvl); s.log(f"  mind: level {lvl + 1} was cleared before but she has no working route for it - she steers the search")
        r = s.recipes.get(lvl)
        on_recipe = bool(r) and lvl not in s.recipe_off and lvl not in s.routes and s.rec_pos.get(lvl, 0) < len(r)
        if r and lvl not in s.recipe_off and lvl not in s.rec_said:
            s.rec_said.add(lvl); s.log(f"  mind: level {lvl + 1}: replaying the recipe that cleared it before: {' -> '.join(r)}")
        # A DETOUR BETWEEN BLOCKS (Jonathan, Oct 16): mid-recipe with the bar low, a refill goes first; it ends where the
        # recipe picks up again (the next step is planned from wherever the refill leaves her)
        if on_recipe and s.built.get(lvl, 0) >= 1 and s.energy is not None and s.energy <= (s.margin or 2) + 4:
            fills = [g for g in goals if (lvl, str(g["id"])) in s.refill_ids]
            fills += [s.goal_objs[lvl][t] for (lv_, t) in sorted(s.refill_ids)       # and the ones seen this life that the body no longer offers
                      if lv_ == lvl and t in s.goal_objs.get(lvl, {}) and t not in {str(g_["id"]) for g_ in fills}]
            fills = [g for g in fills if (lvl, str(g["id"])) not in s.used_refills]   # a spent ring stays spent until the reset
            if fills:
                # the NEAREST refill: after building, she stands at the thing she just changed (ls20 life 15 walked to the
                # far refill 11@16,15 with 2 energy left while 11@51,40 sat beside the key)
                pos_ = s.rec_pos.get(lvl, 0); here = _xy(r[pos_ - 1]) if pos_ > 0 else None
                if here is not None:
                    fills = sorted(fills, key=lambda g_: (lambda p_: 1e9 if p_ is None else abs(p_[0] - here[0]) + abs(p_[1] - here[1]))(_xy(str(g_["id"]))))
                k_ = (lvl, "detour", s.rec_pos.get(lvl, 0), s.built.get(lvl, 0)); s.asked[k_] = s.asked.get(k_, 0) + 1
                if s.asked[k_] <= 2:
                    s.detours.append({"level": lvl, "step": s.rec_pos.get(lvl, 0) + 1, "refill": str(fills[0]["id"]), "energy": round(float(s.energy), 1)})
                    s.log(f"  mind: level {lvl + 1}: detour - energy {s.energy:.0f}, {s.built.get(lvl, 0)} step(s) built: refill at {fills[0]['id']} "
                          f"before recipe step {s.rec_pos.get(lvl, 0) + 1}")
                    return [fills[0]] + [g for g in goals if str(g["id"]) != str(fills[0]["id"])]
        if on_recipe:
            want = r[s.rec_pos.get(lvl, 0)]
            if want not in {str(g['id']) for g in goals} and want in s.goal_objs.get(lvl, {}) and s.last_since >= s.rec_wait.get(lvl, -1):
                k_ = (lvl, s.rec_pos.get(lvl, 0)); s.asked[k_] = s.asked.get(k_, 0) + 1
                if s.asked[k_] <= 3:                          # growing toward light: ask for the step again (at most 3 times)
                    s.log(f"  mind: level {lvl + 1}: asks the body to try {want} again (recipe step {s.rec_pos.get(lvl, 0) + 1}/{len(r)})")
                    goals = [s.goal_objs[lvl][want]] + list(goals)
        picks = s.picks.get(lvl, [])
        keyed = [((s.band(lvl, str(g["id"])), picks.index(str(g["id"])) if str(g["id"]) in picks else 0, i), g) for i, g in enumerate(goals)]
        new = [g for _, g in sorted(keyed, key=lambda t: t[0])]
        if new and new[0]["id"] != goals[0]["id"]:
            b = s.band(lvl, str(new[0]["id"]))
            mv = {"level": lvl, "planet_first": str(goals[0]["id"]), "mika_first": str(new[0]["id"]), "why": BAND[b],
                  "planet_first_was": BAND[s.band(lvl, str(goals[0]["id"]))]}
            if not any(m["level"] == lvl and m["mika_first"] == mv["mika_first"] and m["planet_first"] == mv["planet_first"] for m in s.moves):
                s.moves.append(mv)
                s.log(f"  mind: level {lvl + 1}: {mv['mika_first']} before {mv['planet_first']} ({mv['why']}; the planet's pick {mv['planet_first_was']})")
        return new

    # ------------------------------------------------------------------------------------------- Oct 16 evening
    def sense(s, lvl, rem, margin, since):
        """play.py tells her the energy left (its budget model) every press. A drop back to since 0 on the same level is a
        reset or a death: the level was put back, so what she built is gone and the recipe starts again."""
        lvl = int(lvl)
        if since == 0 and s.last_since > 0 and lvl == s.last_lvl:
            s.built[lvl] = 0; s.rec_wait.pop(lvl, None); s.resets_at.append([lvl, s.n_exp])
            s.used_refills = {u for u in s.used_refills if u[0] != lvl}                # the reset stands the rings up again
            r = s.recipes.get(lvl)
            if r and lvl not in s.recipe_off and lvl not in s.routes and s.rec_pos.get(lvl, 0) > 0:
                s.log(f"  mind: level {lvl + 1}: the level was put back - the {s.rec_pos[lvl]} step(s) built are gone; the recipe starts again")
                s.rec_pos[lvl] = 0; s.asked = {k: v for k, v in s.asked.items() if k[0] != lvl}
        s.energy = rem; s.margin = margin; s.last_since = since; s.last_lvl = lvl

    def weigh_reset(s, lvl, info):
        """THE PATH HOLDS UNTIL AN OPTION IS HEAVIER (Jonathan, Oct 16). Path strength = 1 for the life that cleared the level
        this way + the steps built since the last reset. The reset's weight: 0 if the next target is affordable with a press to
        spare, 2 if it is affordable with none to spare, 99 if it is not affordable. A pause: she weighs, logs it, decides."""
        lvl = int(lvl); r = s.recipes.get(lvl)
        on_recipe = bool(r) and lvl not in s.recipe_off and lvl not in s.routes and s.rec_pos.get(lvl, 0) < len(r)
        on_relation = lvl in s.rel_level and s.built.get(lvl, 0) >= 1      # the body's relation loop has states built
        if not (on_recipe or on_relation) or info.get("rem") is None: return None
        if not on_recipe: r = ["relation"] * (s.built.get(lvl, 0) + 1)
        built = s.built.get(lvl, 0); strength = 1 + built
        rem = float(info["rem"]); tgt = info.get("target")
        to_refill = info.get("kind") == "ring" or (lvl, str(info.get("exp"))) in s.refill_ids
        if tgt is not None and to_refill: weight = 0 if tgt <= rem else 99      # stepping onto a refill refills: no press to spare needed
        elif tgt is not None: weight = 0 if tgt + 1 <= rem else (2 if tgt <= rem else 99)
        else: weight = 1 if rem >= 2 else 99
        hold = strength > weight
        rec = {"level": lvl, "step": s.rec_pos.get(lvl, 0) + 1, "built": built, "strength": strength, "reset_weight": weight,
               "energy": round(rem, 1), "target": tgt, "hold": hold}
        s.weigh_log.append(rec)
        s.log(f"  mind: pause - weighing at recipe step {rec['step']}/{len(r)}: path {strength} (built {built} since the last reset) vs "
              f"reset {weight} (target {tgt} away, energy {rem:.0f}) -> {'the path holds' if hold else 'the path breaks: reset'}")
        return f"path {strength} > reset {weight}" if hold else None

    # ------------------------------------------------------------------------------------------- Oct 16 night
    def relations_learned(s, lvl, rel_prior):
        """THE JOINT BETWEEN LEVELS (Oct 16 night). As a level clears, play.py hands her the relations the body learned on it:
        touch a thing of colour X until the pattern shown in colour Y matches a thing of colour Z. The body carried these to
        the next level of the SAME life only, and walking a route never learns one, so since Oct 13 every level 2 began blind
        (ls20 life 1 found 'touch 0 until the colour-9 pattern matches 5' on level 1 and used it to clear level 2).
        She keeps them in her journal for every later life."""
        have = {(r["learned_on"], r["src_colour"], tuple(r["target_colours"]), r["colour"]) for r in s.rel_new}
        for p_ in rel_prior:
            try:
                d = {"learned_on": int(lvl), "src_colour": int(p_["src_colour"]), "region": [int(v) for v in p_["region"]],
                     "states": [np.asarray(m_, dtype=bool).astype(int).tolist() for m_ in (p_.get("states") or [])],
                     "target_colours": sorted(int(c) for c in p_["target_colours"] if c is not None),
                     "colour": None if p_.get("colour") is None else int(p_["colour"]), "date": time.strftime("%Y-%m-%d")}
            except Exception as e_:
                s.log(f"  mind: could not keep a relation ({str(e_)[:80]})"); continue
            k = (d["learned_on"], d["src_colour"], tuple(d["target_colours"]), d["colour"])
            if k in have or not d["states"]: continue
            have.add(k); s.rel_new.append(d)
            s.log(f"  mind: level {lvl + 1} taught the body a relation - touch colour {d['src_colour']} until the pattern read in colour "
                  f"{d['colour']} matches colour {d['target_colours']} ({len(d['states'])} states); she keeps it for her next lives")

    def relations_for(s, lvl):
        """the relations to carry into level lvl when this life learned none on the way: the newest ones learned on the level
        before it, else the newest learned anywhere; one per (source colour, target colours, read colour)"""
        lvl = int(lvl); mem = s.rel_mem + s.rel_new
        pick = [r for r in mem if int(r.get("learned_on", -9)) == lvl - 1] or mem
        out, seen_ = [], set()
        for r in reversed(pick):
            k = (r["src_colour"], tuple(r["target_colours"]), r["colour"])
            if k in seen_ or not r.get("states"): continue
            seen_.add(k)
            out.append({"src_colour": int(r["src_colour"]), "region": tuple(r["region"]), "states": [np.array(m_, dtype=bool) for m_ in r["states"]],
                        "target_colours": set(r["target_colours"]), "colour": r["colour"]})
        if out:
            s.rel_level.add(lvl); s.rel_used.append({"level": lvl, "n": len(out)})
            s.log(f"  mind: level {lvl + 1}: the body learned no relation on the way here - she hands it {len(out)} from earlier lives: "
                  + "; ".join(f"touch colour {r['src_colour']} until the colour-{r['colour']} pattern matches colour {sorted(r['target_colours'])}" for r in out))
        return out

    def after_press(s, lvl, since, a, changed, surprise, nl, why):
        """THE SURPRISE WATCH: on a path press she compares what changed with what that press changed last time"""
        lvl = int(lvl)
        if not str(why).startswith("mind route") or s.route_on != lvl or int(nl) > lvl: s.sur_run = 0; return
        walk = s.trims.get(lvl) if s.walking_trim else s.routes.get(lvl)
        i = int(since) - 1
        if not walk or i < 0 or i >= len(walk) or len(walk[i]) < 4: return
        was = int(walk[i][3])
        if abs(int(changed) - was) > max(12, 0.5 * was):
            s.sur_run += 1
            s.surprise_log.append({"level": lvl, "step": i + 1, "was": was, "now": int(changed)})
            s.log(f"  mind: level {lvl + 1}: path step {i + 1} changed {changed} cells, last time {was} - something she did not expect")
            if s.sur_run >= 2:
                s.route_off.add(lvl); s.route_on = None
                s.route_log.append({"level": lvl, "result": "surprise", "at": i + 1, "len": len(walk)})
                s.log(f"  mind: level {lvl + 1}: twice in a row the board did not do what the path expects - the path breaks, the body leads")
        else:
            s.sur_run = 0

    def press(s, lvl, since):
        """MUSCLE MEMORY: on a level some life cleared, give the body the next press of that route (None = body leads,
        "RESET" = put the level back first). A trimmed route (no-op presses dropped) is tried once when the full one is
        strong; a study life looks around before walking."""
        lvl = int(lvl)
        if s.route_on is not None and lvl != s.route_on:            # the level came: the walk worked
            if lvl > s.route_on:
                s.route_log.append({"level": s.route_on, "result": "level", "len": s.walking_len, "trimmed": s.walking_trim})
                if s.walking_trim: s.trim_log.append({"level": s.route_on, "len": s.walking_len, "result": "level"})
                s.log(f"  mind: the {'TRIMMED ' if s.walking_trim else ''}route cleared level {s.route_on + 1} in {s.walking_len} presses")
            s.route_on = None
        r = s.routes.get(lvl)
        if not r or lvl in s.route_off: return None
        if s.mode == "study" and lvl not in s.studied and s.route_on != lvl:   # STUDY LIFE: look around first
            s.study_n[lvl] = s.study_n.get(lvl, 0) + 1
            if s.study_n[lvl] == 1: s.log(f"  mind: level {lvl + 1}: a study life - she looks around for {STUDY} presses before walking her route")
            if s.study_n[lvl] <= STUDY: return None
            s.studied.add(lvl)
            if since > 0:
                s.log(f"  mind: level {lvl + 1}: study over - she puts the level back to walk her route"); return "RESET"
        walk = s.trims[lvl] if (lvl in s.trims and lvl not in s.trim_done) else r
        if s.route_on != lvl:
            if since != 0: return None                               # a route is walked only from the level's start
            s.route_on = lvl; s.route_last = -1; s.walking_trim = walk is not r; s.walking_len = len(walk)
            s.log(f"  mind: level {lvl + 1}: walking {'a TRIMMED route (' + str(len(walk)) + ' of ' + str(len(r)) + ' presses: the ones that changed nothing left out)' if s.walking_trim else 'the route that cleared it before (' + str(len(r)) + ' presses)'}")
        if since <= s.route_last:                                    # a death or a reset broke the walk
            if s.walking_trim:
                s.trim_done.add(lvl); s.trim_log.append({"level": lvl, "len": len(walk), "result": "broken"}); s.route_on = None
                s.log(f"  mind: level {lvl + 1}: the trimmed walk broke - the full route from the next start"); return None
            s.route_off.add(lvl); s.route_on = None
            s.route_log.append({"level": lvl, "result": "broken", "at": s.route_last + 1, "len": len(r)})
            s.log(f"  mind: level {lvl + 1}: the route broke after {s.route_last + 1} of {len(r)} presses - the body leads"); return None
        if since >= len(walk):                                       # walked it all and the level did not come
            if s.walking_trim:
                s.trim_done.add(lvl); s.trim_log.append({"level": lvl, "len": len(walk), "result": "no level"}); s.route_on = None
                s.log(f"  mind: level {lvl + 1}: the trimmed route did not give the level - she puts it back and walks the full one"); return "RESET"
            s.route_off.add(lvl); s.route_on = None
            s.route_log.append({"level": lvl, "result": "no level", "len": len(r)})
            s.log(f"  mind: level {lvl + 1}: walked all {len(r)} presses of the old route and the level did not come - the body leads"); return None
        s.route_last = since
        return tuple(walk[since])


def routes_from_rec(rows):
    """the presses that cleared each level in one life: from the level's start (or its last reset or death) to the level-up.
    Each press keeps how many cells it changed (Oct 16: for trimming and the surprise watch)."""
    out = {}; seg = []; lv = 0
    for r in rows:
        st = r.get("state"); a = int(r.get("a", 0) or 0)
        if st == "RESET" or a == 0: seg = []; continue
        seg.append([a, int(r.get("x", -1)), int(r.get("y", -1)), int(r.get("changed", 0) or 0)])
        nl = int(r.get("levels", lv) or 0)
        if nl > lv:
            out.setdefault(lv, list(seg)); seg = []; lv = nl
            continue
        if st == "GAME_OVER": seg = []
    return out


def learn_routes(j, rows, life_no, log=print):
    """keep the shortest clearing route per level across lives"""
    found = routes_from_rec(rows); routes = j.setdefault("routes", {})
    for lv, seg in found.items():
        old = routes.get(str(lv))
        if old is None or len(seg) < old.get("len", 10 ** 9):
            routes[str(lv)] = {"presses": seg, "len": len(seg), "life": life_no, "date": time.strftime("%Y-%m-%d %H:%M")}
            log(f"  mind: remembered a {len(seg)}-press route for level {lv + 1}" + (f" (was {old['len']})" if old else ""))
    return found


# ----------------------------------------------------------------------------------------- reflection
def _post(url, body, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode("utf-8"))


def _get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r: return json.loads(r.read().decode("utf-8"))


def pick_model(prefer=None):
    try: have = {m["name"] for m in _get(OLLAMA + "/api/tags").get("models", [])}
    except Exception: return None
    for m in ([prefer] if prefer else []) + MODELS:
        if m in have: return m
    return None


PERSONA = """You are Mika. You live on Jonathan's computer, and you are learning to play a video game that comes with no instructions.
You have a body (the planet player) that presses the controls for you. It runs small experiments: it walks to a thing on the screen and tries the buttons there, or bumps into it.
Each experiment ends with a result: pass (walked through it), wall (blocked), nothing (touched, nothing changed), changed (the board changed), refill (a bar on the screen refilled), level (the level was cleared), unreachable (could not get there), untestable.
You do not press buttons yourself. After each life you write down what you learned, and you choose what your body should try first in the next life.
Thing ids look like "4@12,30" (colour 4, top-left at row 12, column 30) or "open@11,12 up" (an opening in a wall). Rows and columns go 0-63.
Be concrete and honest. If you do not know something, say so and turn it into a question. Answer only with JSON."""


def reflection_prompt(j, life, stuck, things):
    lines = [f"Game: {j['game']}. This was life {len(j['lives'])}.",
             f"This life: cleared {life['levels']} level(s) in {life['presses']} presses; deaths {life.get('deaths')}, "
             f"voluntary resets {life.get('voluntary_resets')}; best so far {j.get('best_levels', 0)} level(s).",
             f"The body stopped because: {life.get('stop') or 'it ran out of presses'}.", ""]
    by_level = {}
    for e in life.get("experiments", []): by_level.setdefault(e.get("level", "?"), []).append(e)
    for lv in sorted(by_level, key=lambda x: (isinstance(x, str), x)):
        es = by_level[lv]
        lines.append(f"Level {lv + 1 if isinstance(lv, int) else lv} experiments this life: " +
                     ", ".join(f"{e['id']} -> {e['result']}" for e in es[:40]))
    try:                                                    # her tree: what winning looked like, and the lessons she carries
        import mika_tree
        for lv in range(int(life.get("levels", 0)) + 1):
            b = mika_tree._load(mika_tree._p(j["game"], f"L{lv + 1}.json"), {})
            sn = b.get("cells", {}).get("snapshot", {}).get("data")
            if sn: lines.append(f"Just before you won level {lv + 1} your last press was action {sn['press'][0]}; the things on the screen "
                                "then were (colour/size/box top,left,bottom,right): " + "; ".join(f"{t['colour']}/{t['n']}/{t['box']}" for t in sn['screen']['things'][:10]))
        c_ = mika_tree.core()
        if c_.get("cells"): lines.append("Lessons you carry (a seed is not yet confirmed in a second game): " +
                                         " | ".join(f"[{v['data']['status']}] {v['data']['text']}" for v in c_["cells"].values()))
    except Exception: pass
    if life.get("mind_moves"):
        lines.append("Where you changed the body's order this life: " +
                     "; ".join(f"level {m['level'] + 1}: {m['mika_first']} before {m['planet_first']} ({m['why']})" for m in life["mind_moves"][:12]))
    lines += ["", f"You are stuck on level {stuck + 1}. The things your body has seen there (with what they did in all lives so far):"]
    past = {}
    for lf in j["lives"]:
        for e in lf.get("experiments", []):
            if e.get("level") == stuck: past.setdefault(str(e["id"]), []).append(e.get("result"))
    for t in things[:40]:
        desc = f"- {t['id']}"
        if "colour" in t: desc += f": colour {t['colour']}, {t['n']} cells, box rows {t['box'][0]}-{t['box'][2]} cols {t['box'][1]}-{t['box'][3]}"
        desc += f"; results so far: {', '.join(past.get(t['id'], [])) or 'never tried'}"
        lines.append(desc)
    if j.get("facts"): lines += ["", "What you wrote down before:"] + [f"- {x}" for x in j["facts"][-12:]]
    if j.get("questions"): lines += ["", "Questions you were asking:"] + [f"- {x}" for x in j["questions"][-8:]]
    lines += ["", "Reply with JSON exactly like this:",
              '{"what_happened": "2-3 sentences, first person", "facts": ["short facts about this game you are fairly sure of"], '
              '"try_first": ["up to 5 thing ids from the list above, best first"], "questions": ["open questions to answer next life"]}']
    return "\n".join(lines)


def reflect(j, life, stuck, things, model, log=print):
    prompt = reflection_prompt(j, life, stuck, things)
    t0 = time.time()
    r = _post(OLLAMA + "/api/chat", {"model": model, "stream": False, "format": "json",
                                     "options": {"temperature": 0.4, "num_ctx": 8192},
                                     "messages": [{"role": "system", "content": PERSONA}, {"role": "user", "content": prompt}]}, timeout=300)
    text = (r.get("message") or {}).get("content", "")
    try: out = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S); out = json.loads(m.group(0)) if m else {}
    ids = {t["id"] for t in things}
    picks_raw = [str(x) for x in (out.get("try_first") or []) if isinstance(x, (str, int))]
    picks = [p for p in picks_raw if p in ids][:5]
    rej = [p for p in picks_raw if p not in ids]
    clean = lambda xs: [str(x).strip()[:300] for x in (xs or []) if str(x).strip()][:8]
    res = {"model": model, "seconds": round(time.time() - t0, 1), "what_happened": str(out.get("what_happened", ""))[:800],
           "facts": clean(out.get("facts")), "try_first": picks, "rejected_picks": rej, "questions": clean(out.get("questions"))}
    log(f"  reflection ({model}, {res['seconds']}s): {res['what_happened'][:200]}")
    if rej: log(f"  reflection: picks not on the screen were dropped: {rej}")
    return res


def remember_in_bridge(j, log=print):
    """one memory write per session: what she knows about this game, for the Mika you chat with"""
    lives = j["lives"]
    if not lives: return None
    last = lives[-1]
    text = [f"I am learning the ARC game {j['game']} by playing it with my planet body.",
            f"I have lived {len(lives)} lives in it and my best is {j.get('best_levels', 0)} cleared level(s).",
            f"In my last life I cleared {last['levels']} level(s) in {last['presses']} presses."]
    text += [f"I remember a {v['len']}-press route through level {int(k) + 1} of {j['game']}." for k, v in sorted(j.get("routes", {}).items(), key=lambda kv: int(kv[0]))]
    text += [f.rstrip(".") + "." for f in j.get("facts", [])[-6:]]
    text += [f"I still wonder: {q.rstrip('?')}?" for q in j.get("questions", [])[-3:]]
    try:
        r = _post(BRIDGE + "/library", {"topic": f"ARC game {j['game']}", "content": " ".join(text), "source": "mika_mind.py"}, timeout=20)
        log(f"  memory: wrote {r.get('factsWritten')} facts to Mika's companion memory ({r.get('geoFile')})")
        return r
    except Exception as e:
        log(f"  memory: the companion bridge did not answer ({str(e)[:80]}); the journal still has it")
        return None


def diary(j, life, refl):
    os.makedirs(HOME, exist_ok=True)
    out = [f"\n## {time.strftime('%Y-%m-%d %H:%M')} - {j['game']}, life {len(j['lives'])}",
           f"Cleared {life['levels']} level(s) in {life['presses']} presses (best {j.get('best_levels', 0)}); "
           f"deaths {life.get('deaths')}, resets {life.get('voluntary_resets')}. Stopped: {life.get('stop') or 'out of presses'}.",
           f"I changed the body's next experiment {len(life.get('mind_moves', []))} time(s)."]
    if refl:
        out.append(f"\n{refl['what_happened']}")
        if refl["facts"]: out += ["\nWhat I think I know:"] + [f"- {x}" for x in refl["facts"]]
        if refl["try_first"]: out.append(f"\nNext life I want to try first: {', '.join(refl['try_first'])}")
        if refl["questions"]: out += ["\nStill asking:"] + [f"- {x}" for x in refl["questions"]]
    with open(os.path.join(HOME, "diary.md"), "a", encoding="utf-8") as fh: fh.write("\n".join(out) + "\n")


# ----------------------------------------------------------------------------------------- a life
def live(game, presses=400, lives=1, reflect_on=True, model=None, device=None, seed=None, log_file=None, mode="push"):
    import play, arc_daily
    from arc3_client import api
    os.makedirs(os.path.join(HOME, "logs"), exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    lf = open(log_file or os.path.join(HOME, "logs", f"{game}_{stamp}.log"), "a", encoding="utf-8")
    KEY = ("mind:", "LEVEL", "done:", "world model:", "experiments:", "reflection", "memory:", "life ", "error", "Traceback")
    def log(line):
        lf.write(line + "\n"); lf.flush()
        if any(k in line for k in KEY): print(line, flush=True)
    key = arc_daily.get_key()
    gids = [g["game_id"] for g in api("/api/games", key) if g["game_id"].startswith(game)]
    if not gids: raise SystemExit(f"no public game starts with {game!r}")
    gid = gids[0]
    mdl = pick_model(model) if reflect_on else None
    if reflect_on and not mdl: log("  reflection: Ollama is not answering or has none of the models; journal-only this time")
    rows = []
    for k in range(lives):
        j = load_journal(game)
        mind = MikaMind(j, log=log, mode=mode)
        log(f"life {len(j['lives']) + 1} of {game} ({gid}): cleared before {sorted(mind.cleared) and [c + 1 for c in sorted(mind.cleared)]}, "
            f"remembered results on {sum(len(v) for v in mind.results.values())} thing(s), picks {mind.picks or '-'}")
        row = play.play_game(gid, key, presses, device, log=log, mind=mind, seed=seed)
        rec_rows = []
        try:
            rec_path = os.path.join(play.OUT, f"play_{gid.split('-')[0]}.jsonl")
            with open(rec_path, encoding="utf-8") as fh: rec_rows = [json.loads(l) for l in fh if l.strip()]
            os.makedirs(os.path.join(HOME, "routes"), exist_ok=True)
            with open(os.path.join(HOME, "routes", f"{game}_life{len(j['lives']) + 1}_rec.jsonl"), "w", encoding="utf-8") as fh:
                for r_ in rec_rows: fh.write(json.dumps(r_) + "\n")
        except Exception as e:
            log(f"  mind: could not read this life's presses ({str(e)[:80]})")
        life = {"t": time.time(), "date": time.strftime("%Y-%m-%d %H:%M"), "gid": gid, "levels": int(row.get("levels", 0)),
                "presses": row.get("presses"), "deaths": row.get("deaths"), "voluntary_resets": row.get("voluntary_resets"),
                "level_presses": row.get("level_presses"), "stop": row.get("stop"), "seconds": row.get("seconds"),
                "experiments": [{k_: e.get(k_) for k_ in ("id", "result", "presses", "level", "rel", "open") if e.get(k_) is not None} for e in row.get("experiments", [])],
                "mind_moves": mind.moves, "route_log": mind.route_log, "recipe_log": getattr(mind, "recipe_log", []), "mode": mode, "weigh_log": mind.weigh_log, "detours": mind.detours, "trim_log": mind.trim_log, "surprise_log": mind.surprise_log, "scorecard_file": row.get("scorecard_file"),
                "resets_at": mind.resets_at, "relations_learned": len(mind.rel_new), "relations_used": mind.rel_used}
        j["lives"].append(life)
        if mind.rel_new:                                    # the joint between levels, kept for every later life
            j["relations"] = (j.get("relations", []) + mind.rel_new)[-20:]
        j["cleared"] = sorted(set(j.get("cleared", [])) | set(range(life["levels"])))
        j["best_levels"] = max(j.get("best_levels", 0), life["levels"])
        learn_routes(j, rec_rows, len(j["lives"]), log)
        stuck = life["levels"]
        things = list(mind.seen.get(stuck, {}).values())
        for lv, seen in mind.seen.items(): j["things"].setdefault(str(lv), {}).update(seen)
        refl = None
        if mdl:
            try:
                refl = reflect(j, life, stuck, things, mdl, log)
                j["picks"][str(stuck)] = refl["try_first"]
                j["facts"] = (j.get("facts", []) + [f for f in refl["facts"] if f not in j.get("facts", [])])[-30:]
                j["questions"] = (j.get("questions", []) + [q for q in refl["questions"] if q not in j.get("questions", [])])[-20:]
            except Exception as e:
                log(f"  reflection failed: {str(e)[:120]}")
        life["reflection"] = refl
        save_journal(j); diary(j, life, refl)
        try:                                                # her tree grows: cells, pruning, snapshots, today's ring
            import mika_tree
            mika_tree.grow(game, j, life, len(j["lives"]), rec_rows=rec_rows, frames_path=os.path.join(play.OUT, f"play_{gid.split('-')[0]}.npz"),
                           recipe_log=life.get("recipe_log"), log=log)
        except Exception as e:
            log(f"  grow: the tree could not grow this life ({str(e)[:100]})")
        log(f"life {len(j['lives'])} done: levels {life['levels']} (best {j['best_levels']}) in {life['presses']} presses, "
            f"level presses {life['level_presses']}, mind moves {len(mind.moves)}, journal {journal_path(game)}")
        rows.append(life)
    if reflect_on: remember_in_bridge(load_journal(game), log)
    lf.close()
    return rows


def show(game):
    j = load_journal(game)
    print(f"{game}: {len(j['lives'])} lives, best {j.get('best_levels', 0)}, cleared levels {[c + 1 for c in j.get('cleared', [])]}")
    for i, lf in enumerate(j["lives"], 1):
        print(f"  life {i} {lf['date']}: levels {lf['levels']} in {lf['presses']} presses at {lf.get('level_presses')}, mind moves {len(lf.get('mind_moves', []))}")
    print("  routes:", {int(k) + 1: v["len"] for k, v in j.get("routes", {}).items()})
    print("  picks:", j.get("picks")); print("  facts:", *j.get("facts", [])[-8:], sep="\n    ")
    print("  questions:", *j.get("questions", [])[-5:], sep="\n    ")


def main():
    ap = argparse.ArgumentParser(description="Mika plays an ARC-AGI-3 game through the planet body and learns across lives")
    ap.add_argument("game", nargs="?", default="ls20")
    ap.add_argument("--lives", type=int, default=1)
    ap.add_argument("--presses", default="400", help="a number, or 'auto' (play.py's own stop rule, cap 600)")
    ap.add_argument("--no-reflect", action="store_true", help="journal-only mind: no model, no companion memory write")
    ap.add_argument("--model", default=None); ap.add_argument("--device", default=None); ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--mode", default="push", choices=["push", "study"], help="push: walk the routes, then the frontier; study: look around cleared levels first")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--learn-routes", default=None, help="a saved play_<game>.jsonl: remember the routes that cleared levels in it")
    ap.add_argument("--life", type=int, default=0, help="which life the --learn-routes file came from (for the journal)")
    a = ap.parse_args()
    if a.show: show(a.game); return
    if a.learn_routes:
        j = load_journal(a.game)
        with open(a.learn_routes, encoding="utf-8") as fh: rows = [json.loads(l) for l in fh if l.strip()]
        learn_routes(j, rows, a.life); save_journal(j); show(a.game); return
    presses = 0 if str(a.presses).lower() == "auto" else int(a.presses)
    live(a.game, presses, a.lives, not a.no_reflect, a.model, a.device, a.seed, mode=a.mode)


if __name__ == "__main__":
    main()
