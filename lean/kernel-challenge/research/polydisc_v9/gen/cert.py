# Size certificates for the D5 band: integer potentials u, v with  bnd(r,c) * 2^K <= 2^(u_r) * 2^(v_c)
# for every entry of the subresultant matrix S_d(f, g) (all last-column degrees i <= d), from the spec's
# coefficient-width limits only.  Then |S_d coefficient| * 2^(K N) <= N! * 2^(sum u + sum v).
import math, json, sys
import numpy as np
from scipy.optimize import linprog, linear_sum_assignment
def width(k, i):
    num = (k - 3) * (102 * 24 * i - 2 * i * i); den = 100 * 576
    return min(k, max(2, 3 + (num + den - 1) // den))
def bounds(K):
    m = 24
    Fb = {e: (1 if e == m else 2 ** (width(K, m - e) - 1)) for e in range(m + 1)}
    Gb = {e: (e + 1) * Fb[e + 1] for e in range(m)}
    return Fb, Gb
def shcN(P, deg, t, e):
    if t <= e and e - t <= deg: return P[e - t]
    return 0
def matrix_bounds(Fb, Gb, d, i):
    m, n = 24, 23
    nx, ny = n - d, m - d; N = nx + ny
    rows = [(Fb, m, nx - 1 - r) for r in range(nx)] + [(Gb, n, ny - 1 - s) for s in range(ny)]
    def coldeg(c): return m + n - d - 1 - c if c + 1 < N else i
    return [[shcN(P, deg, t, coldeg(c)) for c in range(N)] for (P, deg, t) in rows]
def lg(x): return math.log2(x) if x > 0 else None
def cert(K, d):
    Fb, Gb = bounds(K)
    mats = [matrix_bounds(Fb, Gb, d, i) for i in range(d + 1)]
    N = len(mats[0])
    # entry exponent bound: max over i (only the last column changes)
    W = [[None] * N for _ in range(N)]
    for M in mats:
        for r in range(N):
            for c in range(N):
                if M[r][c]:
                    w = math.ceil(lg(M[r][c]) - 1e-12)
                    while 2 ** w < M[r][c]: w += 1
                    W[r][c] = w if W[r][c] is None else max(W[r][c], w)
    # LP: minimize sum u + sum v, u_r + v_c >= W_rc
    Wmax = max(w for row in W for w in row if w is not None) + 1
    A, b = [], []
    for r in range(N):
        for c in range(N):
            if W[r][c] is not None:
                row = [0] * (2 * N); row[r] = -1; row[N + c] = -1; A.append(row); b.append(-W[r][c])
    res = linprog(np.ones(2 * N), A_ub=np.array(A), b_ub=np.array(b), bounds=[(-4 * Wmax, 4 * Wmax)] * (2 * N), method="highs")
    x = np.round(res.x).astype(int)
    u, v = [int(t) for t in x[:N]], [int(t) for t in x[N:]]
    ok = all(W[r][c] is None or u[r] + v[c] >= W[r][c] for r in range(N) for c in range(N))
    # max assignment for comparison
    BIG = -10**9
    Wm = np.array([[W[r][c] if W[r][c] is not None else BIG for c in range(N)] for r in range(N)])
    ri, ci = linear_sum_assignment(-Wm); best = int(Wm[ri, ci].sum())
    # shift to nonnegative exponents
    t0 = min(u); u = [x - t0 for x in u]; v = [x + t0 for x in v]     # min u = 0, sums unchanged
    Kx = max(0, -min(v)); v = [x + Kx for x in v]
    S = sum(u) + sum(v) - Kx * N          # log2 bound before the factorial
    # q: fact(N) * 2^(sum u + sum v) < 2^(q-1) * 2^(Kx N)
    q = S + 1
    while math.factorial(N) * 2 ** (sum(u) + sum(v)) >= 2 ** (q - 1) * 2 ** (Kx * N): q += 1
    return dict(d=d, N=N, u=[int(t) for t in u], v=[int(t) for t in v], K=int(Kx), q=int(q),
                lp=int(round(res.fun)), assign=best, ok=ok)
if __name__ == "__main__":
    K = 3484
    out = []
    for d in range(22, -1, -1):
        c = cert(K, d); out.append(c)
        print(f"S_{d:2d}: N={c['N']:2d} assignment {c['assign']:6d} LP {c['lp']:6d} ok={c['ok']} shift K={c['K']} q={c['q']}")
    json.dump(out, open("cert_3484.json", "w"))
