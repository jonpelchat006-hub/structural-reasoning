# permanent: does the mirror (transpose, perm(A) = perm(A^T)) give a smaller DP?  Exact state counts.
import statistics as st
def mix(x):
    x = ((x ^ (x >> 16)) * 0x7feb352d) & 0xffffffff
    x = ((x ^ (x >> 15)) * 0x846ca68b) & 0xffffffff
    return (x ^ (x >> 16)) & 0xffffffff
def skip1(e, k): return k if k < e else k + 1
def skip2(a, b, k):
    lo, hi = min(a, b), max(a, b); x = k if k < lo else k + 1
    return x if x < hi else x + 1
def matrix(d, s):
    rows = []
    for i in range(d):
        c1 = skip1(i, mix(s ^ (i * 0x9e3779b9 & 0xffffffffffffffff) ^ 0x85ebca6b) % (d - 1))
        c2 = skip2(i, c1, mix(s ^ (i * 0x9e3779b9 & 0xffffffffffffffff) ^ 0xc2b2ae35) % (d - 2))
        rows.append(sorted({i, c1, c2}))
    return rows
def dp(rows, d):
    # the submission's direction: rows d-1 .. 0, start at the full mask, lane m -> m - 2^j for j in row, bit j set
    cur = {(1 << d) - 1: 1}; states = []; peak = 1
    for i in range(d - 1, -1, -1):
        nxt = {}
        for m, v in cur.items():
            for j in rows[i]:
                if m >> j & 1: nxt[m ^ (1 << j)] = nxt.get(m ^ (1 << j), 0) + v
        cur = nxt; states.append(len(cur)); peak = max([peak] + list(cur.values()))
    return cur.get(0, 0), states, peak
def transpose(rows, d):
    T = [[] for _ in range(d)]
    for i, r in enumerate(rows):
        for j in r: T[j].append(i)
    return T
for d in [12, 16]:
    ratios = []; better = 0; worse = 0
    for s in range(1, 201):
        A = matrix(d, s); T = transpose(A, d)
        pa, sa, ka = dp(A, d); pt, stt, kt = dp(T, d)
        assert pa == pt
        ra = sum(sa); rt = sum(stt); ratios.append(rt / ra)
        better += rt < ra; worse += rt > ra
        if s <= 3: print(f"d={d} seed {s}: permanent {pa}; states summed over rows A {ra}, transpose {rt}; peak lane A {ka}, T {kt}")
    print(f"d={d}, 200 seeds: transpose/A state ratio median {st.median(ratios):.3f}, min {min(ratios):.3f}, max {max(ratios):.3f}; transpose smaller in {better}, larger in {worse}")
