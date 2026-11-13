"""Part XXXIX lab — the orthogonal rings as lenses: locked rotation, one-ring flips,
bending and breaking, and the wall-connection ladder.

Jonathan's claims:
 (1) "between turns all the rings could rotate together" -> simultaneous conjugation:
     EVERY trace is exactly invariant. Rotating the whole assembly is free and safe —
     that is why consolidation happens between turns.
 (2) "one could switch its perspective while 2 others stay locked ... find the right
     combination" -> with two rings locked, the third has exactly ONE other perfect
     position: the VIETA FLIP z -> 3xy - z on the Markov equation x^2+y^2+z^2 = 3xyz.
     Every flip lands on another perfect wall-connection; the tree of all combinations
     is the Markov tree. Exploration = flipping one ring at a time.
 (3) "improve the connection to the walls" -> the connection quality of a ring-combination
     IS the Markov spectrum: L(m) = sqrt(9 - 4/m^2), the sharpest constant with which the
     combination's quadratic points hug the wall. The golden branch 1,2,5,13,34,89...
     climbs L = 2.236 -> 3: each flip measurably improves the wall connection.
 (4) "when it lifts with a stored solve the rings wouldnt rotate together and it would
     start bending and breaking" -> rotate ONE generator continuously (not a full flip):
     the boundary relation tr[A,B] = -2 drifts (BENDING); when the commutator's trace
     enters (-2,2) it turns elliptic — the seam spins — and the group BREAKS (indiscrete).
     Only the discrete flip positions re-lock tr[A,B] = -2 exactly.
"""
import numpy as np, json
from itertools import product

Rm = np.array([[1,1],[0,1]], dtype=object)
Lm = np.array([[1,0],[1,1]], dtype=object)
def mat(word):
    M = np.eye(2, dtype=object)
    for ch in word: M = M @ (Rm if ch == 'R' else Lm)
    return M
def tr(M): return int(M[0,0] + M[1,1]) if M.dtype == object else float(M[0,0] + M[1,1])
def inv2i(M):
    a,b,c,d = (int(x) for x in M.flatten())
    return np.array([[d,-b],[-c,a]], dtype=object)

# ---- (1) all rings together: conjugation — every trace exact ----
rng = np.random.default_rng(5)
ok1 = True
words = ["RL", "RRL", "RLL", "RRLL", "RLRLL"]
for _ in range(30):
    G = mat("".join(rng.choice(list("RL"), size=rng.integers(1, 6))))
    Gi = inv2i(G)
    for w in words:
        M = mat(w)
        ok1 &= (tr(G @ M @ Gi) == tr(M))
print("(1) rotate ALL rings together (conjugation): every trace exactly unchanged over"
      " 150 checks:", ok1, " — consolidation between turns is free")

# ---- (2) one ring flips, two locked: the Vieta move on the Markov equation ----
def flips(t):
    x, y, z = t
    return [tuple(sorted((3*y*z - x, y, z))), tuple(sorted((x, 3*x*z - y, z))),
            tuple(sorted((x, y, 3*x*y - z)))]
seen = {(1, 1, 1)}
frontier = [(1, 1, 1)]
ok2 = True
for depth in range(6):
    new = []
    for t in frontier:
        for t2 in flips(t):
            x, y, z = t2
            ok2 &= (x*x + y*y + z*z == 3*x*y*z)
            if t2 not in seen:
                seen.add(t2); new.append(t2)
    frontier = new
print("\n(2) one ring flips while two stay locked (z -> 3xy - z):")
print("    %d distinct perfect combinations reached; Markov equation x²+y²+z²=3xyz holds"
      " EXACTLY at every one: %s" % (len(seen), ok2))
print("    first triples:", sorted(seen, key=lambda t: t[2])[:8])

# ---- (3) the wall-connection ladder ----
print("\n(3) connection-to-the-wall quality L(m) = sqrt(9 - 4/m²) up the golden branch:")
branch = [1, 2, 5, 13, 34, 89, 233]
for m in branch:
    print("    m = %4d :  L = %.6f" % (m, np.sqrt(9 - 4/(m*m))))
print("    m=1 gives sqrt5 = Hurwitz (Part XXXIV: the golden, maximal void); the ladder")
print("    climbs toward 3 — every flip measurably improves the wall connection.")

# ---- (4) bending and breaking: rotate ONE ring continuously ----
A = np.array([[1.0, 1.0], [1.0, 2.0]])
B = np.array([[1.0, -1.0], [-1.0, 2.0]])
def comm(P, Q):
    return P @ Q @ np.linalg.inv(P) @ np.linalg.inv(Q)
print("\n(4) locked pair: tr A = %.0f, tr B = %.0f, tr[A,B] = %.6f  (the -2 seam: perfect lock)"
      % (tr(A), tr(B), tr(comm(A, B))))
thetas = np.linspace(0, 0.5, 400)
drift, broke_at = [], None
for th in thetas:
    Rt = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    t_c = tr(comm(A, Rt @ B))
    drift.append(t_c)
    if broke_at is None and -2 < t_c < 2:
        broke_at = th
print("    rotating ONE ring by theta: tr[A,B_th] drifts off -2 (bending);")
print("    at theta = %.4f rad the commutator turns ELLIPTIC — the seam spins: BROKEN"
      % broke_at)
print("    (only the discrete flip positions restore tr = -2 exactly — the stored solve")
print("     must come back up through a full flip, not a partial rotation)")

json.dump(dict(conj_ok=bool(ok1), markov_ok=bool(ok2), n_triples=len(seen),
               ladder={m: float(np.sqrt(9 - 4/(m*m))) for m in branch},
               broke_at=float(broke_at)),
          open("/home/claude/rh_voidline/markov_rings_res.json","w"))
np.savez("/home/claude/rh_voidline/markov_rings_out.npz",
         thetas=thetas, drift=np.array(drift))
print("\nsaved markov_rings_res.json / markov_rings_out.npz")
