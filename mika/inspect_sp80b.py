import json
import numpy as np
from collections import Counter
rows = [json.loads(l) for l in open(r"D:\planet\mika\routes\sp80_life10_rec.jsonl", encoding="utf-8") if l.strip()]
F = np.load(r"D:\planet\eye\play_sp80.npz")["F"]
fives = [t for t in range(9, min(len(rows), len(F) - 1)) if rows[t].get("a") == 5]
print("L2 presses of action 5 at:", fives[:20])
for t in fives[:6]:
    d = F[t + 1] != F[t]
    cols = Counter(zip((F[t][d] % 16).tolist(), (F[t + 1][d] % 16).tolist()))
    print(t, "changed", int(d.sum()), "from->to colours", dict(cols.most_common(6)), "state", rows[t].get("state"), "levels", rows[t].get("levels"))
# L1: what the 8-press route did, frame by frame
for t in range(0, 9):
    d = F[t + 1] != F[t]
    cols = Counter(zip((F[t][d] % 16).tolist(), (F[t + 1][d] % 16).tolist()))
    print("L1", t, "a", rows[t].get("a"), rows[t].get("x"), rows[t].get("y"), "changed", int(d.sum()), dict(cols.most_common(5)))
