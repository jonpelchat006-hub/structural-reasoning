"""Adds the mind's say over the body's relation loop to play.py (guarded: a mind without allow_relation changes nothing)."""
import sys, shutil, time
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "allow_relation" in s:
    print("already patched"); raise SystemExit
shutil.copy(p, p + ".bak_" + time.strftime("%Y%m%d") + "_before_allow_relation")
old1 = '''                            srcobj = next((o for o in graph["objects"] if o["id"] == r_["src"]), None)
                            if srcobj is not None:
                                rel = {"src": srcobj, "rel": r_, "tries": 0, "dst": r_["targets"][0]["object"]}'''
new1 = '''                            srcobj = next((o for o in graph["objects"] if o["id"] == r_["src"]), None)
                            if srcobj is not None and mind is not None and hasattr(mind, "allow_relation"):
                                try:
                                    if not mind.allow_relation(lvl, r_): continue      # her planner may stop the body's loop (Oct 27)
                                except Exception: pass
                            if srcobj is not None:
                                rel = {"src": srcobj, "rel": r_, "tries": 0, "dst": r_["targets"][0]["object"]}'''
assert s.count(old1) == 1, "anchor 1"
s = s.replace(old1, new1)
old2 = '''                if rel is not None: rel["tries"] = 0                                # the HUD state did not survive the reset'''
new2 = old2 + '''
                if rel is not None and mind is not None and hasattr(mind, "allow_relation"):
                    try:
                        if not mind.allow_relation(lvl, rel["rel"], reset=True): rel = None   # Oct 27: she may stop the loop at a reset
                    except Exception: pass'''
assert s.count(old2) == 1, "anchor 2"
s = s.replace(old2, new2)
old3 = '''                if exp is not None and exp.get("rel"): exp = None
                if rel is not None: rel["tries"] = 0
                route_plan = None; met.stand(f)'''
new3 = '''                if exp is not None and exp.get("rel"): exp = None
                if rel is not None: rel["tries"] = 0
                if rel is not None and mind is not None and hasattr(mind, "allow_relation"):
                    try:
                        if not mind.allow_relation(lvl, rel["rel"], reset=True): rel = None   # Oct 27: and at a death
                    except Exception: pass
                route_plan = None; met.stand(f)'''
assert s.count(old3) == 1, "anchor 3"
s = s.replace(old3, new3)
compile(s, p, "exec")
open(p, "w", encoding="utf-8").write(s)
print("patched", p)
