"""what exactly did ls20 life 1 do on level 2 (the only clear)? experiments in order with presses"""
import json
j = json.load(open(r"D:\planet\mika\ls20.json", encoding="utf-8"))
life = j["lives"][0]
print("life keys:", sorted(life.keys()))
print("levels", life.get("levels"), "level presses", life.get("level_presses"))
tot = 0
for i, e in enumerate(life.get("experiments", [])):
    if int(e.get("level", -1)) != 1: continue
    tot += int(e.get("presses") or 0)
    print(f"{i:3d} {e.get('id'):24s} {e.get('result'):12s} presses {e.get('presses')} cum {tot}")
for k in ("resets", "reset_log", "deaths"):
    if k in life: print(k, str(life[k])[:400])
