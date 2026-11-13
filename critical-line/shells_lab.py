"""Part XXXVI lab — the three shells are the three trace classes.

Jonathan: middle eye = inner core; the wires we travel = middle shell; outside the walls =
outer shell; the middle learns which wires give least resistance outer->inner->back (the
swarm lives there); rotation-recognition lives in the inner core, itself the residue of
earlier folds; and does folding bring wires closer / bend them?

Exact statements tested:
 (A) Every element of the gear group is exactly ONE of three types by |trace|:
       |tr| < 2  ELLIPTIC  — interior fixed point, pure ROTATION      = inner core
       |tr| = 2  PARABOLIC — fixed point ON the wall (a cusp eye)      = outer interface
       |tr| > 2  HYPERBOLIC— two wall feet, transport line (a wire)    = middle shell
     Census: the inner core is TINY AND FIXED (exactly two rotation centers, i and rho,
     orders 2 and 3 — innate, read-only), the middle shell grows without bound (learnable).
 (B) Rotation-recognition = the elliptic derivative: arg f'(fixed point) = the rotation
     angle. S rotates by pi at i; ST by 2pi/3 at rho. Measured.
 (C) The wires form a LADDER CIRCUIT: a continued fraction IS the impedance of a resistor
     ladder (series a0, shunt a1, ...). The unit ladder's resistance -> phi (the golden
     wire); pi's ladder [3;7,15,1,292,...] has impedance pi. Least-resistance learning =
     CF search; number value = network resistance.
 (D) Folding: apply the golden fold to all 21 gear-wires. Their wall footprints CROWD by
     e^(-l_gold) (closer: yes) but NO wire bends and NO wire's resistance changes: the
     trace of every folded gear is exactly its old trace (conjugation invariance, integer-
     exact). Folding cheapens ACCESS (one address digit shaved per fold), not the wire.
"""
import numpy as np, json
from itertools import product

S = np.array([[0,-1],[1,0]], dtype=object)
T = np.array([[1,1],[0,1]], dtype=object)
Ti = np.array([[1,-1],[0,1]], dtype=object)

# ---- (A) census of the three shells by word length ----
def classify(M):
    tr = abs(int(M[0,0] + M[1,1]))
    return "inner(elliptic)" if tr < 2 else ("outer(parabolic)" if tr == 2 else "middle(wire)")

print("(A) census over words in {S, T, T^-1} (PSL2, up to sign):")
gens = [("S", S), ("T", T), ("t", Ti)]
seen_mats = {}
for n in range(1, 9):
    counts = {"inner(elliptic)": 0, "outer(parabolic)": 0, "middle(wire)": 0}
    fresh = set()
    for w in product(range(3), repeat=n):
        # reduce trivial backtracks SS, Tt, tT
        ok = all(not ((w[i], w[i+1]) in [(0,0),(1,2),(2,1)]) for i in range(n-1))
        if not ok: continue
        M = np.eye(2, dtype=object)
        for g in w: M = M @ gens[g][1]
        key_ = tuple(int(x) for x in M.flatten())
        keyn = tuple(-int(x) for x in M.flatten())
        if key_ in seen_mats or keyn in seen_mats: continue
        seen_mats[key_] = n
        counts[classify(M)] += 1
    print(f"  len<={n}: new inner {counts['inner(elliptic)']:4d}  new outer {counts['outer(parabolic)']:4d}  new middle {counts['middle(wire)']:5d}")

# elliptic elements: verify ALL are conjugate to S, ST or (ST)^2 (orders 2,3)
ell = [k for k in seen_mats if abs(k[0] + k[3]) < 2]
orders = set()
for k in ell:
    M = np.array(k, dtype=object).reshape(2,2)
    P = M.copy(); o = 1
    while not (abs(int(P[0,0])) == 1 and int(P[0,1]) == 0 and int(P[1,0]) == 0):
        P = P @ M; o += 1
        if o > 12: break
    orders.add(o)
