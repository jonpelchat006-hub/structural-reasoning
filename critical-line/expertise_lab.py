"""Part XLIII lab — expertise as repeated refolding of one base pixel; friction decay;
and the teacher's watching post at gap zero.

Jonathan's claims:
 (1) "use the same base pixel over and over, unfold and rebuild with new things folded in
     -> more filled-out branches -> access from more sides, no recalculating to turn" ->
     practice = filling the circle's subtree. Measured: turn positions available WITHOUT
     recalculation (filled tangent-neighbor ring) and access sides both grow with rounds
     of practice.
 (2) "less friction internally" -> friction = fresh constructions needed per task inside
     the circle. Measured: mean new-mediant constructions per random task DECAYS with
     practice depth — the practiced circle answers from what it already built.
 (3) "only one pair of hands on the welder; where the gap goes to 0 is where the teacher
     watches" -> the expert and novice circles share exactly ONE point (the tangency,
     gap = 0), and it hovers ABOVE the wall at height exactly h = 1/(q^2 + s^2):
     the finer the pair of skills, the LOWER the watching post — close supervision for
     fine work, high overview for coarse. Verified exactly over many pairs.
"""
import numpy as np, json
from fractions import Fraction

# ---- (1)+(2) practice fills the circle; friction decays ----
def fill_subtree(lo, hi, depth):
    """practice rounds: repeatedly unfold/refold = breadth-fill the cell's mediant tree"""
    filled = {lo, hi}
    frontier = [(lo, hi)]
    for _ in range(depth):
        nxt = []
        for a, b in frontier:
            m = Fraction(a.numerator + b.numerator, a.denominator + b.denominator)
            filled.add(m)
            nxt += [(a, m), (m, b)]
        frontier = nxt
    return filled

lo, hi = Fraction(1, 2), Fraction(1, 1)     # the practiced circle's territory
eye = Fraction(2, 3)                         # its central eye
rng = np.random.default_rng(9)

def route_cost(target, filled):
    """count NEW mediants needed to address target given what practice already built"""
    a, b = lo, hi
    new = 0
    while True:
        m = Fraction(a.numerator + b.numerator, a.denominator + b.denominator)
        if m not in filled: new += 1
        if target == m: return new
        if target < m: b = m
        else: a = m

# random tasks: targets at CF-depth ~9 inside the territory
targets = []
while len(targets) < 300:
    a, b = lo, hi
    for _ in range(9):
        m = Fraction(a.numerator + b.numerator, a.denominator + b.denominator)
        if rng.random() < 0.5: b = m
        else: a = m
    targets.append(Fraction(a.numerator + b.numerator, a.denominator + b.denominator))

print("(1)+(2) practice on the same base pixel (cell [1/2, 1], eye 2/3):")
print("    rounds | filled nodes | eye-neighbors filled (turn positions) | friction (new builds/task)")
rows = []
for d in [1, 2, 4, 6, 8, 10]:
    filled = fill_subtree(lo, hi, d)
    # tangent neighbors of the eye 2/3 inside the cell: |p*3 - q*2| = 1
    nb = sum(1 for f in filled if abs(f.numerator*3 - f.denominator*2) == 1)
    fr = float(np.mean([route_cost(t, filled) for t in targets]))
    rows.append((d, len(filled), nb, fr))
    print("    %6d | %12d | %8d | %8.3f" % (d, len(filled), nb, fr))
print("    -> turn positions grow with practice; friction decays toward zero: the expert")
print("       circle turns without recalculating because every side is already built.")

# ---- (3) the teacher's post: the tangency at gap zero, height 1/(q^2+s^2) ----
print("\n(3) the teacher's watching post (the one shared point of tangent universes):")
ok = True
ex = []
for (p, q, r, s) in [(0,1,1,1), (0,1,1,2), (1,2,2,3), (1,2,1,3), (2,3,3,4), (3,7,2,5), (5,13,3,8)]:
    assert abs(p*s - r*q) == 1
    c1 = np.array([p/q, 1/(2*q*q)]); r1 = 1/(2*q*q)
    c2 = np.array([r/s, 1/(2*s*s)]); r2 = 1/(2*s*s)
    d = np.linalg.norm(c2 - c1)
    tang = c1 + (r1/d)*(c2 - c1)
    h_theory = 1.0/(q*q + s*s)
    ok &= abs(tang[1] - h_theory) < 1e-12
    ex.append((f"{p}/{q}|{r}/{s}", float(tang[1])))
    print("    %s x %s: gap = %.1e, watch post at height %.6f  (theory 1/(q²+s²) = %.6f)"
          % (f"{p}/{q}", f"{r}/{s}", d - r1 - r2, tang[1], h_theory))
print("    exact for all pairs:", ok)
print("    -> the teacher watches from EXACTLY the gap-zero point, hovering at 1/(q²+s²):")
print("       coarse skills are supervised from high overview; the finer the pair, the")
print("       closer the watch. One pair of hands on the welder; one point to see it from.")

json.dump(dict(practice=[(d, n, nb, f) for d, n, nb, f in rows],
               posts=ex, height_exact=bool(ok)),
          open("/home/claude/rh_voidline/expertise_res.json","w"))
print("\nsaved expertise_res.json")
