"""Oct 16: the mind may ask for a repeat. play.py used to accept her order only if it had exactly as many candidates
as the body offered; now it also accepts one that adds back a thing she saw earlier this life (all of the body's
candidates must still be there)."""
import ast, shutil
F = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\play.py"
shutil.copy2(F, F + ".bak_20261016_before_repeat")
s = open(F, encoding="utf-8").read()
old = "                        if ordered_ and len(ordered_) == len(goals): goals = ordered_\n"
new = ("                        ids_ = {c_[\"id\"] for c_ in goals}\n"
       "                        if ordered_ and len(ordered_) >= len(goals) and ids_ <= {c_[\"id\"] for c_ in ordered_}: goals = ordered_   # she may add back a thing she saw this life (Oct 16)\n")
assert s.count(old) == 1
s = s.replace(old, new); ast.parse(s); open(F, "w", encoding="utf-8").write(s); print("patched; backup play.py.bak_20261016_before_repeat")
