"""Price planner3 variants at fixed paired points (judge's kernel window, callgrind)."""
import json, sys, time, collections
sys.path.insert(0, "/home/claude/fibvar"); sys.set_int_max_str_digits(0)
import xbench, planner3 as p3
from planner import fib_pair
PTS = {14: [5375, 9250], 15: [20700, 22300], 16: [35500, 38700], 17: [84000, 89500], 18: [136000, 147000]}

def bases():
    d1 = json.load(open("/home/claude/fibvar/pass1.json"))
    by = collections.defaultdict(list)
    for r in d1: by[r["L"]].append((r["ir"], r["t"], r["P"], r["c"]))
    out = collections.defaultdict(set)
    for L in range(14, 19):
        for _, t, P, c in sorted(by[L])[:4]: out[L].add((t, P, c))
        for t in (7, 8):
            for r in (2, 3):
                P = L - t - r
                if 5 <= P <= 9:
                    out[L].add((t, P, P))
    return out

def variants(L, t, P, c):
    r = L - t - P
    fins = {0: ["C"], 1: ["A", "Ab", "D"]}.get(r, ["D", "E"])
    for fin in fins:
        for tab, conv in (("m0", "sg"),) + ((("m1", "xy"),) if fin in ("C", "A", "D") else ()):
            p = p3.Plan3(L, t, P, c, fin, tab, conv)
            if p.ok(): yield p

def run(plans, out_json, batch=60):
    res = []
    for b0 in range(0, len(plans), batch):
        chunk = plans[b0:b0 + batch]
        extra = p3.common_defs() + "\n" + "\n".join(p3.emit(p, f"pa{i}") for i, p in enumerate(chunk))
        cases = []
        for i, p in enumerate(chunk):
            for n in PTS[p.L]:
                cases.append((f"{i}|{n}", f"pa{i} n", n, fib_pair(n)[0]))
        t0 = time.time()
        r = xbench.run(cases, extra_defs=extra, workers=2)
        for k, w in r.items():
            i, n = k.split("|"); p = chunk[int(i)]
            res.append({"plan": p.name(), "L": p.L, "t": p.t, "P": p.P, "c": p.c, "fin": p.fin, "tab": p.tab,
                        "conv": p.conv, "n": int(n), "ir": w})
        json.dump(res, open(out_json, "w"), indent=0)
        print(f"batch {b0 // batch}: {len(chunk)} plans, {len(cases)} cases, {time.time() - t0:.0f}s", flush=True)
    return res

if __name__ == "__main__":
    B = bases()
    plans = [p for L in sorted(B) for (t, P, c) in sorted(B[L]) for p in variants(L, t, P, c)]
    if len(sys.argv) > 2 and sys.argv[2] == "smoke":
        seen, sm = set(), []
        for p in plans:
            key = (p.fin, p.tab, p.conv)
            if key not in seen: seen.add(key); sm.append(p)
        plans = sm
    print(len(plans), "plans", flush=True)
    run(plans, sys.argv[1])
