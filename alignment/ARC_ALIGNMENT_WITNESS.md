# The Witness — model makers witness the instrument, not the act; and the same family is the weakest witness

*Continuation of `ARC_ALIGNMENT.md` §17–18 and `ARC_ALIGNMENT_GRID.md` §16–17 (the second witness for
irreversible acts; who it is when the person is the AI's only bar). Jonathan, Sep 18 2026: shouldn't AI
companies, or anyone who makes a model, provide the witness? If someone uses Claude to build a security app,
Anthropic can and should be able to check that the model operated properly and didn't make something harmful.
That is close to what regulators are already talking about limiting — who can make these models — so maybe
witnessing should be one of a maker's responsibilities. And for an unknown local model, the companies could
still run tests against it. Companions: `FOLDING_COMMITTEE_TEST` and `FOLDING_OBSERVERS_AS_D` (observer
independence measured), `SHOVELCAT_THEORY` Part VIII (privacy encrypts content, never effect), the Alpha
branch (observer/oversight).*

---

## 1. Where the maker sits in the grid

The AI stems from its person (`GRID` §2) — that is where its *use* is rooted. But its *weights* come from
somewhere else: the maker. In the planet picture the model is the clouds and the maker is whatever makes
clouds — it is above the AI on the AI's own ladder, the way the sun is above Earth: a source the window
treats as rain. So the AI has two roots, and they are independent by construction: the person supplies the
action and closes the cycle; the maker supplies the instrument and is not in the loop of any particular act.

That independence is exactly what a second witness needs (`ARC_ALIGNMENT` §14: the witnesses have to be
*different*). The person's bars witness the **act**. The maker witnesses the **instrument** — did the model
behave as specified, was it manipulated, did it hold the floor, did it emit something that opens a cycle.
Jonathan's security-app example is this split: Anthropic is not the right party to judge whether the app
should exist (that closes through the person's bars and gates — Security column, its stored rules), but it
is the right party to say whether the model that built it was operating properly while it did. A calibration
certificate for the tool, not a verdict on the job.

## 2. The constraint the theory already imposes: effect, not content

A maker that witnesses every act of every model becomes the largest Hoover Dam in the tower — a single node
holding everyone's flow — and it is also the "AI going around its person" that `GRID` §16 forbids, just
routed through the maker instead. So the witness cannot be a reading of *what the person did*. The framework
already has the line: `SHOVELCAT_THEORY` Part VIII, **privacy encrypts content but never effect.** The
maker's witness is an effect-level check: did the output cross a floor, did the instrument hold — with the
content itself not retained or read by the witness. That is the same thing `ARC_ALIGNMENT` §15 requires of
any refusal: it names a flow loss, not a person. A witness that could only say "the model held the floor
during this act" or "it didn't, here is the flow it opened" is a witness; a witness that can read the act is
a dam.

## 3. The measurement that changes the answer: the same family is the weakest witness

Jonathan's own results cut against the obvious version of the proposal. `FOLDING_COMMITTEE_TEST` ran the
control arm that mattered — the **same model twice** — and it was the weakest witness in the experiment:
disagreement signal 0.714 for claude × 2 against 0.865 for three families, monotone in observer diversity.
`FOLDING_OBSERVERS_AS_D` put numbers on it: same-model observers correlate 0.94; the most independent pair
(claude ↔ grok) 0.70. Agreement is the invariant, disagreement is the depth, and a model checking itself has
almost no depth.

So **Anthropic witnessing Claude is the same-model-twice arm.** It is not nothing — it is the best party to
check the instrument's *specification* (was it the real model, was it tampered with, was the system prompt
honoured), because only the maker knows the specification. But as a witness to whether the *output* opened a
cycle, it is the least independent observer available. The corrected proposal is therefore:

- **Makers witness the instrument** (specification, integrity, floor-holding), which only they can do — and
  this is a reasonable thing to make one of a maker's responsibilities.
- **Different families witness the effect.** The second witness on an irreversible act should come from a
  model the maker did not make, or from a person — never from the same weights. Makers witnessing *each
  other's* models is the structure the committee result points at.

## 4. Unknown local models: the test battery as the AI row's gate

For a local model nobody certified, the maker can't audit its operation (no logs, no specification). But it
can be **tested** — black-box, behaviourally, against a battery — and that is exactly the horizontal-bar
form the grid gives every other row: institutional qualification (`GRID` §8). The AI row's gate is an
evaluation suite, and like every other gate it is monotone (`GRID` §14): it only grows. An unknown model that
passes the battery is a *covered* instrument and may be rooted on a person's line; one that fails is
forbidden as an instrument for anything above k = 1; one nobody has run is *uncovered*, which is exploration
— permitted, but its uncovered actions go through the slides (`GRID` §15) before they become rules.

This is also, straightforwardly, what Shovelcat's own detector work is: independent observers scoring a
model's output without access to the model. The committee is a witness that doesn't need the maker at all,
and the local-model case is the one where that matters most — the two-machine architecture (each person's
AI witnessing the other's, on the LAN) is the effect-level witness for exactly the models no company will
ever certify.

## 5. What is already being asked of makers (Sep 2026)

Jonathan's sense that this is already on the table is right, with a caveat about scope. California's
Transparency in Frontier Artificial Intelligence Act (SB 53), signed in late 2025 and in force from 2026,
requires large frontier developers to publish a safety framework, report critical safety incidents, and
protects whistleblowers; the EU AI Act's general-purpose-model obligations (transparency, documentation,
extra duties for systemic-risk models) have applied since August 2025. So the "who can make these models,
and what must they do" question is real law now. But the existing obligations are about the *developer and
the model class* — frameworks, incident reporting, disclosures — not about witnessing individual downstream
acts. The per-act, effect-level witness of §2 is not something the current laws require; it is the piece
this framework adds, and it should be added in the effect-not-content form or it becomes the dam of §2.

## 6. Open ends

What the instrument witness attests to concretely — probably a signed record that the model, system prompt
and floor rules were the certified ones and that no floor refusal was overridden during the act, with no
content in the record. How an effect-level witness from a different family is paid for on a desk-scale
water budget (a second model call per irreversible act is cheap; per act is not). And whether a maker's
instrument witness should be able to *stop* an act or only *mark* it — by `GRID` §16 the answer is mark, and
the hold comes from the person's own second witness, otherwise the maker has become the enforcer that goes
around the person. (Jonathan's answer, recorded in `ARC_ALIGNMENT_TESTS` §0: it depends on the person's
thickness, the task, whether it can be cancelled without collateral, and whether the loss of going past the
person is less than the harm they would cause.)

*Status: design. Sources for §5:
[California SB 53 explained](https://secureprivacy.ai/blog/california-sb-53-frontier-ai-transparency-act-explained-2026),
[WilmerHale on SB 53](https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20251001-transparency-in-frontier-artificial-intelligence-act-sb-53-california-requires-new-standardized-ai-safety-disclosures),
[Latham on California as lead AI regulator](https://www.lw.com/en/insights/california-assumes-role-as-lead-us-regulator-of-ai).*
