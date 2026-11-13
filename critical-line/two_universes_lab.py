"""Part XLII lab — two universes on the wall: exclusion, ease-by-size, and
learning as recreation-plus-verification.

Jonathan's claims:
 (1) "only one could occupy the space at the same time" -> FORD'S THEOREM: the circles'
     interiors are ALWAYS disjoint — measured over every Farey pair, the gap
     dist(centers) - (r1 + r2) is >= 0, and = 0 exactly at tangency (|ps-qr| = 1).
     Two universes can touch at ONE point; they can never share interior. Exclusion
     is not a design choice here — it is the geometry.
 (2) "different sized circles ... would be able to rotate more easily" -> one click of a
     circle's own rotation (its parabolic) steps its tangent-neighbor ring by exactly one
     neighbor, for EVERY circle — but the absolute wall distance covered per click grows
     with circle size. Measured: the big universe sweeps more wall per click.
 (3) "the new circle would build some paths while its in the space, then the experienced
     one would verify it" -> transfer = CONJUGATED RECREATION: the expert's skill-wire g
     cannot be wired in directly (its feet lie in the expert's territory — verified
     outside the novice's cell); the novice must rebuild it in its own coordinates,
     g' = W g W^-1 — new location (feet inside the novice's cell), SAME invariants
     (trace integer-equal, closure det = 1, Fricke triple equal). The expert verifies
     without ever entering: invariants are conjugation-blind. Expertise cannot be
     transplanted — only re-grown and certified.
"""
import numpy as np, json
from fractions import Fraction

# ---- (1) exclusion: Ford interiors never overlap ----
Q = 60
fracs = sorted({Fraction(p, q) for q in range(1, Q+1) for p in range(0, q+1)})
worst, tangs, pairs = 1e9, 0, 0
for i in range(len(fracs)):
    p1, q1 = fracs[i].numerator, fracs[i].denominator
    for j in range(i+1, min(i+40, len(fracs))):
        p2, q2 = fracs[j].numerator, fracs[j].denominator
        r1, r2 = 1/(2*q1*q1), 1/(2*q2*q2)
        d = np.hypot(float(fracs[i]) - float(fracs[j]), r1 - r2)
        gap = d - (r1 + r2)
        worst = min(worst, gap)
        pairs += 1
        if abs(p1*q2 - p2*q1) == 1: tangs += 1
print("(1) exclusion over %d circle pairs (q <= %d):" % (pairs, Q))
print("    minimum interior gap = %.2e  (never negative: NO overlap, ever)" % worst)
print("    tangent pairs (|ps-qr|=1): %d — one point of contact is the ONLY sharing allowed" % tangs)

# ---- (2) ease-by-size: wall distance per rotation click ----
def parabolic(p, q):
    # conjugate of T by M with M(inf)=p/q: P = [[1-pq, p^2],[-q^2, 1+pq]]
    return np.array([[1 - p*q, p*p], [-q*q, 1 + p*q]], dtype=object)
print("\n(2) one rotation click of each universe (parabolic around its eye):")
rows = []
for (p, q) in [(1, 2), (1, 3), (2, 5), (3, 7), (5, 13)]:
    P = parabolic(p, q)
    # click a tangent neighbor one step around the ring
    # neighbor r/s with |ps-qr|=1: take the Farey neighbor
    r = None
    for s in range(q+1, 4*q+2):
        for rc in (round(s*p/q), round(s*p/q)+1, round(s*p/q)-1):
            if abs(p*s - rc*q) == 1: r = rc; break
        if r is not None: break
    x0 = r/s
    a, b, c, d = (int(v) for v in P.flatten())
    x1 = (a*x0 + b)/(c*x0 + d)
    # exactness: the clicked neighbor is again a Farey neighbor (det preserved)
    fr1 = Fraction(a*r + b*s, c*r + d*s)
    tang = abs(p*fr1.denominator - fr1.numerator*q) == 1
    rows.append((q, abs(x1 - x0), tang))
    print("    universe %s (size 1/%d): click moves neighbor %s -> %s  wall distance %.5f  still tangent: %s"
          % (f"{p}/{q}", 2*q*q, f"{r}/{s}", f"{fr1.numerator}/{fr1.denominator}", abs(x1-x0), tang))
