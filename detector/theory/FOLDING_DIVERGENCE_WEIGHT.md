# Divergence should weigh something — but only what is measured

*2026-07-31. Jonathan challenged the committee's divergence rule: if the theory is multiple
verification and the observers are independent, one model finding a broken part that the other
missed should still count — so shouldn't a Gemini-fake / Claude-real split lean **ai-generated**
rather than land as "contested, no weight"? And with more observers, shouldn't each opinion carry a
visible weight? Status: DESIGN DISCUSSION, resolves to a measurable upgrade. Feeds the shipped
committee logic in `lib/committee.ts` (detector site v1).*

---

## Part I — The challenge, and why the theory sides with it

The current shipped rule (detector v1): both routes agree → 9:1; one route opines, other abstains →
3:1; routes disagree → **contested, lr null, no weight**.

Jonathan's argument: detection is a search for any broken part. Independent observers check
different things (or the same things under different weights), so a positive finding by one is not
cancelled by the other's clear — misses are expected. Either side can find the break the other
missed, and it should still count.

**The corpus agrees more strongly than intuition does:**

- `FOLDING_OUTER_SLOT` Part III: authentic = a **stable floor atom** — independent routes converge.
  Fake = an **ephemeral isotope** — "holds together for one glance but decays under independent
  multi-route scrutiny — **the observers diverge**." Read strictly: divergence is the decay
  signature, i.e. evidence *toward* generated, not a null.
- `FOLDING_OBSERVERS_AS_D` (measured, n=58): the disagreement channel discriminates AI content at
  **|d| = 0.365** — disagreement between independent observers is a real signal.
- The one contested case in production (Midjourney portrait: Gemini ai-generated 0.85–0.88, Claude
  photographic 0.92) **was AI**. Resolving that divergence toward ai-generated would have been
  correct.
- The current rules contain an oddity the challenge exposes: fake-vs-**abstain** earns 3:1 while
  fake-vs-**real** earns 0 — though the theory says the second carries *more* information.

## Part II — The two brakes (why one positive must not latch)

1. **The union problem.** The container tier's ratchet latches on the strongest single finding
   because container findings carry **measured** false-positive rates (0/61 genuine captures). A
   vision model's "I see an artifact" is an opinion with an unknown, nonzero FP rate — models
   hallucinate artifacts. If either route's positive convicts, the committee FP rate becomes the
   **union** of both routes' FP rates — strictly worse than either model alone, and worst on real
   photos, the trust-killing error class (the 0/72 ethos).
2. **n=1 is not a distribution.** The measured |d| = 0.365 came from disagreement *distributions*
   across many probed regions. A single binary vote split cannot distinguish "fake decaying under
   independent scrutiny" from "one observer erred."

## Part III — Resolution: divergence gets a *measured* weight

Same standard as everything else in the product: no assumed numbers.

- **Measure the divergence rates.** On a labeled set (the n=58 benchmark; production agent_logs as
  known-answer images accumulate): count how often the Gemini+Claude pair splits on known-real vs
  known-AI images. The ratio **is** the likelihood ratio of the "contested" outcome, rule-of-three
  capped by the sample.
- **Ship the lean with its basis.** If splits are ~3× more common on AI content, the report reads:
  "CONTESTED — leans ai-generated, ~3:1, basis: measured divergence rates on n=58." If the rates
  turn out symmetric, the current zero-weight rule was right and is then *measured* rather than
  assumed.
- Until counted, **zero weight remains the honest floor** — asserting the lean from intuition is the
  "0.87 fake" sin.

## Part IV — Scaling to more observers ("how much each opinion weighs")

- Per-route weight = measured LR from that route's hit rate / false-alarm rate on the benchmark —
  capped by rule of three at the benchmark n. Weights become printed, sample-backed quantities.
- **Multiply only across measured independence.** `FOLDING_OBSERVERS_AS_D`: GPT↔Gemini r = 0.91
  (nearly one observer, two logos); Claude↔Grok r = 0.70 (most independent pair). Correlated routes
  discount toward a single vote; only measured independence buys combined weight. "Add a model, add
  3:1" is wrong whenever the added model dissipates into one already in the room.
- Architecture stays two-tier per OBSERVERS_AS_D: one scout for the global read (0.932 alone);
  extra observers earn their cost only on the disagreement channel — routed to the regions the scout
  *cleared*, where the informative disagreement lives.

## Next actions

1. Count the four divergence cells (real/AI × converge/diverge) on the existing n=58 benchmark for
   the shipped Claude+Gemini pair.
2. Seed known-answer images through production periodically so agent_logs accumulates calibration
   data at zero marginal cost.
3. When the cells support it, ship the measured "contested" lean with its printed basis — and cite
   it in the XPRIZE narrative: *even our disagreements carry error bars.*

*Sources: `FOLDING_OUTER_SLOT` (stability = convergence; fake = decay under scrutiny),
`FOLDING_OBSERVERS_AS_D` (|d| = 0.365; independence matrix; two-tier architecture),
`FOLDING_EVIDENCE_NOT_VERDICTS`, `DETECTOR_SITE_V1` (shipped committee rules), production agent_logs
(the contested Midjourney case, 2026-07-30).*
