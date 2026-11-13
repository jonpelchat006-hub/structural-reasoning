# Evidence, not verdicts — and the correction to my "refutation"

*2026-07-28. **This supersedes the verdict in `FOLDING_CAMERA5_HUMAN_ARM` §3.** I declared level 4
"refuted" because hand strokes and machine masks overlap on boundary complexity. Jonathan named the
error precisely, and he is right:*

> *"It's not just about the count though, it's also about could an AI recreate that too. There's always
> a chance we are going to be wrong, just like there's a chance for someone to randomly guess a sha256
> password, but what are the odds an AI would make a scribble like that?"*

---

## 1. The error, stated plainly

**Overlapping distributions kill a THRESHOLD. They do not kill EVIDENCE.**

The question a forensic observer answers is not *"is this value on the fake side of a line"*. It is

    P(observation | machine)  vs  P(observation | human)

A feature can be enormously informative in that ratio while its marginal distributions overlap
heavily. I conflated the two and wrote off a whole level on the strength of it.

**And there is a second error underneath.** Vertex count is not a property of the hand — it is a
property of the *tool*. A scribble tool produces thousands of boundary points for three seconds of
work; a lasso produces thirty for the same effort. Comparing vertex counts *across tools* measures the
tool, not the labour. That is why the scribble landed at 1280 and looked like a machine mask. Jonathan
said this too: *"for that tool it's not hard to get many points."*

## 2. The right feature is definitional, not incidental

The question "what are the odds a generative editor would produce a blue scribble" answers itself once
you ask what a generative fill is *for*:

> **A generative fill exists to match its surroundings. Drawn ink exists not to.**
> A fill that escaped the local colour gamut would have *failed at its own job*.

That is not a statistical tendency that a better model will erase. It is the objective the model is
trained against. So measure it directly, locally, within the frame — scene, camera, exposure and
compression all cancel.

## 3. Results

| | local gamut escape | uniformity ratio | surround distance (Lab a·b) |
|---|---|---|---|
| **blue scribble (hand)** | **0.926** | 1.50 | **80.1** |
| green line (hand) | 0.000 | 2.10 | 14.4 |
| machine fill, median (n=22) | 0.003 | 1.05 | 2.4 |
| machine fill, **max** | 0.166 | 2.32 | 21.9 |

**The blue scribble is not reached by any of the 22 machine fills, on two independent features.**
Gamut escape 0.926 against a machine maximum of 0.166. Surround distance 80.1 against a machine
maximum of 21.9.

**The green line is not separated, and that is an honest miss.** It is a *translucent* marker — its
saturation is only 91, well inside the cat photo's own range. A pale overlay is a genuinely hard case
and arguably the more AI-like of the two.

## 4. Stating the strength honestly — the rule of three

With **0 of 22** machine fills reaching the observation, the 95% upper bound on P(observation | machine)
is 3/22 ≈ 0.14. So:

> **Likelihood ratio > 7 : 1 in favour of "hand-applied". Not proof. Not a verdict.**

That is *weak-to-moderate* evidence — and the limit is **my sample size, not the feature**. With 200
machine fills and still zero hits it would be LR > 67 : 1. **The ceiling on this claim is a data
problem, not a method problem**, which is the most fixable kind.

This is also the right register for the sha256 analogy. Nobody says a hash collision is impossible;
they say the odds are bounded and state the bound. An observer that reports "LR > 7:1, here is why, and
here is the sample that bound rests on" is more useful and more defensible than one that reports
"FAKE".

## 5. A bug worth recording, since it nearly buried the result

The first version of gamut escape compared the region against the **whole frame's** 99.9th-percentile
saturation. Both hand strokes scored exactly **0.000** — because the landscape contains fully clipped
pixels at s = 255 somewhere, so the global ceiling pinned at the clipping tail and nothing could ever
exceed it.

That is a **broken estimator, not a negative result**, and it would have read as a clean refutation.
"Does not belong" is a *local* property: blue ink over grey sky is out of place regardless of what the
flowers are doing 3000 px away. Taking the ceiling from the surrounding ring moved the blue scribble
from 0.000 to 0.926.

Same lesson as the MakerNote sequence: *a signal read from the wrong place looks exactly like a signal
— and a signal measured against the wrong reference looks exactly like its absence.*

## 6. What this changes about the architecture

Jonathan's framing is the correct one and it should govern the whole stack:

> *"AI detection isn't perfect already, but we cut down on at least one problem, and it should just be
> another opinion rather than a verdict. We should still perform at or around other models that do
> this but also have our opinion backed with reasons from all these tests."*

Three consequences, and they are structural rather than cosmetic:

**Every observer reports a likelihood ratio and a reason, never a label.** "Metadata layout is not one
this camera writes" and "this region escapes its local gamut, unmatched in 22 machine fills" are
statements a claims adjuster or a judge can weigh. "0.87 fake" is not.

**The ratchet needs restating.** `FOLDING_RATCHET_AND_ROUTING` had it as a hard latch — one finding
reaches the bar and the verdict is fixed. In a likelihood frame the ratchet is **the strongest single
LR dominating the combination**, which preserves the intuition ("once I see one sure thing, nothing
takes it back") without pretending to certainty. That is a better fit for the evidence we actually
have.

**"At or around other models" is the right target.** The differentiator was never going to be raw AUC —
it is that every number comes with a mechanism and a stated sample size behind it. That is also
precisely what a DSRI reviewer and an insurance/legal buyer want, and what nobody shipping a single
opaque score can offer.

## 7. Corrected tally

| level | status |
|---|---|
| 1 — imaginary camera (container layout) | **holds** — 1/61 FP, 5/5 on camera 5 |
| 2 — imaginary programs | catalogue exists, untested |
| 3 — plausible human action | untested |
| 4 — effort budget | **partially restored** |

Level 4, restated correctly:

- ❌ **boundary complexity measures human effort** — refuted, and it stays refuted
- ❌ **width CV measures instrument discipline** — refuted, and the rasterisation excuse was tested and
  died (code at r=2 gives CV 0.000; the hand gives 0.324 and 0.602)
- ✅ **colour identity of the changed region is evidence about authorship** — LR > 7:1 on 1 of 2 hand
  strokes, mechanism grounded in what a generative fill is optimised for

## 8. Next

1. **More machine fills.** The LR bound is 7:1 only because n = 22. This is the cheapest possible
   improvement to the strongest claim in the level.
2. **A translucent-overlay arm.** The green line is the failure case and it is the realistic one —
   watermarks, tinted overlays, soft-light layers.
3. **Hand-made selection edits** (clone/heal/paste by hand). Still outstanding from
   `FOLDING_CAMERA5_HUMAN_ARM`, and still the true apples-to-apples control.
4. **Rewrite the ratchet in likelihood terms** and re-derive whether the old max-aggregation results
   survive the translation.

**Code:** `likelihood.py`, `likelihood.json`.
