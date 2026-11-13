"""Adds the mind's eye on every press to play.py: mind.see(level, frame, levels_now, experiment_id, relation_source_id, why).
Guarded with hasattr, so a mind without see() (the daily MikaMind, ThinkingMind) changes nothing. Oct 27 2026."""
import sys, shutil, time, py_compile, tempfile, os
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "mind.see(" in s:
    print("already patched"); raise SystemExit
old = '''            if mind is not None and hasattr(mind, "after_press"):
                try: mind.after_press(lvl, since, a, int(d.sum()), round(sp, 3), nl, why)
                except Exception: pass
'''
new = old + '''            if mind is not None and hasattr(mind, "see"):               # Oct 27: her core reads the frame after every press
                try: mind.see(lvl, g, nl, exp.get("id") if isinstance(exp, dict) else None,
                              (rel.get("src") or {}).get("id") if isinstance(rel, dict) and isinstance(rel.get("src"), dict) else None, why)
                except Exception: pass
'''
assert s.count(old) == 1, "anchor"
s2 = s.replace(old, new)
tmp = os.path.join(tempfile.gettempdir(), "play_see_check.py")
open(tmp, "w", encoding="utf-8").write(s2)
py_compile.compile(tmp, doraise=True)
shutil.copy(p, p + ".bak_" + time.strftime("%Y%m%d") + "_before_see")
open(p, "w", encoding="utf-8").write(s2)
print("patched", p)
