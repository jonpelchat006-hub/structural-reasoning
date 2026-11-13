# Filling the void with hypotheses — the residual you can't flatten becomes a store of diagnosis, affect, and things-to-try-next-time

*Session Aug 2026. Extends `ARC_VOID_DOMAIN` / `ARC_RECURSIVE_VOID` / `ARC_OPERATOR_INDUCTION`. Jonathan: the
void isn't only driven to 0 — where things can't flatten (the pillars that stick up, the shadow), you FILL the
space with why it's there: a hypothesis, a diagnosis, or (with no idea what went wrong) a 'frustration' tag,
plus things-to-try-next-time — the side-knowledge a person processes but that never reaches the final answer.
`fill_void.py`, figure `fill_void.png`. Grounds in `FOLDING_OBSERVERS` (a lone observer can't see depth; the
committee reconstructs it), the memory-pillar work (`FOLDING_SYNTHESIS`: structural void points "understood
empty, optionally filled with layers of episodic memory"), `FOLDING_DISCOVERY` (a positive surprise mints a new
gap ahead = things to try next time), `void_antenna` (the known parts give "the shape of what to try").*

## The idea
The observers can't see an operator's DEPTH from a single view (`FOLDING_OBSERVERS`: "real depth → observers
disagree → the committee reconstructs it"). So one interaction leaves the operator AMBIGUOUS, and that leftover
ambiguity is the void — the pillar that won't flatten. Instead of discarding it, **fill the void with the
partial hypotheses**; accumulated views (a committee over time) then resolve what no single view can. The
contents of a filled void are graded by how much is known:
- **large candidate set → frustration / "no idea what went wrong yet"** — an unresolved, high-uncertainty
  marker that says *poke this first* (surprise-gated compute);
- **narrowed set → a diagnosis forming** ("it's one of {rot180, flipV}");
- **the stored set → things to try next time** (next view, only test the remaining candidates);
- **singleton → resolved** — it leaves the void and becomes a reusable tool.

## Measured (500 streams, 5 operators, 6 views; each view single-axis symmetric so one look is ambiguous)
- **A lone observer can't see depth:** a single view resolves the operator only **25.8%** of the time.
- **FILL-VOID** (store the candidate hypotheses, intersect across views): **26% → 100% resolved by the 2nd
  view**, and 100% correct. Two views along different symmetry axes intersect to the truth — the two-orthogonal-
  observer recovery of `FOLDING_OBSERVERS`, in time instead of space.
- **DISCARD** (forget the residual each time): **stuck at 26% forever** — it only ever commits the operators
  that happen to be unambiguous on a single look; the hard ones are never learned because the partial evidence
  is thrown away.
- **Cost:** FILL-VOID **8.7 pokes/stream** (it stops poking a committed operator); DISCARD **30.0** (keeps
  re-viewing and never commits). Filling the void is 3× cheaper *and* strictly more capable.

## What this adds
The void is not only a residual to zero (`ARC_VOID_DOMAIN`) — it is a **structured store** for the part of the
computation that doesn't reach the answer:
- **Hypotheses / diagnosis.** The stored candidate set is a live diagnosis of the unexplained residual; it is
  exactly the "shape of what to try" (`void_antenna`: known parts along the ray beat a blind guess 13.6×).
- **Affect as an index.** A large candidate set = frustration = *unresolved, high-information, do this first*;
  a small one = near-diagnosis, low priority. Frustration isn't noise — it's the priority tag on the void.
- **Things to try next time = minted gaps.** The stored to-try list is `FOLDING_DISCOVERY`'s minted gap: the
  growth site the next attempt starts from. Discarding it is what makes a solver re-derive from scratch each
  time; keeping it is the amortization (`ARC_RATCHET` drones, one level up — now storing *unsolved* residuals,
  not just solved tools).
- **The pillars and the shadow.** The un-flattenable pillar is the void point; filling it with an episodic
  layer (what happened here, what I tried, how it felt) is exactly the memory-pillar model (`FOLDING_SYNTHESIS`:
  structural pillars, optionally filled, importance = the lift that surfaces them later).

## For the build
On the ARC / game solver this is a concrete upgrade to the failure handling: when the op-generation gate can't
commit (ambiguous or unreproduced), **don't discard — store the narrowed candidate set at that task/element**
and carry it. On the next encounter (a new train pair, a new level, a re-view), intersect rather than restart.
This turns the honest-abstain of `ARC_OPGEN`/`ARC_OPERATOR_INDUCTION` from a dead end into an accumulating
diagnosis, and it prioritises the highest-uncertainty residuals (the frustration tag) for the next probe —
active induction driven by where the void is largest.

## Honest bounds
Synthetic; the ambiguity is engineered (single-axis-symmetric regions) so a single view is usually
unresolvable and orthogonal views intersect cleanly — real evidence would be noisier and the intersection
would need the θ-tolerance band (`ARC_VOID_DOMAIN`) rather than exact set intersection. The "affect" here is a
scalar (candidate-set size) standing in for a richer signal; the claim measured is only that *set size is a
usable priority/uncertainty index*, not that it is emotion. Two symmetry axes suffice here because the family
is small; a larger transform family would need more views. No claim about the real ARC-3 environment (not
loaded). `fill_void.py`; scripts live in the session.
