"""Before run 26 (Oct 28): level-6 nodes were read while its things moved (wrong squares blamed), and the first press
after each death was read against the frame before the reset (bad jumps). Keep only jumps the spring law explains on
the level's first frame; drop the level-6 nodes. A backup is taken first."""
import json, time, shutil, sys, numpy as np
sys.path.insert(0, r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet")
import mika_core as C
p = r"D:\planet\mika\ls20.json"
shutil.copy(p, r"D:\planet\mika\think\ls20_before_run26_clean.json")
j = json.load(open(p, encoding="utf-8"))
F = np.load(r"D:\planet\eye\play_ls20.npz")["F"]
rec = C.align_rec([json.loads(l) for l in open(r"D:\planet\eye\play_ls20.jsonl", encoding="utf-8")])
first = {}
for k in range(1, min(len(rec), len(F) - 1)):
    first.setdefault(int(rec[k - 1]["levels"]), k)
gone_nodes = [k for k in list(j.get("core_nodes", {})) if k.startswith("L5:")]
for k in gone_nodes: j["core_nodes"].pop(k)
kept = dropped = 0; bad = []
for lv, js in list(j.get("core_moves", {}).get("jumps", {}).items()):
    if int(lv) not in first: continue
    f = np.array(F[first[int(lv)]], copy=True); f[f == 5] = 3
    good = []
    for e in js:
        st = C.step_to(f, (e[0], e[1]), e[2], [1])
        if st is not None and tuple(st[0]) == (e[3], e[4]): good.append(e); kept += 1
        else: dropped += 1; bad.append((int(lv) + 1, e))
    j["core_moves"]["jumps"][lv] = good
j.setdefault("core_fixes", []).append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "what": f"before run 26: removed level-6 nodes {gone_nodes} (read while its things moved); kept {kept} jumps the spring law explains, dropped {dropped} read across a death: {bad}"})
json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False)
print("nodes removed", gone_nodes); print("jumps kept", kept, "dropped", dropped, bad)