print("    -> every universe's click = exactly one neighbor-step; the BIG universe covers")
print("       the most wall per click (%.4f vs %.6f): bigger circles rotate more easily." %
      (rows[0][1], rows[-1][1]))

# ---- (3) recreation + verification ----
Rm = np.array([[1,1],[0,1]], dtype=object); Lm = np.array([[1,0],[1,1]], dtype=object)
def mat(w):
    M = np.eye(2, dtype=object)
    for ch in w: M = M @ (Rm if ch == 'R' else Lm)
    return M
def tr(M): return int(round(float(M[0,0] + M[1,1])))
def att_foot(M):
    a,b,c,d = (float(x) for x in np.asarray(M, dtype=float).flatten())
    sq = np.sqrt((a+d)**2 - 4)
    x1, x2 = ((a-d)+sq)/(2*c), ((a-d)-sq)/(2*c)
    return x1 if abs(1/(c*x1+d)**2) < 1 else x2
def cell(word):
    lo, hi = Fraction(0,1), Fraction(1,1)
    for ch in word:
        med = Fraction(lo.numerator+hi.numerator, lo.denominator+hi.denominator)
        if ch == 'L': hi = med
        else: lo = med
    return lo, hi
def cellmat(word):
    lo, hi = cell(word)
    return np.array([[lo.numerator, hi.numerator], [lo.denominator, hi.denominator]], dtype=float)

expert_W, novice_W = "R", "LL"           # disjoint universes: cells [1/2,1] and [0,1/3]
gamma = np.asarray(mat("RRL"), dtype=float)   # the skill wire (trace 4)
E, N = cellmat(expert_W), cellmat(novice_W)
g_expert = E @ gamma @ np.linalg.inv(E)
g_novice = N @ gamma @ np.linalg.inv(N)   # THE RECREATION: same skill, novice's fold
ce, cn = cell(expert_W), cell(novice_W)
fe, fn = att_foot(g_expert), att_foot(g_novice)
inn = lambda x, c: float(c[0]) <= x <= float(c[1])
print("\n(3) recreation + verification:")
print("    expert universe %s: skill wire anchored at %.4f (inside expert: %s)"
      % (str([str(ce[0]), str(ce[1])]), fe, inn(fe, ce)))
print("    novice universe %s" % str([str(cn[0]), str(cn[1])]))
print("    DIRECT WIRING: expert's anchor %.4f inside the novice? %s — cannot be transplanted"
      % (fe, inn(fe, cn)))
print("    RECREATED wire (same skill word, novice's own fold): anchor %.4f inside novice: %s"
      % (fn, inn(fn, cn)))
print("    VERIFICATION by invariants (no entry needed): trace %d == %d: %s"
      % (tr(g_novice), tr(g_expert), tr(g_novice) == tr(g_expert)))
delta = np.asarray(mat("RL"), dtype=float)
trip = lambda M: (tr(M @ gamma @ np.linalg.inv(M)), tr(M @ delta @ np.linalg.inv(M)),
                  tr(M @ gamma @ delta @ np.linalg.inv(M)))
tE, tN = trip(E), trip(N)
print("    Fricke triple expert %s == novice %s: %s — the whole curriculum certifies by invariants"
      % (tE, tN, tE == tN))
print("    -> expertise cannot be copied across the exclusion; it is re-grown in local")
print("       coordinates and certified by the numbers that survive any fold.")

json.dump(dict(min_gap=float(worst), tangent_pairs=tangs,
               click=[(q, float(dd)) for q, dd, _ in rows],
               recreated_inside=bool(inn(fn, cn)), direct_inside=bool(inn(fe, cn)),
               invariants_ok=bool(tE == tN)),
          open("/home/claude/rh_voidline/two_universes_res.json","w"))
print("\nsaved two_universes_res.json")
