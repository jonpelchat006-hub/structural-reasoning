"""Oct 16: RECIPE MEMORY. A level some life cleared but with no press route (ls20 level 2): replay the sequence of
experiments that did something on the way to that clear, step by step, before trying anything new. Also: on a
cleared level, things that did something before outrank never-tried things. play.py gets a hook so the mind
hears each experiment's result as it happens (it used to learn only after the life)."""
import ast, shutil
P = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet"
for fn in ("play.py", "mika_mind.py"): shutil.copy2(rf"{P}\{fn}", rf"{P}\{fn}.bak_20261016_before_recipe")


def patch(fn, reps):
    s = open(rf"{P}\{fn}", encoding="utf-8").read()
    for old, new in reps:
        assert s.count(old) == 1, (fn, old[:70]); s = s.replace(old, new)
    ast.parse(s); open(rf"{P}\{fn}", "w", encoding="utf-8").write(s)


patch("play.py", [
    ("        super().__init__(); s._lv = level_fn\n",
     "        super().__init__(); s._lv = level_fn; s.hook = None       # hook: the mind hears each result as it happens (Oct 16)\n"),
    ("            except Exception: pass\n        super().append(e)\n",
     "            except Exception: pass\n        super().append(e)\n        if s.hook is not None:\n            try: s.hook(e)\n            except Exception: pass\n"),
    ("experiments = _LevelTagged(lambda: lvl)\n",
     "experiments = _LevelTagged(lambda: lvl)\n        if mind is not None and hasattr(mind, \"observe\"): experiments.hook = mind.observe\n"),
])

patch("mika_mind.py", [
    ('BAND = {0: "her pick, never tried", 1: "never tried", 2: "her pick, tried before", 3: "did something before", 4: "did nothing before"}\n',
     'BAND = {-2: "the recipe that cleared it before", -1: "did something on a level that was cleared before",\n'
     '        0: "her pick, never tried", 1: "never tried", 2: "her pick, tried before", 3: "did something before", 4: "did nothing before"}\n'
     'EFFECT = {"changed", "refill", "level"}                  # did something (an opening that just let her pass is not counted)\n'),
    ("        s.route_on = None; s.route_last = -1; s.route_off = set(); s.route_log = []\n",
     "        s.route_on = None; s.route_last = -1; s.route_off = set(); s.route_log = []\n"
     "        # RECIPE MEMORY (Oct 16): for a level cleared with no press route, the experiments that did something on the way\n"
     "        # to the clear, in order (the shortest such recipe over all lives)\n"
     "        s.recipes = {}\n"
     "        for life in journal.get(\"lives\", []):\n"
     "            by = {}\n"
     "            for e in life.get(\"experiments\", []):\n"
     "                if \"level\" in e and e.get(\"result\") in EFFECT: by.setdefault(int(e[\"level\"]), []).append(str(e[\"id\"]))\n"
     "            for lv, seq in by.items():\n"
     "                if seq and lv < int(life.get(\"levels\", 0)) and (lv not in s.recipes or len(seq) < len(s.recipes[lv])): s.recipes[lv] = seq\n"
     "        s.rec_pos = {}; s.rec_fail = {}; s.recipe_off = set(); s.recipe_log = []; s.rec_said = set()\n"),
    ("    def band(s, lvl, tid):\n",
     "    def observe(s, e):\n"
     "        \"\"\"play.py calls this with every experiment result as it happens\"\"\"\n"
     "        lv = int(e.get(\"level\", -1)); r = s.recipes.get(lv)\n"
     "        if not r or lv in s.recipe_off or lv in s.routes: return\n"
     "        pos = s.rec_pos.get(lv, 0)\n"
     "        if pos >= len(r) or str(e.get(\"id\")) != r[pos]: return\n"
     "        if e.get(\"result\") in EFFECT:\n"
     "            s.rec_pos[lv] = pos + 1; s.rec_fail[lv] = 0\n"
     "            s.recipe_log.append({\"level\": lv, \"step\": pos + 1, \"of\": len(r), \"id\": r[pos], \"result\": e.get(\"result\")})\n"
     "            s.log(f\"  mind: level {lv + 1}: recipe step {pos + 1}/{len(r)} {r[pos]} -> {e.get('result')}\")\n"
     "        else:\n"
     "            s.rec_fail[lv] = s.rec_fail.get(lv, 0) + 1\n"
     "            if s.rec_fail[lv] >= 3:\n"
     "                s.recipe_off.add(lv); s.recipe_log.append({\"level\": lv, \"step\": pos + 1, \"of\": len(r), \"id\": r[pos], \"result\": \"gave up\"})\n"
     "                s.log(f\"  mind: level {lv + 1}: recipe step {pos + 1} ({r[pos]}) did nothing 3 times - she steers without it\")\n"
     "\n"
     "    def band(s, lvl, tid):\n"),
    ("        picked = tid in s.picks.get(lvl, [])\n        past = s.results.get(lvl, {}).get(tid)\n",
     "        picked = tid in s.picks.get(lvl, [])\n        past = s.results.get(lvl, {}).get(tid)\n"
     "        r = s.recipes.get(lvl)\n"
     "        if r and lvl not in s.recipe_off and s.rec_pos.get(lvl, 0) < len(r) and tid == r[s.rec_pos.get(lvl, 0)]: return -2\n"
     "        if lvl in s.cleared and past and any(x in EFFECT for x in past): return -1\n"),
    ("        picks = s.picks.get(lvl, [])\n        keyed =",
     "        r = s.recipes.get(lvl)\n"
     "        if r and lvl not in s.recipe_off and lvl not in s.rec_said:\n"
     "            s.rec_said.add(lvl); s.log(f\"  mind: level {lvl + 1}: replaying the recipe that cleared it before: {' -> '.join(r)}\")\n"
     "        picks = s.picks.get(lvl, [])\n        keyed ="),
    ('"mind_moves": mind.moves, "route_log": mind.route_log, ',
     '"mind_moves": mind.moves, "route_log": mind.route_log, "recipe_log": getattr(mind, "recipe_log", []), '),
])
print("patched both; backups *.bak_20261016_before_recipe")
