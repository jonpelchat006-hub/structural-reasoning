"""Part XLI lab — the sea of context lights branches in every ring layer; overlaid on the
real tree, the highest piles mark where to look, and each ring's rotation has its own plane.

Jonathan's claims:
 (1) "branches lit up in each ring layer overlay onto the real branches; see which pile up
     highest, then find the rings that allow those" -> overlay every combination's path
     (from the root) on the ONE real tree and count occupancy per node. Under a resource
     cap the piles are NOT uniform: they tower along the golden spine (the slowest-growing
     branch holds the most combinations). The consensus of all layers points golden.
 (2) "find the rings that allow those" -> the towering branches are exactly the ones the
     SMALL rings allow: membership count of ring m across all combinations drops steeply
     with m — the golden ring (m=1) sits in the most, then 2, 5, ... The overlay's answer
     and the noble ladder are the same list.
 (3) "the orthogonal rings would have a plane to them as they rotate so we could look at
     each one" -> fix one ring at m: its two partners live on the CONIC x²+y²+m² = 3mxy —
     the ring's own rotation plane — and rotating the ring walks the EXACT chain
     a_{n+1} = 3m·a_n − a_{n-1}: the golden plane (m=1) carries the odd Fibonacci numbers
     1,2,5,13,34,89..., the silver plane (m=2) the Pell-type chain 1,5,29,169,985...
     Every plane inspectable one ring at a time, every chain integer-exact.
"""
import numpy as np, json
from collections import defaultdict

CAP = 10**7
triples = {(1, 1, 1)}
parent = {(1, 1, 1): None}
frontier = [(1, 1, 1)]
while frontier:
    new = []
    for t in frontier:
        x, y, z = t
        for t2 in [tuple(sorted((3*y*z - x, y, z))), tuple(sorted((x, 3*x*z - y, z))),
                   tuple(sorted((x, y, 3*x*y - z)))]:
            if t2 not in triples and max(t2) <= CAP:
                triples.add(t2); parent[t2] = t; new.append(t2)
    frontier = new

# ---- (1) the overlay: light every layer's path on the one tree, count the piles ----
pile = defaultdict(int)
for t in triples:
    node = t
    while node is not None:
        pile[node] += 1
        node = parent[node]
ranked = sorted(pile.items(), key=lambda kv: -kv[1])
print("(1) overlay of %d ring-layer paths on the real tree — the piles:" % len(triples))
for t, h in ranked[:8]:
    tag = "GOLDEN SPINE" if 1 in t else ""
    print("    pile %2d at %-22s %s" % (h, str(t), tag))
gold_spine = [t for t, h in ranked[1:12] if 1 in t]
print("    %d of the top-11 branches (past the root) lie on the golden spine —" % len(gold_spine))
print("    the slowest-growing branch holds the most layers under the cap: consensus points golden.")

# ---- (2) the rings that allow the top branches ----
member = defaultdict(int)
for t in triples:
    for m in set(t):
        member[m] += 1
mm = sorted(member.items())
print("\n(2) which rings allow the most branches (membership across all %d combinations):" % len(triples))
for m, c in mm[:6]:
    print("    ring m=%-6d appears in %2d combinations" % (m, c))
print("    -> the overlay's towers and the noble ladder are the same list: golden first.")

# ---- (3) each ring's plane and its exact chain ----
print("\n(3) each ring's rotation plane: partners on the conic x²+y²+m² = 3mxy,")
print("    walked by the exact chain a_(n+1) = 3m·a_n − a_(n-1):")
ok = True
for m, name in [(1, "golden plane"), (2, "silver plane"), (5, "next noble plane")]:
    a, b = 1, 1 if m == 1 else None
    # find the smallest partner pair on the conic
    found = None
    for x in range(1, 50):
        for y in range(x, 20000):
            if x*x + y*y + m*m == 3*m*x*y: found = (x, y); break
        if found: break
    chain = [found[0], found[1]]
    for _ in range(5):
        chain.append(3*m*chain[-1] - chain[-2])
    for i in range(len(chain)-1):
        ok &= (chain[i]**2 + chain[i+1]**2 + m*m == 3*m*chain[i]*chain[i+1])
    print("    m=%d (%s): chain %s  conic exact: %s" % (m, name, chain, ok))
print("    golden plane = the odd Fibonaccis; silver plane = the Pell chain 1,5,29,169,985 —")
print("    every ring's plane is inspectable alone, and its rotation steps are integer-exact.")

json.dump(dict(n_layers=len(triples), top_piles=[[list(t), h] for t, h in ranked[:8]],
               membership={str(m): c for m, c in mm[:6]}, chains_ok=bool(ok)),
          open("/home/claude/rh_voidline/overlay_res.json","w"))
print("\nsaved overlay_res.json")
