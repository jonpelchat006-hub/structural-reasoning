# Can a PROVABLE bound fix the kept width tight enough to keep the D5 saving?
# Bound: each PRS coefficient is +-a determinant (checked 223/223), so |det| <= product of column sums (l1),
# using only the spec's coefficient-width limits (known in advance for the band), not the actual values.
import sys, math, random, subprocess
sys.path.insert(0, "/home/claude/polyvar"); sys.set_int_max_str_digits(0)
import prs_model as pm, reference_answers as ref
sys.path.insert(0, "/home/claude/lkc/evaluation/judge")
def width(k, i):                  # spec coefficientWidth for k > 64
    num = (k - 3) * (102 * 24 * i - 2 * i * i); den = 100 * 576
    return min(k, max(2, 3 + (num + den - 1) // den))
K = 3484
fb = [0.0] + [width(K, i) - 1 for i in range(1, 25)]          # log2 bound of |a_i| (a_0 = 1)
gb = [math.log2(24 - k) + fb[k] for k in range(24)]           # g = f': b_k = (24-k) a_k
def lse(xs):
    m = max(xs); return m + math.log2(sum(2**(x - m) for x in xs))
def bound_bits(j):                # log2 bound for every coefficient s_{j,i}, i = j..0
    m, n = 24, 23; W = m + n - j
    def colsum(e):                # l1 bound of the column for degree e
        terms = []
        for r in range(n - j):
            s = n - j - 1 - r; k = m - (e - s)
            if 0 <= e - s <= m: terms.append(fb[k])
        for r in range(m - j):
            s = m - j - 1 - r; k = n - (e - s)
            if 0 <= e - s <= n: terms.append(gb[k])
        return lse(terms)
    fixed = sum(colsum(e) for e in range(W - 1, j, -1))
    return [fixed + colsum(i) for i in range(j, -1, -1)]
GM = "/home/claude/gmpcost/gmpcost"
def price(ops, tag):
    p = f"ops_{tag}.txt"; open(p, "w").write("".join(f"{o} {max(a,1)} {max(b,1)}\n" for o, a, b in ops))
    out = f"cg_{tag}.out"
    subprocess.run(f"valgrind --tool=callgrind --collect-atstart=no --callgrind-out-file={out} {GM} < {p}", shell=True, capture_output=True)
    for l in open(out):
        if l.startswith("summary:"): return int(l.split()[1])
bl = lambda x: abs(x).bit_length()
random.seed(11)
for n in [random.randint(2**57, 2**63) for _ in range(2)]:
    P = ref.candidate_polynomial(n)[0]
    F, G = P, pm.deriv(P); first = True
    low_meas, low_bound, rows = [], [], []
    while len(G) > 1:
        dm = 1 if first else F[0] * F[0]
        lf, lg = F[0], G[0]
        c1 = lg * F[1] - lf * G[1]; mA, mC = lg * lg, lg * lf
        H = []
        for jx in range(len(F) - 2):
            x = F[jx+2]; z = G[jx+1]; y = G[jx+2] if jx + 2 < len(G) else 0
            e = mA * x - mC * y - c1 * z
            H.append(e // dm if (e >= 0) == (dm >= 0) else -((-e) // dm))
        j = len(H) - 1
        qb = [math.ceil(b) + 2 for b in bound_bits(j)]               # per-coefficient provable width (+sign, +1)
        qm = [bl(h) + 2 for h in H]
        rows.append((j, max(qm), max(qb)))
        for qs, ops in [(qm, low_meas), (qb, low_bound)]:
            ops += [("mul", bl(lg), bl(F[1])), ("mul", bl(lf), bl(G[1])), ("mul", bl(lg), bl(lg)), ("mul", bl(lg), bl(lf))]
            if dm != 1: ops += [("mul", max(qs), max(qs))] * 3
            for jx in range(len(F) - 2):
                q = qs[jx]; x = F[jx+2]; z = G[jx+1]; y = G[jx+2] if jx + 2 < len(G) else 0
                ops += [("mul", min(q, bl(mA)), bl(x)), ("and", q + bl(x), q), ("mul", min(q, bl(mC)), bl(y)), ("and", q + bl(y), q),
                        ("mul", min(q, bl(c1)), bl(z)), ("and", q + bl(z), q)]
                if dm != 1: ops += [("mul", q, q), ("and", 2*q, q)]
        F, G, first = G, H, False
    a, b = price(low_meas, f"m{n%1000}"), price(low_bound, f"b{n%1000}")
    print(f"n = {n}: low-part with measured widths {a/1e6:.1f}M, with the provable bound {b/1e6:.1f}M  (full method 469M)")
    for j, qm_, qb_ in rows[::4] + [rows[-1]]:
        print(f"   S_{j:2d}: actual widest {qm_:6d} bits, provable bound {qb_:6d} bits, ratio {qb_/qm_:.3f}")
