import json, sys, statistics as st, collections
def load(f):
    d = collections.defaultdict(list)
    for r in json.load(open(f)): d[r['game'][:4]].append(r)
    return d
names = sys.argv[1:]
D = [load(f"runs/{n}.json") for n in names]
print("game  " + "  ".join(f"{n:>12s}" for n in names))
for g in sorted(D[0]):
    print(f"{g}  " + "  ".join(f"{st.mean(x['score'] for x in d[g]):6.2f} {st.mean(x['levels'] for x in d[g]):4.1f}L" for d in D))
print("mean  " + "  ".join(f"{st.mean(st.mean(x['score'] for x in d[g]) for g in d):11.3f}" for d in D))
