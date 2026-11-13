"""Oct 16: refills are upkeep (the body already detours to refill when its bar runs low), not part of a level's
recipe; a refill step 'does nothing' whenever the bar is full and stalled the replay. Recipes keep changed/level only.
Also: ls20 gets 400 presses in the daily run (its one level-2 clear came at press 267 of a 400-press life)."""
import ast
F = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\mika_mind.py"
s = open(F, encoding="utf-8").read()
old = '                if "level" in e and e.get("result") in EFFECT: by.setdefault(int(e["level"]), []).append(str(e["id"]))\n'
new = '                if "level" in e and e.get("result") in ("changed", "level"): by.setdefault(int(e["level"]), []).append(str(e["id"]))   # refills are upkeep\n'
assert s.count(old) == 1; s = s.replace(old, new); ast.parse(s); open(F, "w", encoding="utf-8").write(s)
D = r"D:\planet\mika\mika_daily.py"
d = open(D, encoding="utf-8").read()
d = d.replace('GAMES = [("sp80", 2), ("ls20", 2)]\nPRESSES = "300"\n', 'GAMES = [("sp80", 2, "300"), ("ls20", 2, "400")]\n')
d = d.replace("    for game, lives in GAMES:\n", "    for game, lives, PRESSES in GAMES:\n")
ast.parse(d); open(D, "w", encoding="utf-8").write(d)
print("patched mika_mind (recipes without refills) and mika_daily (ls20 400 presses)")
