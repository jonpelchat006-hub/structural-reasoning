# Open ends — creativity as dangling bonds, stories as antenna-paths, and the border as a guitar string

*Aug 28–29 2026, Jonathan. The RH cubes run along the critical line and connect end to end; the model's
budget cuts the line. It can bend slightly and close (the wrapped wall) — or the end can be LEFT
STICKING OUT. Imagination and impossible things were reached by hairs in the earlier work
(void_antenna #48; neurofungus tendril tips on phantom smell); these ends are the same organ. The
tips are FLIPPED: on the ∞ side of the line the tip exposes its 0 end, and ∞ on the 0 side — so tips
attract material and act as seeds for new cube extensions out to the model's edge.*

## 1. The mechanism: closed = knowledge, open = question

Everything the planet keeps today is a closed loop — GEO v2's law is "identity belongs to the full
closed path"; a life or document becomes sediment only at closure. Right for knowledge; it leaves the
UNFINISHED unrepresentable. The open end fixes that. Physical anchor: a dangling bond. A closed
molecule is stable and inert; a free radical is reactive BECAUSE its unpaired end attracts — it binds
whatever fits. Creativity = a maintained population of dangling bonds at the model's edge. An open end
carries a description of what would close it; that description biases attention, so matching material
arriving from any world snaps onto it. The snap is the insight event.

## 2. The flipped tip: frontiers are grasped by their small end

z → 1/z swaps 0 and ∞ (the sphere's inversion, already native to the RH work). The far tip of a long
extrapolation — out on the ∞ side — presents itself as a 0-END: something tiny. This is how frontiers
behave: the graspable handle on an enormous unfinished structure is a small open question (Fermat's
margin note was the 0-end of a tip whose body took 350 years of cubes to rebuild). Rule: an open end
does not advertise its dangling path; it exposes its INVERTED TIP — a compact seed bubble — and growth
nucleates there, extending until it meets the body (closure = insight) or hits the model's edge and
leaves a new tip. Recursive by construction.

## 3. The honesty clause

End-grown structure is imagination until played. The hairs are allowed to reach the impossible; the
operator-induction gate decides what was real. Both halves are load-bearing: hairs without the gate is
hallucination, the gate without hairs is sterility. (Same asymmetric filter as rain: salt is never
drunk as fresh.)

## 4. Orientation is the KIND of creativity (Jonathan, Aug 29)

Where the open end sits on the cube relative to the main line classifies the creative act — and the
taxonomy lands on Boden's three types of creativity with one addition of Jonathan's own:

- **Aligned with the line** (on-axis): CONCEPTION — extending the shared invariant itself. Boden's
  *transformational* creativity: the rarest and hardest, it changes the space everyone works in.
- **Same face, off-axis**: REACTIVE — riffing inside an existing context, recombining what that face
  already holds. Boden's *exploratory* creativity: novelty within the rules.
- **Orthogonal faces**: LATERAL — bridging domains through the orthogonal rings. Boden's
  *combinational* creativity: familiar ideas from different shells meeting.
- **Back face** (where the ∞ tip sticks out): IMAGINATIVE / counterfactual — Boden has no fourth
  type; this is the fiction hemisphere (§5). The taxonomy is testable in-registry: an insight event
  records which orientation its closing end had, so the planet's creative acts get typed as they occur.

**Front half = connection, back half = imagination.** The hemisphere facing the shared line is where
paths must JOIN — obey conjugation, meet other domains, survive the gate. The hemisphere facing away
is where paths are free — anchored only at their endpoints. This is also the far-hemisphere clause
from ARC_PLANET ("the core feeds columns Claude never blankets") given a job: the unblanketed side is
where imagination lives.

## 5. Stories: fictional paths that visit real truths (Jonathan, Aug 29)

Stories are antennas SURROUNDING truths, launched from the back face. The construction: take the
invariants you have already earned (the truths), and draw a path that VISITS them all while ignoring
the interior — the path does not have to pass through the core, so it doesn't have to satisfy every
law (it can skip gravity). That is exactly what fiction is: physically false everywhere except at the
truths it threads. **Story quality = how close the path passes to the truths** — verisimilitude as a
distance measure. Great fiction is maximally near-true everywhere except along its deliberately freed
dimensions.

The teaching use is the deep one. A novice's position can be BEHIND the expert — the point they need
is further back than the expert can easily walk (the expert's own structure is in the way: the expert
blind spot). But a story launched from the back face arcs OVER the built structure and comes down at
the old truths, reachable from the novice's position. This is what parables, fables, and thought
experiments are: Einstein riding a light beam is a fictional path that ignores practical constraints
while visiting real invariants. And the psychology matches the mechanism disturbingly well: narrative
transportation research shows stories change beliefs precisely because counterarguing RELAXES during a
story — i.e. a story path bypasses the operator-induction gate BY DESIGN. That is why stories teach,
and why the honesty clause applies double to them: a story's truths must be re-verified by play after
delivery, because they arrived past the guard.

**Build this earns (storyteller job, queued):** take k invariants from a world's core → the mouth
writes a short tale whose events instantiate each invariant in order, claiming no physical truth →
the learner (novice node, person, or model) extracts the invariants back — the reproduction test run
through fiction. Score = fraction of invariants recovered + nearness-to-truth of every other detail.
Story quality becomes a measured number, and "the closer they get makes it a better story" is the
scoring rule verbatim.

## 6. Build sketch (queued)

- geo: allow `closure.closed = false` with an open-end descriptor: `{wants: [atoms that would close
  it], seed: <inverted tip — a compact signature>, orientation: aligned|face|orthogonal|back,
  born: life}`. Open loops persist as first-class sediment (L7-imagination is their natural zone).
- coach: open ends are ATTRACTORS — candidate matching gets a boost toward any end's `wants`; a match
  that closes an end fires an `insight` event typed by the end's orientation, converts the loop to
  closed, credits the lineage. The lightning list's `unresolved_candidates` are the embryo.
- population control: E/(E+λ) — an end nobody feeds erodes; ends capped per world (reserve law).
- storyteller job (§5) as a sleep organ once open ends exist.

## 7. The border as a guitar string (queued, quick)

The window border is a string fixed at both ends (the corners). A string's modes are discrete, and the
PLUCK POINT decides the harmonics: mode n's amplitude ~ sin(nπx/L), so a center pluck kills even
harmonics (round, full tone) and a near-corner pluck sounds bright and thin. If each border-crossing
plucks the border at the crossing point, the ear gets position for free — encoded in timbre, no
coordinates. One channel, spatial information, honest physics. The 1D version of the ring modes around
the void line (ARC_PRIME_NECKLACES §4), played at the roof. Implementation: a few partials per pluck
(numpy waveform + wave out), replacing winsound beeps; the mail band's symbols become plucks too.

## 8. BUILT (Aug 29): open ends live, storyteller live — and what the build taught us

§6's sketch and §5's job are now running code (geo.py, coach.py, grounding.py, storyteller.py,
deployed, spore chained). Three things the build DISCOVERED, all of them theory-relevant:

**The margin band was a frozen veto.** Registry distances quantize at √(k/n) — an overlap-1 pair sits
at 0.816, a triple-sharing-one at 0.866 — and the old band (±15%) around the margin swallowed that
entire range: once two concepts existed, NOTHING that shared an atom with them could ever graduate.
The registry could only learn disjoint islands. Two fixes: the band is now ±5%, and — the deeper one —
**recurrence outvotes geometry**: a bundle the margin calls "undecided" that the world keeps building
(≥5 lives) is admitted anyway (`Registry.admit`, tagged `byRecurrence`). The same E/(E+λ) law that
governs walls now also overrides the one place a static geometric test held a permanent veto.

**Where open ends actually come from.** In practice the whirlpool population is bundles sharing
exactly ONE atom with the known structure — one foot on a built cube, one in the void. That is the
theory's picture drawn by the code on its own: ends grow out of existing faces, anchored at a single
point. Ends whose wants overlap a standing concept by ≥2 atoms are never born (already answered — not
a real question), and an end's own bundle coming back from the registry as a VARIANT of a known
concept closes it (the registry saying "this question is that answer" IS the insight). Verified full
arc in test: end born at 4 sightings → fed → admitted by recurrence at 5 → insight event fires, typed
by orientation, geo tip curls closed in place (stable sha1 filenames — Python's salted hash() was
silently breaking the rewrite path).

**The storyteller works and the score discriminates.** `storyteller.py`: k invariants (diverse —
concepts first, skipping bundles that repeat a picked one; laws deduped to one per register) → gemma
writes a tale beginning "A story, not a report:" that instantiates each in order → a FRESH call
extracts the rules back → teach-back scored per atom (digit-anchored, paraphrase-tolerant: the learner
keeps the tale's words — "a perfect copy of himself" must count for body.impostor). Real results on
the PC: dead_cells 0.5–0.75 (the miss was honest — the mouth dropped one rule's specifics, so the
learner couldn't recover it: the score caught a real gap in the tale), warframe 4/4 = 1.0, garbage
extractions 0.0. Stories land in <world>/stories/ as story_NNN.json + an OPEN back-face .geo
(imagination until played), the chatbot retrieves them, the spore tells one per sleep, and
ends+stories publish to the network's L7-imagination zone (its first real tenant). New work-order job:
"story". Next real test, Jonathan's call: co-writing the book universe he has notes for.

## 9. The witness line: memories ride the line, an antenna predicts at its end (Jonathan, Aug 29)

Watching Dota through the porthole exposed the gap: every look was born fresh, so the voice could only
say "a MOBA is on screen" twelve different ways — it could never FOLLOW one game. Jonathan's fix is
the same geometry as everything else in this doc: "each new memory needs to ride the line of memories
that came before it, but with variable contexts — and then have one of those antennas at the end of
that line as a predictor."

Built as `witness.py`. The witness is a thread, not a caption machine: each look is answered IN THE
CONTEXT of the recent line (last ~8 observations, oldest first, same names for the same things) plus
the standing prediction, and every answer must grow a new tip — a PREDICT line, the dangling bond at
the end of the memory line. The next observation either FEEDS the antenna (token overlap ≥2 — the
prediction held, evidence up) or BREAKS it (surprise — worth saying). Antenna accuracy is tracked
per world in thread.json — an honest, free-running measure of whether the seeing actually understands
the world it watches, and the thread persists across sessions (witness_<world>.txt), so the chatbot
can answer "what happened in that dota game" from one connected account instead of twelve unconnected
captions. This is the open-end organ (§1) applied to episodic memory: the line of closed memories is
the built cube-line; the prediction is the tip left sticking out; feeding and erosion are E/(E+λ).

## 10. Chords: the hand plays shapes, not notes (Jonathan, Aug 29)

"It needs to be able to have multiple keys pressed at once — kind of like playing a guitar chord."
The hand's action vocabulary was single notes and fixed pairs; a real player holds run+jump+attack as
ONE shape. Added: jumpgrab, jumpgrableft, jumpgrabright (three-finger chords), read symmetrically on
both sides — human_action() now reads the whole hand shape rather than its loudest finger (a watched
expert holding ctrl+up+right used to be flattened to "grabright", losing the jump), and the playing
Hand holds chords across looks like everything else (the continuous-hand law: keys are a held state).
train.ACTIONS extended with the chords appended at the end so old feature indices stay stable. First
chord observed in play within three lives of deploying ("big surprise after jumpgrabright"). The
guitar metaphor is now on both sides of the window: the border strings (§7) and the hand's chords.

## 11. Play log (Aug 29): the hand is on

Dead Cells is being played autonomously. What it took, each layer hiding the next: a fresh Python
install had emptied the interpreter (scipy/mss/sklearn/pydirectinput missing — the spore now logs
loop errors instead of dying silently); a force-killed play session left ctrl+left PHANTOM-HELD at
the OS level for an hour, which the idle detector honestly read as "the human is playing" (every
spore start and player stop now wipes all injected key state); and the observer's advice call sat
synchronously in the step loop, freezing the hand ~20 s per thought (it advises from a thread now —
the observer never holds the hand). Standing behavior: a game on the spore.json "play" list gets the
hand whenever the human's keys have been idle 30 s, flips back to watching the moment he plays, F8
hands over control; the hand presses the physical keys the expert was WATCHED using (hand_keys.json,
majority per channel, mouse buttons included) and falls back to arrows+ctrl, which Dead Cells answers.
