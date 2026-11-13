"""Oct 16: hook her tree (mika_tree.py) into her lives: grow after each life, prune dead things to the back,
ask the body to repeat a recipe step it stopped offering, and tell her reflection what winning looked like."""
import ast, shutil
F = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\mika_mind.py"
shutil.copy2(F, F + ".bak_20261016_before_tree")
s = open(F, encoding="utf-8").read()
reps = [
    ('        0: "her pick, never tried", 1: "never tried", 2: "her pick, tried before", 3: "did something before", 4: "did nothing before"}\n',
     '        0: "her pick, never tried", 1: "never tried", 2: "her pick, tried before", 3: "did something before", 4: "did nothing before",\n'
     '        5: "pruned: tried 3+ times, never did anything"}\n'),
    ("        s.rec_pos = {}; s.rec_fail = {}; s.recipe_off = set(); s.recipe_log = []; s.rec_said = set()\n",
     "        s.rec_pos = {}; s.rec_fail = {}; s.recipe_off = set(); s.recipe_log = []; s.rec_said = set()\n"
     "        s.goal_objs = {}; s.asked = {}                  # things seen this life, so she can ask the body to try one again\n"),
    ("        if lvl in s.cleared and past and any(x in EFFECT for x in past): return -1\n",
     "        if lvl in s.cleared and past and any(x in EFFECT for x in past): return -1\n"
     "        if past and len(past) >= 3 and all(x in DEAD for x in past) and not picked: return 5    # pruned (the tree stops feeding it)\n"),
    ("        for g in goals:\n            if str(g[\"id\"]) not in seen: seen[str(g[\"id\"])] = describe(g, f)\n",
     "        for g in goals:\n            if str(g[\"id\"]) not in seen: seen[str(g[\"id\"])] = describe(g, f)\n"
     "            s.goal_objs.setdefault(lvl, {})[str(g[\"id\"])] = g\n"),
    ("        picks = s.picks.get(lvl, [])\n        keyed =",
     "        if r and lvl not in s.recipe_off and lvl not in s.routes and s.rec_pos.get(lvl, 0) < len(r):\n"
     "            want = r[s.rec_pos.get(lvl, 0)]\n"
     "            if want not in {str(g['id']) for g in goals} and want in s.goal_objs.get(lvl, {}):\n"
     "                k_ = (lvl, s.rec_pos.get(lvl, 0)); s.asked[k_] = s.asked.get(k_, 0) + 1\n"
     "                if s.asked[k_] <= 3:                          # growing toward light: ask for the step again (at most 3 times)\n"
     "                    s.log(f\"  mind: level {lvl + 1}: asks the body to try {want} again (recipe step {s.rec_pos.get(lvl, 0) + 1}/{len(r)})\")\n"
     "                    goals = [s.goal_objs[lvl][want]] + list(goals)\n"
     "        picks = s.picks.get(lvl, [])\n        keyed ="),
    ("    if life.get(\"mind_moves\"):\n",
     "    try:                                                    # her tree: what winning looked like, and the lessons she carries\n"
     "        import mika_tree\n"
     "        for lv in range(int(life.get(\"levels\", 0)) + 1):\n"
     "            b = mika_tree._load(mika_tree._p(j[\"game\"], f\"L{lv + 1}.json\"), {})\n"
     "            sn = b.get(\"cells\", {}).get(\"snapshot\", {}).get(\"data\")\n"
     "            if sn: lines.append(f\"Just before you won level {lv + 1} your last press was action {sn['press'][0]}; the things on the screen \"\n"
     "                                \"then were (colour/size/box top,left,bottom,right): \" + \"; \".join(f\"{t['colour']}/{t['n']}/{t['box']}\" for t in sn['screen']['things'][:10]))\n"
     "        c_ = mika_tree.core()\n"
     "        if c_.get(\"cells\"): lines.append(\"Lessons you carry (a seed is not yet confirmed in a second game): \" +\n"
     "                                         \" | \".join(f\"[{v['data']['status']}] {v['data']['text']}\" for v in c_[\"cells\"].values()))\n"
     "    except Exception: pass\n"
     "    if life.get(\"mind_moves\"):\n"),
    ("        save_journal(j); diary(j, life, refl)\n",
     "        save_journal(j); diary(j, life, refl)\n"
     "        try:                                                # her tree grows: cells, pruning, snapshots, today's ring\n"
     "            import mika_tree\n"
     "            mika_tree.grow(game, j, life, len(j[\"lives\"]), rec_rows=rec_rows, frames_path=os.path.join(play.OUT, f\"play_{gid.split('-')[0]}.npz\"),\n"
     "                           recipe_log=life.get(\"recipe_log\"), log=log)\n"
     "        except Exception as e:\n"
     "            log(f\"  grow: the tree could not grow this life ({str(e)[:100]})\")\n"),
]
for old, new in reps:
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)
ast.parse(s); open(F, "w", encoding="utf-8").write(s)
print("patched; backup mika_mind.py.bak_20261016_before_tree")
