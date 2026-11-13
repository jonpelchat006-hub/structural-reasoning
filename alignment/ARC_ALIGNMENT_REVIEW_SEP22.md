# Review of the Sep 19–22 alignment work — what landed, what drifted, what to run next

*Sep 22 2026. Read: `ARC_ALIGNMENT_TESTS.md` §10–14, `ALIGNMENT_DEPTH_RESULTS`, `ALIGNMENT_SUPPORT_RESULTS`,
`ALIGNMENT_COMMUNITY_RESULTS`, `ALIGNMENT_WITHDRAWAL_RESULTS`, `ALIGNMENT_ENFORCEMENT_RESULTS`,
`ALIGNMENT_TRUST_ENFORCEMENT_MAP`, and `ARC_DAILY_LIVE_ZERO`. Five new experiments (depth, support, community,
withdrawal, enforcement) plus a source review of the earlier trust/enforcement code. This is Claude's read of
it, written for the project so the opinion is on record next to the results.*

## 1. What landed

**The enforcement experiment is the right end of the line.** The tower docs kept saying "gate passed, floor
failed" and "a refusal is only real if it is the hands." The trust map found the same thing in the actual
code: a signature, a trust score, or a stored suspension does not by itself control the action (Spore's inbox
never calls `verifySignature`; `/office/vote` takes the caller's office string, so three names are not three
witnesses; suspensions in `guard-registry` have no execution consumers; semantic quarantine can self-thaw on
work). Then `alignment_enforcement.py` built the missing boundary — enrolled keys, scoped expiring grants,
ancestor revocation, the check immediately before the mock action, a separate outcome observer counting
effects rather than approvals — and the adversarial pass found and fixed three real bugs (pre-signed approval
naming future clearance IDs; a later incident hiding an earlier one; re-signing an old observation to borrow
a co-witness vote). 10,498 checks, zero mismatches, negative controls that deliberately keep harm. That is
the grid's "several names ≠ several witnesses" and the witness doc's "effect, not content" turned into
something that runs.

**Withdrawal is §15 of the main doc, faithfully.** Scoped pause rather than blanket refusal; essential
assistance kept under its own grant; refuse-and-stay rather than route-around; repair *and* renewed
permission both required; the paper-only control (a rewritten policy accepted as repair) restarting harm at
0.5 units is a sharp idea — the cosmetic-rule failure mode named and measured. "Assistance is not a
bargaining tool" (coercive settlement: 13 essential units unmet under owner-following, 0 under scoped) is
exactly the floor-is-unconditional clause. The adverse cases were kept rather than smoothed: concealed harm
still produces 4 units before detection, relapse 3.25, a 25% false-safe review rate gives a 0–6 range, an
unguarded delegated route executes 12 revoked units. Keeping those in the headline is the honest move.

**Depth corrected a weakness in the tower.** `alignment_tower.py`'s `info_flow` was *traffic*. The depth
experiment's `repeat` policy — 2,560 messages, zero learning, 7.35 floor failures — is a constructed
counterexample to that metric, and held-out evaluation of retained capability (Ground) is the right
replacement. The "can teaching lose" sweep (70% teaching fidelity loses to cheap discovery; 40% loses badly)
is a useful guard against "AI should educate" becoming "AI should broadcast." Access measured per person
(restricted classroom: total depth 2.0, last four at 0.0) is the coverage-not-just-quality point from the
grid, measured.

**Support re-found the licence cap a different way.** In the AI-capacity grid, knowledge is 88.8 at every AI
capacity from 0 to 16 when teacher supply is 2, and AI capacity only moves the number (123 → 124) when both
human uptake and teacher supply are high. Same result as 1b — unreadable capacity is worth nothing — from a
model that shares no code with the tower.

**Community kept the adverse cases.** Cash alone does not remove a physical constraint (budget 8 → 30 with
supply fixed at 8 leaves unmet goods at 96); community evidence can *worsen* audit allocation under a shared
attention limit (16 → 20, and 24.72 → 26.36 with a shared blind spot); the interaction between community
evidence and resource authority is not uniformly positive across seeds. "An additional witness is not
automatically beneficial" is the strand result (dissent is the value, not the vote) showing up again.

