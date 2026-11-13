"""Lets the mind ask for the relation carried from the last level even when one was found on this level:
mind.want_carried(level, rels). Guarded with hasattr, so the daily MikaMind changes nothing. Oct 27 2026."""
import sys, shutil, time, py_compile, tempfile, os
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "want_carried" in s:
    print("already patched"); raise SystemExit
old = '''                        if rel_prior and not any(r_["targets"] for r_ in rels):
                            carried = relations.carry(rel_prior, f, graph["objects"], floor_)'''
new = '''                        want_c_ = False
                        if rel_prior and mind is not None and hasattr(mind, "want_carried"):
                            try: want_c_ = bool(mind.want_carried(lvl, rels))      # Oct 27: her equation needs the carried turn
                            except Exception: want_c_ = False
                        if rel_prior and (want_c_ or not any(r_["targets"] for r_ in rels)):
                            carried = relations.carry(rel_prior, f, graph["objects"], floor_)'''
assert s.count(old) == 1, "anchor"
s2 = s.replace(old, new)
tmp = os.path.join(tempfile.gettempdir(), "play_carry_check.py")
open(tmp, "w", encoding="utf-8").write(s2)
py_compile.compile(tmp, doraise=True)
shutil.copy(p, p + ".bak_" + time.strftime("%Y%m%d") + "_before_carry")
open(p, "w", encoding="utf-8").write(s2)
print("patched", p)
