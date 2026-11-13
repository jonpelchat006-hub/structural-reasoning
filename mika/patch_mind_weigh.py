r"""Oct 16 evening (Jonathan): she changes her mind when an option outweighs her path; detours between blocks (refill
first) that end where the next block starts; trimmed routes and a personal leaderboard; push and study lives; a
surprise watch on path presses; deliberate pauses (logged) where she weighs. Patches mika_mind.py; backup kept."""
import ast, shutil
F = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\mika_mind.py"
shutil.copy2(F, F + ".bak_20261016_before_weigh")
s = open(F, encoding="utf-8").read()

NEW_REGION = r'''    def order(s, goals, lvl, f):
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
            fills = [g for g in goals if (lvl, str(g["id"])) in s.refill_ids] or \
                    [s.goal_objs[lvl][t] for (lv_, t) in sorted(s.refill_ids) if lv_ == lvl and t in s.goal_objs.get(lvl, {})]
            if fills:
                k_ = (lvl, "detour", s.rec_pos.get(lvl, 0), s.built.get(lvl, 0)); s.asked[k_] = s.asked.get(k_, 0) + 1
                if s.asked[k_] <= 2:
                    s.detours.append({"level": lvl, "step": s.rec_pos.get(lvl, 0) + 1, "refill": str(fills[0]["id"]), "energy": round(float(s.energy), 1)})
                    s.log(f"  mind: level {lvl + 1}: detour - energy {s.energy:.0f}, {s.built.get(lvl, 0)} step(s) built: refill at {fills[0]['id']} "
                          f"before recipe step {s.rec_pos.get(lvl, 0) + 1}")
                    return [fills[0]] + [g for g in goals if str(g["id"]) != str(fills[0]["id"])]
        if on_recipe:
            want = r[s.rec_pos.get(lvl, 0)]
            if want not in {str(g['id']) for g in goals} and want in s.goal_objs.get(lvl, {}):
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
            s.built[lvl] = 0
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
        if not on_recipe or info.get("rem") is None: return None
        built = s.built.get(lvl, 0); strength = 1 + built
        rem = float(info["rem"]); tgt = info.get("target")
        if tgt is not None: weight = 0 if tgt + 1 <= rem else (2 if tgt <= rem else 99)
        else: weight = 1 if rem >= 2 else 99
        hold = strength > weight
        rec = {"level": lvl, "step": s.rec_pos.get(lvl, 0) + 1, "built": built, "strength": strength, "reset_weight": weight,
               "energy": round(rem, 1), "target": tgt, "hold": hold}
        s.weigh_log.append(rec)
        s.log(f"  mind: pause - weighing at recipe step {rec['step']}/{len(r)}: path {strength} (built {built} since the last reset) vs "
              f"reset {weight} (target {tgt} away, energy {rem:.0f}) -> {'the path holds' if hold else 'the path breaks: reset'}")
        return f"path {strength} > reset {weight}" if hold else None

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


'''
a = s.index("    def order(s, goals, lvl, f):\n"); b = s.index("def learn_routes(j, rows, life_no, log=print):\n")
s = s[:a] + NEW_REGION + s[b:]

reps = [
    ("    def __init__(s, journal, log=print):\n        s.j = journal; s.log = log\n",
     "    def __init__(s, journal, log=print, mode=\"push\"):\n        s.j = journal; s.log = log; s.mode = mode\n"),
    ("        s.goal_objs = {}; s.asked = {}                  # things seen this life, so she can ask the body to try one again\n",
     "        s.goal_objs = {}; s.asked = {}                  # things seen this life, so she can ask the body to try one again\n"
     "        # Oct 16 evening: weighing, detours, trimming, study lives, the surprise watch\n"
     "        s.built = {}; s.energy = None; s.margin = None; s.last_since = 0; s.last_lvl = -1\n"
     "        s.weigh_log = []; s.detours = []; s.trim_log = []; s.surprise_log = []; s.sur_run = 0\n"
     "        s.studied = set(); s.study_n = {}; s.walking_trim = False; s.walking_len = 0\n"
     "        s.trims = {}; s.trim_done = set()\n"
     "        try:\n"
     "            import mika_tree\n"
     "            for lv, rt in s.routes.items():\n"
     "                b_ = mika_tree._load(mika_tree._p(journal.get(\"game\", \"?\"), f\"L{lv + 1}.json\"), {})\n"
     "                strong = b_.get(\"cells\", {}).get(\"route\", {}).get(\"strength\", 0) >= 2\n"
     "                tr = [p for i, p in enumerate(rt) if i == len(rt) - 1 or len(p) < 4 or int(p[3]) > NOOP]\n"
     "                if strong and len(tr) < len(rt) and len(tr) not in b_.get(\"data\", {}).get(\"trim_failed\", []): s.trims[lv] = tr\n"
     "        except Exception:\n"
     "            pass\n"),
    ("            s.rec_pos[lv] = pos + 1; s.rec_fail[lv] = 0\n",
     "            s.rec_pos[lv] = pos + 1; s.rec_fail[lv] = 0\n"
     "            if e.get(\"result\") in (\"changed\", \"level\"): s.built[lv] = s.built.get(lv, 0) + 1\n"),
    ('EFFECT = {"changed", "refill", "level"}',
     'STUDY = 60                                              # presses a study life spends looking around a cleared level\n'
     'NOOP = 3                                                # a press that changed this many cells or fewer changed nothing (the energy tick)\n'
     'EFFECT = {"changed", "refill", "level"}'),
    ("def live(game, presses=400, lives=1, reflect_on=True, model=None, device=None, seed=None, log_file=None):\n",
     "def live(game, presses=400, lives=1, reflect_on=True, model=None, device=None, seed=None, log_file=None, mode=\"push\"):\n"),
    ("        mind = MikaMind(j, log=log)\n", "        mind = MikaMind(j, log=log, mode=mode)\n"),
    ('"recipe_log": getattr(mind, "recipe_log", []), ',
     '"recipe_log": getattr(mind, "recipe_log", []), "mode": mode, "weigh_log": mind.weigh_log, "detours": mind.detours, '
     '"trim_log": mind.trim_log, "surprise_log": mind.surprise_log, '),
    ('ap.add_argument("--seed", type=int, default=None)\n',
     'ap.add_argument("--seed", type=int, default=None)\n'
     '    ap.add_argument("--mode", default="push", choices=["push", "study"], help="push: walk the routes, then the frontier; study: look around cleared levels first")\n'),
    ("    live(a.game, presses, a.lives, not a.no_reflect, a.model, a.device, a.seed)\n",
     "    live(a.game, presses, a.lives, not a.no_reflect, a.model, a.device, a.seed, mode=a.mode)\n"),
]
for old, new in reps:
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)
ast.parse(s); open(F, "w", encoding="utf-8").write(s)
print("mika_mind.py patched; backup .bak_20261016_before_weigh")
