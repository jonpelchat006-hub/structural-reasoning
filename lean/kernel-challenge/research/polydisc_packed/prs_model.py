"""polydisc: the v7 normal PRS in Python, with every product/division logged by operand size."""
import sys
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/lkc/evaluation/judge")
import reference_answers as ref

def deriv(p):
    d = len(p) - 1
    return [(d - i) * p[i] for i in range(d)]

class Log:
    def __init__(s): s.mul = []; s.div = []
    def m(s, a, b): s.mul.append((abs(a).bit_length(), abs(b).bit_length())); return a * b
    def d(s, a, b):
        s.div.append((abs(a).bit_length(), abs(b).bit_length()))
        q, r = divmod(abs(a), abs(b)); assert r == 0, "inexact"
        return q if (a >= 0) == (b >= 0) else -q

def step(F, G, dm, L):
    lf, lg = F[0], G[0]
    c1 = L.m(lg, F[1]) - L.m(lf, G[1])
    mA, mC = L.m(lg, lg), L.m(lg, lf)
    out = []
    for j in range(len(F) - 2):
        x = F[j + 2]; z = G[j + 1]; y = G[j + 2] if j + 2 < len(G) else 0
        e = L.m(mA, x) - L.m(mC, y) - L.m(c1, z)
        out.append(L.d(e, dm))
    return out

def run(P, L):
    F, G = P, deriv(P)
    seq = [F, G]
    first = True
    while len(G) > 1:
        H = step(F, G, 1 if first else F[0] * F[0], L)
        first = False
        F, G = G, H
        seq.append(H)
    return G[0], seq

if __name__ == "__main__":
    for n in [300000, 1099511628553, 1152921504606859221]:
        P = ref.candidate_polynomial(n)[0]
        L = Log()
        r, seq = run(P, L)
        want = ref.polynomial_discriminant(P)
        print(n, "resultant matches disc:", r == want or -r == want, "| products", len(L.mul), "divisions", len(L.div),
              "| final bits", abs(r).bit_length(), "| coeff bits per poly:", [max(abs(c).bit_length() for c in p) for p in seq][::4])


def gmp_price(ops, tag="x"):
    """instructions GMP spends on a list of ('mul'|'div'|'add'|'sub', bitsA, bitsB) (Lean's own GMP)"""
    import subprocess, os
    path = f"/tmp/ops_{tag}.txt"
    with open(path, "w") as f:
        for o, a, b in ops: f.write(f"{o} {max(a, 1)} {max(b, 1)}\n")
    out = f"/tmp/gp_{tag}.out"
    subprocess.run(f"valgrind --tool=callgrind --collect-atstart=no --callgrind-out-file={out} /home/claude/gmpcost/gmpcost < {path}",
                   shell=True, capture_output=True)
    for l in open(out):
        if l.startswith("summary:"): return int(l.split()[1])
