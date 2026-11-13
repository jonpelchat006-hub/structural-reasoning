import json
import numpy as np
j = json.load(open(r"D:\planet\mika\sp80.json", encoding="utf-8"))
print("L1 route:", j["routes"]["0"]["presses"])
rows = [json.loads(l) for l in open(r"D:\planet\mika\routes\sp80_life10_rec.jsonl", encoding="utf-8") if l.strip()]
print("rec rows:", len(rows), "keys:", list(rows[0].keys()))
for r in rows[:3]: print({k: (v if not isinstance(v, list) or len(v) < 12 else f"list[{len(v)}]") for k, v in r.items()})
from collections import Counter
print("actions used:", Counter(int(r.get("a", 0) or 0) for r in rows))
F = np.load(r"D:\planet\eye\play_sp80.npz")["F"]
# what each action did to the bars on level 2: compare consecutive frames, report moved colours and shift
for t in range(9, 40):
    a = rows[t].get("a") if t < len(rows) else None
    d = (F[t + 1] != F[t])
    if not d.any(): print(t, "a", a, "no change"); continue
    cols = Counter((F[t][d] % 16).tolist()) + Counter((F[t + 1][d] % 16).tolist())
    ys, xs = np.nonzero(d)
    print(t, "a", a, rows[t].get("x"), rows[t].get("y"), "changed cells", int(d.sum()), "colours", dict(cols), "box", (ys.min(), xs.min(), ys.max(), xs.max()))
