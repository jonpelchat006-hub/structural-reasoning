"""Write the slot filler's answers for every task it commits to: slotfill_predictions.json.
Per task: the rule (feature names, mode), whether it passed leave-one-out (trusted), and up to two attempts
(one grid per test input). The TypeScript solver can read this as an extra, verified candidate source."""
import json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import slotfill
out = {}
for split in ("train", "eval"):
    tasks = json.load(open(f"{split}_tasks.json")); out[split] = {}
    for tid, task in tasks.items():
        r = slotfill.solve(task, max_attempts=2)
        if r:
            out[split][tid] = {"rule": list(r[0][0]), "mode": r[0][1], "trusted": bool(r[0][2]),
                               "attempts": [[p.tolist() for p in preds] for _, _, _, preds in r]}
    print(split, len(out[split]), "tasks with a rule,", sum(v["trusted"] for v in out[split].values()), "trusted")
json.dump(out, open("slotfill_predictions.json", "w"))