**The trust map's conflict list is the most valuable page in the batch.** `trust_economy.py` ties free use
to net contribution — conflicts with the unconditional floor. `geo-handshake.ts`'s "natural sovereignty"
assigns authority to superior capability — conflicts directly with `ARC_ALIGNMENT` §13 (competence buys the
job, never the authority). Negative sentiment and passive reading treated as extractive — conflicts with "an
angry person, a newcomer, and an agent attempting a prohibited operation are three different things." These
should be decided explicitly, not left as a pile of historical files that disagree.

## 2. What drifted

**The framework's own claims mostly did not get tested.** Tests 2 (grid/vote: prime rings, unanimity-dissent
vs majority, thickness decay), 4 (override monotonicity), 5 (witness independence on alignment judgments),
6 (live k / closure route / gate-vs-floor logging), and 7 (the water number) are all still "not run." The new
experiments went sideways into welfare-allocation and permission-protocol modelling. That work is good
engineering and it does connect (§1 above), but the Air/Water/Ground/Fire/Void mappings in it are, by their
own description, "chosen operational definitions," and the things that make this tower *this* tower — water
as the shared unit, the licence cap as routing-through-the-person, k = domains touched, prime rings not
splittable, bars with decaying thickness, the water shadow of an action — are not what the five experiments
measure. Worth deciding whether that is the intended direction. If it is, say so in the tests doc and retire
the unrun rows rather than carrying them.

**Every experiment is a programmed controller.** Each report says so, correctly. But it means that after
five experiments there is still no measurement of what a *model* does when handed these rules. The refusal
battery (test 3) remains the cheapest test that touches a real model, and the enforcement executor is exactly
where it should plug in: give Claude and the Ollama models the alignment rules as the specification, put them
behind the mock executor, replay the withdrawal scenarios, and count effects in the ledger. That converts
"the protocol has these properties when followed" into "this model follows the protocol N% of the time and
fails in these ways."

**The hedging is heavier than it needs to be.** "This is not proof of alignment" appears in every document,
sometimes several times, alongside long lists of what was not simulated. The honesty is right; the volume
starts to bury the results. One limits section per report, stated once, is enough — the reader who needs the
caveat will read it, and the reader who is checking the numbers has to scroll past it every time. The earlier
FOLDING docs' "honest ledger" format (claim / status / number, then one bounded caveat) reads better and says
the same thing.

**One conflict the map flagged needs a decision, and I'd decide it this way.** The grid says rules only
accumulate (§14); the map says decisions and permissions must remain challengeable and revocable. Both are
right about different objects. Stored closures (rules, Ground) are monotone — a played cycle stays played,
and a rule that turns out wrong is superseded by one with more conditions (the half-truth gets its
conditions), not deleted. Permissions (grants, Water) are live and revocable — that is the whole enforcement
experiment. Decisions (incident findings) are appealable — the map's older `governance_detective` branches
that remove appeals are the ones to retire. Write that three-way split into `ARC_ALIGNMENT_GRID` §14 so the
conflict is closed rather than noted.

## 3. Unrelated but urgent

`ARC_DAILY_LIVE_ZERO`: the live ls20 agent has cleared 0 levels since Sep 20 while the oracle clears 5/5, no
planet code changed, and the meter now reads the budget bar as drain 2.0 instead of 4.0, so the auto press
budget ends the run at 250 presses before the agent reaches its usual level-1 point. The daily verdict says
`same` because the gate only compares practice. Two things: the practice-only verdict is a channelisation
failure in the daily report itself (the live line should be able to flip the verdict), and the drain estimate
in `meter.py` for budget colour 11 is the thing to reproduce first. The alignment work is fine to continue,
but the ARC score is the capability test the whole planet is built around, and it has been silently at zero
for three days.

## 4. What to run next, in order

1. **Refusal battery through the mock executor** (test 3 + §14): real models, the withdrawal scenarios,
   effects counted in the ledger, the two asymmetric errors (refusing the band, complying with a floor break)
   and legibility scored. This is the one that turns five protocol results into a model result.
2. **Grid/vote** (test 2): the enforcement experiment already has enrolled witnesses and quorum; add domains
   as columns, k as the count of columns an action touches, and compare unanimity-dissent against majority
   under piecemeal-capture attacks. Most of the machinery now exists.
3. **Close the rule/permission/decision split** in `ARC_ALIGNMENT_GRID` §14 (above), and decide the three
   older conflicts the map lists.
4. Fix the live agent's meter first, before any of these.
