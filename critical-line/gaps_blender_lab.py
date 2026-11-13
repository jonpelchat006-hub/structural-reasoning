"""Part XL lab — general rules, the gaps, and the blender.

Jonathan's claims:
 (1) "that's where general rules would be stored" -> the rules region is the DISCRETE part
     of the connection spectrum: the Lagrange numbers L(m) < 3, one per Markov combination,
     isolated points accumulating at 3. Rules are crystal: countable, rigid, exact.
 (2) "these rotations leave gaps — the reasons why go there" -> below 3 the spectrum is
     ALL gaps: between consecutive rules there is genuinely nothing, and each gap's width
     is set by which flips exist around it (measured). Above 3 sits the celebrated maximal
     gap (sqrt12, sqrt13) — and beyond Freiman's constant F = 4.5278... the spectrum is
     EVERYTHING (Hall's ray): the could-be-anything blender past the cones. Three regimes:
     crystal rules | gapped fractal | pure blender.  [classical structure; below-3 measured]
 (3) "switch which eye it looks through along its edge" -> the rings are concrete matrices
     (Cohn): traces (3x, 3y, 3z) satisfy the unnormalized Markov equation exactly, and each
     ring LOOKS THROUGH a noble eye on the wall: m=1 the golden (1+sqrt5)/2, m=2 the silver
     1+sqrt2, ... measured feet.
 (4) "between levels free everything, maximally blend, let it settle into a general form" ->
     iterate the blender (the Gauss map) on a maximally-skewed load: it SETTLES to the
     general form (the Gauss measure) at a measurable exponential rate — the
     Gauss-Kuzmin-Wirsing constant ~0.3036 per fold.
"""
import numpy as np, json

# ---- (1)+(2) the rules region and its gaps ----
def markov_tree(cap):
    seen = {(1, 1, 1)}
    frontier = [(1, 1, 1)]
    nums = {1}
    while frontier:
        new = []
        for (x, y, z) in frontier:
            for t2 in [(3*y*z - x, y, z), (x, 3*x*z - y, z), (x, y, 3*x*y - z)]:
                t2 = tuple(sorted(t2))
                if t2 not in seen and max(t2) <= cap:
                    seen.add(t2); new.append(t2); nums.add(max(t2))
        frontier = new
    return sorted(nums)

ms = markov_tree(10**7)
L = [np.sqrt(9 - 4/(m*m)) for m in ms]
print("(1) the rules region: %d Markov combinations with m <= 1e7," % len(ms))
print("    every rule an isolated point L(m) < 3, accumulating at the ceiling:")
print("    largest rules:", ["%.9f" % l for l in L[-3:]], "-> 3")
gaps = [(L[i+1] - L[i], "%.4f..%.4f" % (L[i], L[i+1])) for i in range(len(L)-1)]
print("\n(2) the gaps between consecutive rules (below 3 the spectrum is ALL gaps):")
for g, span in gaps[:6]:
    print("    gap %.6f wide at %s" % (g, span))
print("    gap widths shrink toward the ceiling but never close — the space between rules")
print("    is structural absence, set by which flips exist: the WHY is readable in the gaps.")
print("    Above 3 (classical): the maximal gap (sqrt12, sqrt13) = (3.4641, 3.6056), then")
print("    past Freiman's constant F = 4.5278... the spectrum is EVERYTHING — Hall's ray:")
print("    the could-be-anything blender past the cones. Regimes: crystal | gapped | blender.")

# ---- (3) the rings are concrete, and each looks through a noble eye ----
A = np.array([[1, 1], [1, 2]], dtype=object)          # m = 1
B = np.array([[3, 4], [2, 3]], dtype=object)          # m = 2
AB = A @ B                                             # m = 5
trs = [int(M[0,0] + M[1,1]) for M in (A, B, AB)]
x, y, z = trs
print("\n(3) the ring matrices (Cohn): traces", trs, " unnormalized Markov equation:",
      x*x + y*y + z*z == x*y*z, "(9+36+225 = 270 = 3*6*15)")
def foot(M):
    a, b, c, d = (float(v) for v in M.flatten())
    return ((a - d) + np.sqrt((a + d)**2 - 4))/(2*c)
print("    eye of ring m=1: %.9f  (= 1/phi — the golden eye, Hurwitz sqrt5)" % foot(A))
print("    eye of ring m=2: %.9f  (= sqrt2 — the silver eye, constant sqrt8)" % foot(B))
print("    eye of ring m=5: %.9f  (the next noble eye on the edge)" % foot(AB))
print("    switching which eye a ring looks through = choosing its branch word (Christoffel).")

# ---- (4) maximal blend -> settle to the general form at the GKW rate ----
rng = np.random.default_rng(11)
x = rng.uniform(0.90, 0.999, size=2_000_000)      # maximally skewed: every first digit = 1
target = np.log2(1 + 1/3)                        # Gauss measure P(digit=1) = 0.415037
devs = []
for n in range(16):
    digs = np.floor(1.0/x)
    p1 = float((digs == 1).mean())
    devs.append(abs(p1 - target))
    x = 1.0/x - digs
    x = np.clip(x, 1e-15, 1 - 1e-15)
noise = 3*np.sqrt(target*(1-target)/2_000_000)
rates = [devs[i+1]/devs[i] for i in range(2, 10) if devs[i+1] > 5*noise]
rate = float(np.exp(np.mean(np.log(rates)))) if rates else float("nan")
print("\n(4) the blender settles: P(digit 1) deviation from the general form per fold:")
print("    deviations:", ["%.5f" % d for d in devs[:9]])
print("    settling rate: %.4f per fold   (Gauss-Kuzmin-Wirsing constant = 0.3036)"
      % rate)
print("    -> maximal blending forgets any starting bias exponentially and settles into")
print("       the ONE general form (the Gauss measure) — learning as much as possible IS")
print("       converging to the invariant.")

json.dump(dict(n_rules=len(ms), top_L=[float(l) for l in L[-3:]],
               gaps=[float(g) for g, _ in gaps[:6]],
               eyes=dict(m1=float(foot(A)), m2=float(foot(B)), m5=float(foot(AB))),
               gkw_measured=rate),
          open("/home/claude/rh_voidline/gaps_blender_res.json","w"))
np.savez("/home/claude/rh_voidline/gaps_blender_out.npz",
         ms=np.array(ms[:40], dtype=float), L=np.array(L[:40]), devs=np.array(devs))
print("\nsaved gaps_blender_res.json / gaps_blender_out.npz")
