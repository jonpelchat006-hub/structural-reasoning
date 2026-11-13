import json, re
from collections import Counter
for game in ["sp80", "ls20"]:
    j = json.load(open(rf"D:\planet\mika\{game}.json", encoding="utf-8"))
    kinds, res_by_kind = Counter(), {}
    for l in j["lives"]:
        for e in l.get("experiments", []):
            if e.get("level") != 1: continue
            k = re.sub(r"@.*", "", str(e.get("id")))
            kinds[k] += 1; res_by_kind.setdefault(k, Counter())[e.get("result")] += 1
    print(f"\n{game} L2 experiment kinds: {dict(kinds)}")
    for k, c in res_by_kind.items(): print("   ", k, dict(c))
    if game == "ls20":
        l1 = j["lives"][0]
        print("  ls20 life 1, level-2 experiments in order:")
        for e in [e for e in l1.get("experiments", []) if e.get("level") == 1]: print("    ", json.dumps(e)[:160])
    print("  facts:", j.get("facts")); print("  questions:", j.get("questions"))