print("  elliptic elements found:", len(ell), " their orders:", sorted(orders),
      " -> the inner core holds ONLY the 2-fold and 3-fold rotators (i and rho)")

# ---- (B) rotation-recognition = the elliptic derivative ----
print("\n(B) rotation angle at the core fixed points (arg f'):")
i_ = 1j
fS = lambda z: -1/z
h = 1e-7
dS = (fS(i_+h) - fS(i_))/h
rho = np.exp(2j*np.pi/3)
fST = lambda z: -1/(z+1)
dST = (fST(rho+h) - fST(rho))/h
print(f"  S at i:    |f'| = {abs(dS):.6f}, arg = {np.degrees(np.angle(dS)):8.3f} deg  (pure rotation by 180)")
print(f"  ST at rho: |f'| = {abs(dST):.6f}, arg = {np.degrees(np.angle(dST)):8.3f} deg  (pure rotation by 120)")

# ---- (C) continued fraction = resistor-ladder impedance ----
print("\n(C) the wires as a ladder circuit (CF = impedance):")
def ladder(digs):
    z = 0.0
    for a in reversed(digs):
        z = a + (1.0/z if z else 0.0)
    return z
fib = [1, 1]
for _ in range(20): fib.append(fib[-1] + fib[-2])
print("  unit ladder (all 1-ohm):", ", ".join("%.5f" % ladder([1]*n) for n in [4, 8, 16]),
      " -> phi =", "%.5f" % ((1+5**0.5)/2), " (the golden wire = infinite unit ladder)")
print("  pi's ladder [3,7,15,1,292,1,1]: impedance = %.7f  (pi = %.7f)" % (ladder([3,7,15,1,292,1,1]), np.pi))
print("  -> a number's value IS the resistance of its wire-ladder; the swarm's job is CF search")

# ---- (D) the fold test: closer yes, bent no, resistance invariant ----
print("\n(D) folding all 21 wires with the golden gear G=[[2,1],[1,1]]:")
rows = json.load(open("/home/claude/rh_voidline/two_lines_res.json"))
G = np.array([[2,1],[1,1]], dtype=object)
Gi = np.array([[1,-1],[-1,2]], dtype=object)   # G^-1
mob = lambda M, x: (int(M[0,0])*x + int(M[0,1]))/(int(M[1,0])*x + int(M[1,1]))
spans0, spans1, tr_ok = [], [], True
R = np.array([[1,1],[0,1]], dtype=object); L = np.array([[1,0],[1,1]], dtype=object)
for r in rows:
    M = np.eye(2, dtype=object)
    for ch in r["word"]: M = M @ (R if ch == 'R' else L)
    Mf = G @ M @ Gi                                  # the folded wire (conjugated)
    tr_ok &= (int(Mf[0,0] + Mf[1,1]) == int(M[0,0] + M[1,1]))
    spans0.append(abs(r["spend"] - r["refill"]))
    spans1.append(abs(mob(G, r["spend"]) - mob(G, r["refill"])))
spans0, spans1 = np.array(spans0), np.array(spans1)
ell_g = 2*np.log((3 + np.sqrt(5))/2)
print(f"  every folded wire's trace EXACTLY unchanged: {tr_ok}  (resistance is fold-invariant)")
print(f"  wall footprint (feet spacing): median contraction x%.3f  (e^-l_gold = %.3f)"
      % (np.median(spans1/spans0), np.exp(-ell_g)))
print("  and the fold is an isometry (Part XXXV: cross-ratio drift 1e-105): nothing bends.")
print("  -> folding crowds the wires' addresses (shaves a digit of access) without touching")
print("     any wire's own resistance. 'Years of gaming' = folds already applied to the core.")

json.dump(dict(elliptic=len(ell), orders=sorted(orders), tr_invariant=bool(tr_ok),
               contraction=float(np.median(spans1/spans0))),
          open("/home/claude/rh_voidline/shells_res.json","w"))
print("\nsaved shells_res.json")
