# Can a Series of Cuts Cancel the Residual? — No, it's a power law, not geometric

*Companion to `FOLDING_ALIASING.md`, `FOLDING_CONSTRAINT_LADDER.md`, `FOLDING_THE_KNIFE.md`. Jonathan's idea: one flat cut leaves ~40% ambiguous; add a second cut "over there," keep finding cuts until the ambiguity is gone. Tested by reconstructing the A/B boundary with K straight cuts; `recursive_cuts.py`, `oblique_cuts.py`.*

## Result — the residual crawls; it does NOT cancel (CONFIRMED)
Residual vs #cuts: axis-aligned 37%→31%(4)→20%(16)→**13%(48–64)**; oblique (best case) 33%→26%(4)→17%(16)→**13%(64)**. Each doubling removes only ~10–13% (ratio ~0.87–0.9), **not** half — a slow power law, **residual ≈ K^−0.22**, not the geometric 40→20→10→gone Jonathan pictured. Oblique barely helps. Reaching ~1% would take on the order of 10⁶+ cuts. You cannot "cut until it's gone."

## Why — the residual IS the web
The stubborn residual is the genuinely nonlocal, woven part — the interdigitated region not separable by any flat surface. A rugged web-built surface has structure at all scales; flat cuts (local operations) are a poor basis for it. Same wall from a new angle (constraint ladder ~98% orthogonal; aliasing ~40% biased; here K^−0.22). Honest double bind: even with perfect placement the rate is a slow power law, AND each cut must be placed using the true boundary (the web) — so the method needs the web as input, it doesn't predict it. What it's good for: the K^−0.22 exponent is a "how woven is this interface" number.

*Artifacts: `recursive_cuts.py`, `oblique_cuts.py`, `cut_decay.png`.*
