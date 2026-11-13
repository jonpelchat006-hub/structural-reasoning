import json, sys, numpy as np, collections
import slotfill as S
src = open('arc_levels.py').read(); exec(src[src.index('D4 = '):src.index('out = {}')])
split = sys.argv[1]
T = json.load(open(f'{split}_tasks.json'))
det = json.load(open('eval_detail.json'))[split]
done = {d[0] for d in det if d[2] != 'error' and isinstance(d[2], list) and any(x[3] for x in d[2])}
C = [k for k, t in T.items() if classify(t)[0] == 'C' and k not in done]
stat = collections.Counter()
for k in C:
    P, Tt = S.prep(T[k])
    cons = cover_fail = 0; best = None
    for names in S.GROUPS:
        for mode in ('raw', 'abstract'):
            r = S.learn(P, names, mode)
            if r is None: continue
            if not all((pr := S.predict(r, a, bg, F)) is not None and np.array_equal(pr, b) for a, b, bg, F in P): continue
            cons += 1
            miss = sum(1 for a, bg, F in Tt for (key, v) in S.keys_for(F, names, list(zip(*np.nonzero(a == bg))), bg, mode) if key not in r.table)
            if best is None or miss < best[0]: best = (miss, names, mode)
    tag = 'no-consistent-rule' if cons == 0 else 'coverage-only'
    stat[tag] += 1
    print(k, tag, cons, best)
print(stat)
