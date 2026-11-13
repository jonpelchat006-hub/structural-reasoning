"""How often does the packed path fall back? Simulate the exact v8 graphs on random inputs."""
import sys, random, time
sys.path.insert(0, "/home/claude/polyv8")
from gen10 import *
import reference_answers as ref
random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
CFG = {"D1": ("15", "D1", [0, 15], 23, 99, (2**18, 2**25)), "D3": ("205", "D3", [0, 7, 11], 14, 0, (2**37, 2**45))}
band = sys.argv[1]; N = int(sys.argv[2])
name, b, cuts, steps, lb, (lo, hi) = CFG[band]
segs = plan(b, cuts, steps, lb)
fails = 0; t = time.time()
for i in range(N):
    n = random.randint(lo, hi) if i > 1 else (lo if i == 0 else hi)
    P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
    g, res, bad, *_ = build(fz, name, segs, steps, lb)
    if g.val(bad) != 0:
        fails += 1; print("fallback at n =", n, flush=True)
    elif i < 40 or i % 50 == 0:
        assert zdec(g.val(res)) == ref.compute_answer("polydisc", n), n
print(f"{band}: {N} inputs, {fails} fallbacks, {time.time() - t:.0f}s")
