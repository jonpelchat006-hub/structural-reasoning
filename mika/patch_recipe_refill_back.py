"""Oct 16, correcting the no-refill patch: the 400-press test showed every poke of the key followed by a body RESET
(budget out), which puts the level back - so pokes never add up. In life 1 the refills are what kept the energy up so
the pokes could add up. Refills go back into recipes, but a refill step is never a failure: if the bar is full it is
simply skipped (any result moves the recipe on)."""
import ast
F = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\mika_mind.py"
s = open(F, encoding="utf-8").read()
reps = [
    ('                if "level" in e and e.get("result") in ("changed", "level"): by.setdefault(int(e["level"]), []).append(str(e["id"]))   # refills are upkeep\n',
     '                if "level" in e and e.get("result") in EFFECT: by.setdefault(int(e["level"]), []).append(str(e["id"]))\n'
     '                if "level" in e and e.get("result") == "refill": s.refill_ids.add((int(e["level"]), str(e["id"])))\n'),
    ("        s.recipes = {}\n", "        s.recipes = {}; s.refill_ids = set()\n"),
    ("        if e.get(\"result\") in EFFECT:\n            s.rec_pos[lv] = pos + 1; s.rec_fail[lv] = 0\n",
     "        if e.get(\"result\") in EFFECT or (lv, r[pos]) in s.refill_ids:   # a refill step with a full bar is just skipped\n            s.rec_pos[lv] = pos + 1; s.rec_fail[lv] = 0\n"),
]
for old, new in reps:
    assert s.count(old) == 1, old[:60]; s = s.replace(old, new)
ast.parse(s); open(F, "w", encoding="utf-8").write(s); print("refills back in recipes; refill steps never fail")
