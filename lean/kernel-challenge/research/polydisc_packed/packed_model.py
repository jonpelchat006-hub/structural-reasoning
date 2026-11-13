"""Packed PRS: every polynomial is ONE integer F(B) (Kronecker evaluation at B = 2^W); a normal step is
H(B) = (lg²·F(B) − (lf·lg·B + c1)·G(B)) / lf², exact as integers. Prices the GMP work with the oracle and
counts kernel operations, for a lane width W fixed at the sequence's largest coefficient."""
import sys
sys.set_int_max_str_digits(0)
import prs_model as pm
import reference_answers as ref

def model(n, ops_per_step=30):
    P = ref.candidate_polynomial(n)[0]
    L = pm.Log(); r, seq = pm.run(P, L)
    W = max(abs(c).bit_length() for p in seq for c in p) + 2
    ops = []
    for t in range(len(seq) - 2):
        F, G, H = seq[t], seq[t + 1], seq[t + 2]
        lf, lg = F[0], G[0]
        vF = len(F) * W; vG = len(G) * W
        s2 = 2 * abs(lg).bit_length(); sfg = abs(lf).bit_length() + abs(lg).bit_length()
        c1 = abs(lg * F[1] - lf * G[1]).bit_length()
        ops += [("mul", s2, vF), ("mul", sfg, vG), ("mul", c1, vG)]
        if t > 0: ops.append(("div", vF + s2 - 2 * abs(lf).bit_length(), 2 * abs(lf).bit_length()))
    gmp = pm.gmp_price(ops, f"pk{n}")
    kernel_ops = ops_per_step * (len(seq) - 2) + 3 * 25     # steps + packing the input
    return W, gmp, kernel_ops

if __name__ == "__main__":
    for n, v7 in [(300000, 42357658), (1099511628553, 52767331), (1152921504606859221, 557223897)]:
        W, gmp, k = model(n)
        est = gmp + k * 5000
        print(f"n={n}: lane width {W} bits, packed GMP {gmp:,}, ~{k} kernel ops -> estimate {est:,} vs v7 {v7:,}")
