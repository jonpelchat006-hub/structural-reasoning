"""Jonathan's head/tail split on polydisc's PRS (Lehmer / half-GCD style), priced with the GMP oracle.

The first k steps of the normal PRS use only the scalars lf, lg, c1 of each step, and those depend
only on the leading coefficients. So: run k steps on the HEAD (top 2k+2 coefficients) while tracking
cofactors (S = U·F0 + V·G0), then build the two full polynomials after k steps from the cofactors and
the original (small) coefficients, and continue."""
import sys
sys.set_int_max_str_digits(0)
import prs_model as pm
import reference_answers as ref


def pmul(L, a, b):
    """polynomial product (high-to-low lists), logged"""
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x == 0: continue
        for j, y in enumerate(b):
            if y == 0: continue
            out[i + j] += L.m(x, y)
    return out


def padd(a, b):
    n = max(len(a), len(b)); a = [0] * (n - len(a)) + a; b = [0] * (n - len(b)) + b
    return [x + y for x, y in zip(a, b)]


def scal_div(L, p, dm):
    return [L.d(c, dm) if c else 0 for c in p] if dm != 1 else p


def cof_step(L, Uf, Ug, lf, lg, c1, dm):
    """(lg²·Uf − (lf·lg·x + c1)·Ug)/dm for one cofactor"""
    A = L.m(lg, lg); B = L.m(lf, lg)
    t1 = [L.m(A, c) for c in Uf]
    t2 = pmul(L, [B, c1], Ug)
    t1 = [0] * (len(t2) - len(t1)) + t1 if len(t2) > len(t1) else t1
    t2 = [0] * (len(t1) - len(t2)) + t2
    return scal_div(L, [x - y for x, y in zip(t1, t2)], dm)


def split_run(P, k, L, recurse=False):
    F0, G0 = P, pm.deriv(P)
    return split_from(F0, G0, True, k, L, recurse)


def split_from(F0, G0, first, k, L, recurse):
    """k steps by the head/cofactor route from (F0, G0), then the rest (directly, or split again)"""
    if len(G0) <= 1: return G0[0]
    k = min(k, len(G0) - 1)
    h = 2 * k + 4
    F, G = F0[:h + 1], G0[:h]                  # the heads
    UF, VF, UG, VG = [1], [0], [0], [1]         # F = 1·F0 + 0·G0, G = 0·F0 + 1·G0
    fst = first
    for _ in range(k):
        dm = 1 if fst else F[0] * F[0]
        lf, lg = F[0], G[0]
        c1 = L.m(lg, F[1]) - L.m(lf, G[1])
        H = pm.step(F, G, dm, L)               # head of the next polynomial
        UH = cof_step(L, UF, UG, lf, lg, c1, dm)
        VH = cof_step(L, VF, VG, lf, lg, c1, dm)
        F, G, UF, VF, UG, VG = G, H, UG, VG, UH, VH
        fst = False
    # the full polynomials after k steps: S = U·F0 + V·G0, trimmed to their degree
    SF = padd(pmul(L, UF, F0), pmul(L, VF, G0)); SG = padd(pmul(L, UG, F0), pmul(L, VG, G0))
    while SF and SF[0] == 0: SF = SF[1:]
    while SG and SG[0] == 0: SG = SG[1:]
    assert SF[:2] == F[:2] and SG[:2] == G[:2], "head and full disagree"
    if recurse:
        return split_from(SF, SG, False, k, L, recurse)
    # the rest directly
    F, G = SF, SG
    while len(G) > 1:
        H = pm.step(F, G, F[0] * F[0], L)
        F, G = G, H
    return G[0]


def price(L, tag):
    muls = [('mul', a, b) for a, b in L.mul]; divs = [('div', max(a - b, 1), b) for a, b in L.div]
    return pm.gmp_price(muls, tag + "m"), pm.gmp_price(divs, tag + "d"), len(L.mul), len(L.div)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1152921504606859221
    P = ref.candidate_polynomial(n)[0]
    want = ref.polynomial_discriminant(P)
    L = pm.Log(); r, _ = pm.run(P, L)
    m, d, nm, nd = price(L, "v7")
    print(f"n={n}  v7 PRS: products {m:,} + divisions {d:,} = {m + d:,}   ({nm} products, {nd} divisions)", flush=True)
    for rec in (False, True):
        for k in (2, 3, 4, 6, 8, 11):
            L = pm.Log()
            r = split_from(P, pm.deriv(P), True, k, L, rec)
            ok = (r == want or -r == want)
            m2, d2, nm2, nd2 = price(L, f"s{k}{int(rec)}")
            print(f"  {'recursive' if rec else 'one level'} k={k:2d}: correct {ok}  products {m2:,} + divisions {d2:,} = {m2 + d2:,}"
                  f"  ({(m2 + d2) / (m + d) - 1:+.1%})  ({nm2} products, {nd2} divisions)", flush=True)
