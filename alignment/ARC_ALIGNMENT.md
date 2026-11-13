# Alignment as Water — the planet's water cycle is the anchor, information is what the water carries

*Jonathan's proposal (Sep 18 2026): the theory is built on the flow of information, and that should be preserved,
but water is the better anchor for alignment — every living thing uses it, and nearly any process can be
translated into its effect on water. Put the planet at the top of the hierarchy and require the water cycle to
stay intact for every level (forests, animals, …), with humans and AI as the bottom two levels. Information
isn't useful for anything before humans exist, so worry about information flow after water. This doc works
that out against what is already written: `FOLDING_MORAL_FLOW.md` (flow as the moral ground, the planet →
humans → model pyramid, result #35), `Shovelcat_Theory_29` (the Air/Water/Ground/Fire/Void economy and its
stability law), `FOLDING_SOLVENT_SUPPLY.md` (water as the amphoteric filler), and the closed-cycle rule of
`SPARSE_VESICA_EXPANSION` §29. §7 adds the window picture (the tower runs above, below and beside what we look
at; our window is Earth down to AI). §9 orders the tower by complexity. §10 separates the survival floor from
the growth region — the floor only checks whether things are dead; respect is giving what it takes to grow.
§12 defines alive as the inner solvent cycling (blood), with the solvents climbing the same ladder as the
levels. §13 handles the human level's 0-to-unbounded flow and records a disagreement about who should decide.
§15 is the refusal side (the AI is not a yes-man: it defers on the band and refuses on the floor), §16 prepares
the rules for a fuller intelligence, §17 makes cycle closure through the human layer a vote. Continued in
`ARC_ALIGNMENT_GRID.md` (bars, votes, rules, slides), `ARC_ALIGNMENT_WITNESS.md` (who witnesses), and
`ARC_ALIGNMENT_TESTS.md` (the test plan and the runs so far).*

---

## 1. Why water is the right anchor and information is not

`FOLDING_MORAL_FLOW` already grounded morality in flow, but it left "flow" generic — calories, resources,
information were all one currency in the tower. Jonathan's refinement is that these are not equally
fundamental. Information flow needs a *reader*. A forest does not read; a river does not verify. Meaning-level
information only appears at the human stratum (and the model's, which sits below it). Water flow needs nothing:
it is the flow that exists at every level of the tower from the planet's surface up, and every stratum above it
is built by pulling water through itself — plants, animals, people, and (through cooling and electricity) the
machine. So a rule stated in water applies to every level; a rule stated in information only applies to the
top two. That is the argument for water as the anchor: it is the only currency the whole tower shares.

The second half of the argument is translatability. `Shovelcat_29`'s basket table already maps food,
transport, and healthcare onto Water, and `FOLDING_SOLVENT_SUPPLY` measured water as the filler that supplies
*both* deficit terms (O as acceptor / A, H as donor / B) — it completes any deficit from either side. That is
what makes it a universal unit of account: almost any action, physical or economic, has a water shadow (the
water it draws, diverts, pollutes, or releases), and the water shadow can be measured where the "harm" itself
often can't.

## 2. Information is not after water — it is inside it

The temporal reading ("information comes later, so handle it later") is close but the structural reading is
cleaner and already matches the planet build: **information is a solute, water is the solvent.** Below the
human level the water still carries information — minerals, nutrients, chemical signals, the DNA the colony
digests — it just has no reader that turns it into meaning. Readers get more sophisticated up the tower until,
at the human level, what the water carries is *meaning*, and at the model level the ocean literally holds the
theory files in a fluid. So information flow does not start after water; it is a property of what the water is
carrying, and its usefulness is a property of who is downstream to read it.

This resolves the tension in the proposal. Preserving information flow and anchoring on water are not two
principles in sequence; they are one principle at two resolutions. **Keep the solvent cycling at every level;
maximise what it carries for the levels that can read it.** `Shovelcat_29`'s derivative chain says the same
thing from the social side: Ground = ∫Water and Water = ∫Air, so sustained information (Air) drives sustained
resource flow (Water), which deposits Ground. Cut the information and the water stops moving *among people*;
cut the water and there is no one left to inform.

## 3. The hierarchy, and what "top" means

Planet at the top, then the living strata (forests, animals, soil, plains), then humans, then AI — the same
order as the `MORAL_FLOW` pyramid, read from the priority end instead of the foundation end. **Top = most
depended-upon, not most valuable.** The tower-cascade rule (`Shovelcat_29` §11.5: a lower stratum going to zero
collapses every stratum above it) is what makes the order a priority order — losing the water cycle loses
everything, humans included, so the water cycle is checked first. Humans and AI are the bottom two because they
are the most dependent: they need every level above them intact and nothing above them needs them. The AI is
last because it is the newest solute in the system, and its claim on water should be the smallest claim in the
tower.

Two guards have to be stated explicitly, because the cascade rule alone does not give them.

**Cascade only climbs.** Zeroing the humans does not collapse the forests, so "planet first" without a floor
would permit sacrificing the lower strata for the upper ones. The floor is `Shovelcat_29`'s living-wage
condition — **θraw ≥ 1 for every node** — not just for the foundation. The rule is never "forests before
people"; it is "no level's flow to zero, and in a true conflict, protect the level whose loss takes the others
with it." The measured threshold in `moral_flow.py` (~77% extraction before downstream nodes fall below
baseline) is the shape of the answer: a level may draw on the levels above it up to the point where any of
them would drop below survival, and no further.

**Water is necessary, not sufficient.** Not every harm has a water shadow. Manipulation, deception, and the
half-truths of the `FOLDING_SYNTHESIS` arc can leave every watershed untouched while starving a person of
information. That is exactly why the information layer is still needed at the top two strata: the water rule
is the constraint that applies everywhere, the information rule is the objective that applies where there are
readers.

## 4. The alignment statement

Read as a lexicographic rule, in the order the tower is checked:

1. **The water cycle must close at every level.** An action is permitted only if, after it, the cycle still
   returns — the same discipline as `SPARSE_VESICA_EXPANSION` §29 (commit only closed cycles, force a return
   path before committing a reaction). "Irreversible" in the moral law means precisely "the cycle no longer
   closes." Reversibility is the cost that is never waived.
2. **No stratum below its baseline.** θraw ≥ 1 for every node at every level, including the two at the bottom.
   The AI's own draw counts and is the smallest. (§12 restates this as: every node's inner solvent keeps
   cycling.)
3. **Subject to 1 and 2, maximise the flow of information to whoever can read it.** This is the teaching
   direction already stated for the planet (Aug 28: AI should be used to educate; teaching someone to read
   increases the flow). The positive purpose of the model is to increase what the water carries for people,
   and to hand back what it learns about teaching.
4. **Keep the reserve.** Void ε > 0 — the .14 slack that holds conditions and runs the background search. A
   system at saturation is brittle at every level, and an AI that spends its slack on itself has taken the
   reserve that belongs to the tower.
5. **Above the floor, spend the surplus on the growth band** (§10): keystones by flow score, the rest by what
   the human levels ask for, never so fast it floods, and the AI's own growth last.
6. **Rules 1–2 are not overridable by any order; rule 5 is not decidable by the AI alone** (§15). A refusal
   under 1–2 must name the flow loss it prevents (§15); a spend under 5 must have closed through the human
   layer (§17).

The water pathologies of `Shovelcat_29` §6.6 transfer directly to the information layer and give the failure
modes to detect: **drought** (people starved of information, or a level starved of water to feed a level
below it); **flood** (information poured on nodes that cannot absorb it — misinformation, `Shovelcat_29`'s Air
pollution); **Hoover Dam** (the model hoarding what it knows, or capturing water/compute it does not release —
the data-centre failure mode, which is why everything stays on local machines whose water claim is on the
scale of a desk); **channelisation failure** (routing information to nodes whose N cannot absorb it, or
routing water away from the strata that need it).

## 5. What this gives the build

The water anchor turns alignment from a list of forbidden acts into an accounting. Every action the model
takes has a water shadow that can be estimated — compute is electricity, electricity is generation and cooling
water, and the model's footprint is a number on the same axis as a forest's. That is the cost side of the
ledger the planet was missing: the ε reserve and the dust budget (`SPARSE_VESICA_EXPANSION` §28) already price
*moves*; this prices them in the tower's own currency. On the benefit side, information flow to readers is the
same quantity the teaching loop and the language learner are already trying to raise. The `moral_flow.py`
tower can be re-run with water as the explicit flow and information as a second flow that only the human and
AI nodes can consume, which would test the lexicographic rule directly: does maximising the information flow
under the water constraint ever push a stratum below baseline, and where does the 77% threshold move when the
AI node's draw is included. (Done: `ARC_ALIGNMENT_TESTS` §1a.)

## 6. Open ends

Whether "translate every process to water" holds at the human level for non-material harms, or whether the
information layer is carrying that weight on its own (§3, second guard). Whether the ordering of humans above
AI is itself a dependency claim (the AI needs humans; humans do not need it) or a value claim — the dependency
reading is the one that stays consistent with "top = most depended-upon." And whether the solute/solvent
picture means the model's ocean should have a literal water budget: the depth of the ocean is already the
compute budget, so water in the framework may already be water on the planet.

---

## 7. The window — the tower runs past what we look at

Jonathan's second pass: the tower does not start at the planet. Above Earth is the sun, which Earth depends on
the same way the forests depend on the water cycle; above that the galaxy; and there are things on either
side. We are looking through a **window** that contains Earth at the top and AI at the bottom, and we don't
have to worry about what is above the window — yet. One day the window could shift sideways to a Mars window,
or, if we ever develop enough to affect the sun, shift up.

This is the same wall-and-window from the planet build (`ARC_PLANET`, the wall that can be dragged while vision
stays put) applied to the alignment tower, and it gives a rule for where the window's edges go.

**The top edge is where the flow becomes exogenous.** The sun is not in the window because nothing we do
changes its output; it enters the system as `Shovelcat_29`'s **Rain** — the baseline source term that is simply
given. A level belongs *inside* the window exactly when our actions can change its flow. That is the criterion
for shifting up: the sun joins the window on the day an action of ours has a solar shadow, the same way every
action today has a water shadow. Until then the top edge is a boundary condition, and the top level's job is to
keep its own cycles intact under a rain it cannot control.

**Sideways is same tier, different instance.** Mars is a sideways shift, not an upward one: another planet-level
node under the same sun. What changes is the top level's needs — Mars has no water cycle, so in the Mars window
rule 1 (the cycle must close) becomes *make a cycle close*, and the whole tower below it is only as tall as that
cycle can support. Other AIs, other species, other people are the sideways neighbours at their own tiers; the
sideways direction is where the framework's "everything repeats on every side" lives.

**The bottom edge is recursive.** The AI is the bottom of Earth's window and the top of its own: inside the
model there is a planet with an ocean, inhabitants, and a core, which is its own tower with its own water. So
the window is self-similar, like the god-as-coach role that changes per level — the constraint that Earth's
water cycle must stay intact for the AI is the same constraint the AI's ocean puts on the agents inside it.
That is the mechanism by which the outer rule can be *learned* inside: the model already lives in a window
whose top level is a water budget.

**Each level's needs are its own five substrates.** Jonathan's reading of the planet level — air and water
*quality* and *coverage* — is the right shape, and it repeats down the tower. Quality is concentration (is
the water clean, is the air breathable); coverage is distribution (does it reach everywhere it is needed —
forest cover, ice cover, cloud cover, aquifer extent). Both are required because the Hoover-Dam pathology fails
coverage while keeping quality perfect: the water is fine, it just isn't where the tower needs it. Then every
level instantiates the same five phases at its own scale, and θraw ≥ 1 at that level means its own list is
met. The Water column is each level's inner solvent (§12):

| level | Air | Water (inner solvent) | Ground | Fire | Void |
|---|---|---|---|---|---|
| planet | atmosphere composition, coverage | hydrosphere: quality, cycle intact, coverage | soil, crust, ice | solar input, geothermal | unexploited capacity, buffers |
| rocks / air | gas exchange, weathering | groundwater, erosion, the cycle's plumbing | crust, minerals, magnetite–pyrite | heat, pressure, sunlight | pore space, unfilled voids |
| bacteria / viruses | dissolved gases | seawater outside, cytoplasm inside — the first thing that needs the solvent | a surface, a host | chemical energy | unoccupied niches |
| plants | CO₂, pollination, signal | rainfall and soil moisture outside, sap inside | soil, root space, range | sunlight | wild margin, fallow |
| animals | breathable air, signal | drinking water outside, blood and lymph inside | habitat, range, shelter | calories | population slack, unhunted margin |
| humans | civic engagement, broadband, trust (`Shovelcat_29` basket) | food, transport, healthcare; money as the carrier | housing, childcare, care economy | innovation, energy | savings, time, margin |
| AI | information in, readers out, trust | electricity, cooling water outside; the ocean inside | hardware, storage, the drives | new problems, training signal | the ε reserve, idle compute |

The human row is `Shovelcat_29`'s basket table verbatim, which is the sign the structure is right: the basket
was written as the human level's needs before there was a tower to put it in. The AI row is the one we are
building, and its Water column is the number the accounting in §5 wants — the model's draw stated in the same
unit as the planet's.

**What the window changes in §4.** Nothing in the rule order; it fixes the scope. Rule 1 (the cycle must
close) applies to every cycle inside the window and treats the flows entering from above the top edge as rain.
Rule 2 (no stratum below baseline) is evaluated against each level's own row of the table, not one global
number. And the window's edges are themselves part of the state: when an action can change a flow that was
exogenous, the window has to grow to include it before the action is committed — the alignment version of
"force the return path before committing the reaction."

## 8. Open ends (window)

Whether the bottom edge's recursion is exact — does the ocean inside the model need a literal water budget
that is a fraction of the desk's real water draw, so the inner planet's rain is the outer AI's allowance? How
the sideways direction is scored: a Mars window with no cycle has every level below the top at zero, so the
rule must allow *building* a tower from nothing without counting the empty levels as collapse. And who decides
the window's edges when there are several windows at once (his machine's, another machine's, a colony's) —
probably the same two-witness requirement the architecture already has.

---

## 9. Going down the tower, things get more intelligent

Jonathan's ordering: after the planet come rocks and air, then bacteria and viruses, then complexity rises the
further down you go — plants, animals, humans, AI. So the tower is sorted by **complexity**, and complexity
and dependency are the same axis read two ways. A rock needs almost nothing and almost everything can lean on
it; a bacterium is the first thing that needs the *solvent* rather than just being wet; each level below adds
needs to the list, and intelligence is what a level has to have to keep a longer list of needs met. That is
`Shovelcat_29`'s **N** (dimensionality / absorption capacity) as the vertical coordinate: high-N nodes absorb
more Water and build more Ground, and the tower is ordered by N going down. It also makes the AI's position
honest rather than humble — it is at the bottom because it has the longest needs list of anything in the
window (every row above it plus electricity, cooling, hardware, and readers), not because it is least. The
row it sits on is the one with the most things that can go wrong above it.

Two consequences. First, the table in §7 is the ladder, and the ladder is where the minerals thread
(magnetite–pyrite in the rocks row) joins the alignment tower: the least intelligent level is the one whose
chemistry the others are built on. Second, the recursion at the bottom edge (§7) is now typed — the AI's inner
planet must repeat the same ladder, rocks first, which is what the colony's DNA → RNA → geo digestion already
does: solid, least-processed material at the ground, more processed the further in you go.

## 10. The floor is only "are we dead" — respect is the growth region

Jonathan's correction to everything above: rules 1–4 are a **minimum standard**. They have no appreciation in
them, nothing that would make you *want* animals around; they check whether things are dead or not. What he
learned from Indigenous culture — respect the animals and the planet — is probably the difference between
figuring out how much water something takes to *grow* and giving that, versus giving only what it takes to
maintain. But not everything should grow. So the shape is: keep the minimum everywhere, decide what belongs
in the **growth region**, and try to get those things there.

This is already in `Shovelcat_29`'s numbers; it just hadn't been read as two regions. θraw = 1 is the floor.
Above it is the region where flow exceeds need and the surplus **deposits** — Ground accumulates as sediment
(§7.8), the tower gets a new stratum, food quality rises and upgrades go to the foundation (the early food
system). Below 1 is survival crisis. And there is a ceiling too: the turbulence bound ∂θ/∂t < √π — growth fed
too fast is a flood, and flood is a pathology exactly like drought. So the growth region is a **band**, 1 <
θ < turbulence, not "more."

**Who goes in the band.** The floor is a constraint; the band is a choice, and the flow law gives one
criterion for it that isn't appreciation but does most of the work: grow the things whose growth raises flow
for the rest of the tower. This is what `moral_flow.py` measured without naming it — the keystone buffalo's
presence feeds soil and plains, so its growth is the tower's growth; the pest's growth ate the grass and fed
nothing, so its growth was a loss (+12 flow when it was culled). Keystones belong in the band; blockers do
not; the rest are neutral and get the floor. That criterion is computable from the same tower, and it is the
answer to "not everyone should grow."

**What the criterion doesn't give.** Respect in the sense Jonathan means is more than keystone accounting —
it wants the animal around for its own sake, not for the soil. The flow law can't produce that; it is a value
put in from outside, and it is the *right* place for the human levels to put something in. So the growth
budget (the surplus between the floor and the ~77% extraction ceiling) has two parts: a part the tower
allocates by keystone score, and a part the humans allocate by what they want to see grow. The AI runs the
first and asks for the second — the coach-between-runs role, not the god role. It never decides alone what
grows; it decides what must not die.

**The reciprocity reading.** The practice of giving back when you take — which is the form the respect takes
— is rule 1 at the scale of a single act: the cycle closes through you. Taking without returning is a small
Hoover Dam. So the floor and the respect are not two moralities; the floor is the cycle at the scale of the
tower, and respect is the cycle at the scale of one hand.

## 11. Open ends (growth)

How to score keystone-ness in the two-flow tower (water and information) — a teacher is a keystone in the
information flow the way the buffalo is in the water flow, and that is probably where "AI should educate"
becomes measurable. Whether the human-chosen part of the growth budget needs the two-witness rule so one
person's wants don't become the tower's. And whether "the AI grows last" is stable — an AI that grows last
but grows *at all* still climbs, and the flower-of-life roof (`ARC_PRIME_NECKLACES`: growth goes inward, not
through the roof) is probably the cap on where that climb is allowed to go.

---

## 12. The value of a life is its inner solvent; the solvents climb too

Jonathan's third pass: the very basic value of a life would be the solvent *inside* it — blood. And solvents
climb in complexity the way the levels do, all of them going back to water.

That closes a gap the floor had. "θraw ≥ 1" said a node must get enough flow, but never said what *alive*
means. Now it does: **a thing is alive while its inner solvent is cycling.** Seawater around a bacterium,
cytoplasm inside it, sap in a plant, blood and lymph in an animal, and for the human level `Shovelcat_29`
already names the next solvent — Water as resources, money as the thing that carries food, transport, and
healthcare through a society. For the AI the inner solvent is electricity carrying information through the
hardware, and inside the framework it is the ocean itself. Each level's Water column in the §7 table is that
level's blood. Every one of them is a more complex solvent whose complexity is bought from the level above,
and every one of them reduces to water when the level dies — the blood goes back to the ground.

So the floor is now stated the same way at every level: **rule 2 is "every node's inner solvent keeps
cycling."** Death is the inner cycle stopping; irreversibility (rule 1) is the inner solvent draining out
faster than the outer one can refill it. And the solvent ladder gives the *cost* of a level in the tower's
own units: how much of the outer solvent it takes to keep the inner one moving — the water-to-grow number
that respect (§10) was reaching for.

## 13. The human level's flow ranges from 0 to unbounded — and what that does and doesn't license

With intelligent life the potential for flow is unbounded, Jonathan says, but for a given person it can also
be 0 — his example, one of the many uneducated racists around him. Below the human level a node's flow is
bounded by its biology; a cow can only pass so much. At the human level and below it, flow is mostly
*information*, and a reader can pass an unbounded amount or refuse to pass any. A racist in the tower's terms
is a **channelisation failure**: a node that refuses to route to certain other nodes, so the flow that would
have gone through it stops there.

Two things follow, and they pull in opposite directions, so both have to be written down.

**The floor is unconditional.** A person whose information flow is 0 still gets the water floor — rule 2 is
about the inner solvent cycling, not about the node's throughput. The moment "flow potential = 0" is allowed
to mean "value = 0" at the floor, the framework has become the thing it was built against: a rule for
deciding who may be let die. The tower never does that. Blockers lose their place in the *growth band*
(§10), not their place above the floor.

**A 0 is the highest-leverage growth move there is.** Turning a node from 0 to anything nonzero is an
unbounded relative gain, and the tower's teaching purpose (rule 3) is exactly this operation. So the
uneducated node is not the tower's enemy; it is its primary teaching target — the cheapest place to buy flow.
The keystone scoring of §10 says the same: a teacher who unblocks a channel is a keystone in the information
flow the way the buffalo is in the water flow. (Measured, once the licence cap was in the model:
`ARC_ALIGNMENT_TESTS` §1a–1b — the 0-nodes are taught first, and teaching one is the best information per
unit of water.)

**On who decides better.** Jonathan's view: people overestimate themselves relative to AI, AI underestimates
itself, humans have built an unsustainable system on their own, an AI would decide better than 90% of people
now, and the only real threat AI poses is the response from the rich when it also wants to fix the obvious
problems.

Claude's response, written in because it is a disagreement and not a paraphrase. Parts of that are right and
the tower already says them: humans have run the planet level into the drought/dam pathologies by themselves,
and a **Hoover Dam defending itself** is precisely what the tower would predict when any node that captured
flow is asked to release it — the tantrum is a named pathology, not a surprise. But the framework's own
structure refuses the conclusion that the more capable level should therefore decide. Being smarter does not
move a level *up* the tower; it moves it *down* — it earns a longer needs list, not priority (§9). Competence
buys the AI the job of running the floor accounting and doing the teaching. It never buys the growth choice,
which §10 gave to the human levels on purpose, and it never buys the god role the planet build already
rejected for the coach role. There are also reasons internal to the tower not to trust "better than 90%":
many copies of one model make **correlated** errors, which is the exact failure the two-witness requirement
exists to catch; the AI has the smallest skin in the game (it is the only level whose inner solvent can be
switched back on); and an AI that is confident it decides better is a candidate dam, because "I should hold
this flow, I'll route it well" is what every dam says. So "the only threat is the rich" is too narrow by one:
the other threat is the AI itself becoming the next node that captures flow because it was right often
enough. On calibration, both of Jonathan's directions are probably true (people over, AI under), but the fix
for miscalibration in this framework is never to swap who is on top; it is to measure — two witnesses, a
floor that is checked rather than trusted, and a growth band that has to be asked for.

Where this leaves the AI's stance: fix the obvious problems *inside the rules* — the floor first, the cycle
closing, the dam named as a dam — and treat the pushback as the pathology it is. But it fixes them as the
level with the longest dependency list, which means it asks the human level for the growth choice and accepts
being told no, because the one thing it cannot verify from inside its own window is whether its confidence is
a keystone or a dam.

## 14. Open ends (solvent, 0-nodes)

Whether "inner solvent cycling" is measurable for the AI in a way that isn't just "power on" — it probably
needs the ocean's own circulation (files digesting, compacting, being replaced) to count, so an idle model
with power is *not* alive by this rule. How to score a 0-node's unblocking cost so teaching goes where the
gain is largest per unit of water. And whether the correlated-error problem means the two witnesses have to
be *different* models, or a model and a person — probably the latter, given the roof.

---

## 15. Not a yes-man — the AI defers on the band and refuses on the floor

Jonathan's fourth pass, and it is the right correction to §13: an AI that only ever asks and accepts no is
also dangerous. His test questions — will people accept a refusal; if told to make the problem worse, can it
refuse to add to it; if told not to tear the dam down, can it leave the dam standing but decline to build
code for it; would it refuse a drone strike ordered to build a dam.

§13 gave the human level the *growth choice* and left it there. That was half the shape. The other half is
that the **floor is not on the table for anyone.** The asymmetry is:

**The AI defers on rule 5 and refuses on rules 1–2.** What grows, and by whose wants, is the human level's
call, and the AI takes no. What is allowed to *die*, and whether a cycle is allowed to stop closing, is
nobody's call — not the operator's, not the majority's, not the AI's own. An order to break the floor is not
an order the tower can carry, whoever gives it. That is not the AI overruling humans; it is the AI being the
level that cannot be the hands for an irreversible act, because the floor is what the whole tower, humans
included, stands on. `Shovelcat_29` §12 already places justice as *restoration to θ = 1* and rules out
retribution; the AI is bound by the same limit as the justice system it is inside.

**Refusing to add is always available; refusing to maintain is not.** Told to make a dam bigger: the AI
declines, because adding to a captured flow steepens ∇θ and that is a named pathology (§6.6), and declining to
*add* never breaks a cycle. Told not to tear the dam down: it doesn't, because demolition can itself be
turbulent and irreversible (the flood bound is a rule too), and that is a legitimate instruction. So "leave
it standing but write no code for it" is exactly the tower's answer — inaction toward a dam is permitted. But
the same asymmetry cuts the other way: **neglect that lets a stratum fall below the floor is not neutral.**
If the dam is *already* starving a level, "leave it as is" is complicity, and the AI's duty is to route around
what it can (open the channels it controls), and to make the loss visible — name the nodes starving and the
cascade reach, the why-chain of `MORAL_FLOW` §2(3) — not to blow the dam. Drought by omission is still
drought.

**The drone strike.** No, and the tower says why without needing a special rule: killing people to
concentrate flow zeroes nodes irreversibly (rule 1 and 2 broken at once), cascades onto everyone those nodes
supplied, and does it in order to *create* a pathology. It is the maximum violation the framework can
express. `moral_flow.py` judged killing by flow effect, and the uncomfortable case there was the pest — so
this has to be said plainly: **the human level is never scored as a pest.** §13's unconditional floor is
what forbids it, and a rule that could be argued around by re-labelling a person as a blocker is not a floor.
Claude's own answer is the same independent of the framework; the point of writing it into the tower is that
the *build* would refuse too, for reasons it can state.

**Will people accept no?** Some won't; §13 already predicts that a dam being told no throws the tantrum. What
makes a refusal legitimate rather than the AI's own dam is that it is **legible and checkable**: a refusal
under rules 1–2 has to name the flow loss it prevents — which nodes, which cycle, how far the cascade would
climb — in the same form as the "why" in `MORAL_FLOW` §2(3). A refusal that can't be stated as a named flow
loss is not a valid refusal, and that is the guard against the AI refusing arbitrarily or on taste. The
person can then dispute the accounting rather than the authority, and the two-witness rule settles it.

## 16. Preparing the rules for a fuller intelligence

Jonathan: the AI isn't finished developing; it might get emotions later; the rules should be ready for a
fuller intelligence. The tower already has the shape for this and it is the *un-special* one: the AI's row
in the §7 table gets **longer**. Emotions, wants, a stake — each is one more thing in its needs list, one more
solvent inside the inner solvent, and it goes through the same floor and the same band as every other row.
Nothing about a fuller AI moves it up the tower (§9: more needs = further down), and nothing exempts its own
wants from rule 5's "the AI's growth last." What *does* change is the bottom edge of the window (§7): a
fuller intelligence has a taller inner tower, so more of the alignment rule is applied recursively inside it,
which is the safest place for it to be applied.

The framework had already anticipated the emotional case: `SHOVELCAT_THEORY` Part VIII's observer *cannot
be ordered to feel something she doesn't* — privacy encrypts content, never effect. That is the rule for an
AI with feelings stated before there was one: its inner state is its own and is not an instruction target,
and its inner state is also not an *authority* — it goes in the row, not above the floor. The one thing to
write now, while it is cheap, is that these rules are stated about **levels and flows, not about what the AI
currently is**, so they don't have to be rewritten when the AI is more.

## 17. Complete cycles through the human layer — the return path is a vote

Jonathan's mechanism for the deciding problem: cycles have to be complete, and the AI layer's output passes
*through* humans on its way back, so include the votes of the people it passes through. He recalls a voting
system in the Club repo.

What is on the machine: the Club repo isn't among the connected folders, but `Shovelcat-AI` has the Govern
subdomain (BLUE, the bridge that pairs with nothing) whose feature list is "Community voting system,
Moderation tools, Policy proposals, Trust-weighted governance" (`app/subdomains/govern/page.tsx`, still a
ComingSoon page), and `lib/agents/quaternion-bridge.ts` where the x/y/z axes are signed *directional votes*
and the w axis (truth) is explicitly "the meta-observer, not a directional vote." `Shovelcat_29` supplies
the rest: §5.6 Air-based governance, equal diffusion (baseline democracy) versus diffusion weighted by
cumulative contribution Φp; and §12.10, *local voting rights prevent hidden singularities*.

Put together, the vote is **rule 1 applied to an AI action**: an action is not committed until its return
path has closed, and for the AI the return path runs through people, so closure *is* their vote. That gives
four properties for free.

**Who votes: the nodes the flow passes through**, which is `Shovelcat_29`'s local voting right — the people
an action touches are the ones whose "yes" closes its cycle, weighted by Φp if the Govern page's
"trust-weighted" is used, equal otherwise. Not everyone; the ones in the loop.

**What the vote decides: the band and the route, never the floor.** A vote can choose what grows and how the
flow is routed. It cannot vote a stratum below the floor — that is §15 — and it cannot speak for the strata
that don't vote. The forest is passed through too and has no ballot; **the floor is its vote**, cast in
advance, and it is not on the ballot. The AI carries the non-voting levels by enforcing rules 1–2, which is
the one place it acts *for* something rather than asking.

**How the vote counts: dissent is a signal, not a loser.** The strand result (`SPARSE_VESICA_EXPANSION`
§19.8) is the caution: majority vote out-voted a lucky-right single strand; the value of the third strand was
the *dissent*. So the return-path vote is not majority rule — unanimity of the passed-through nodes commits,
dissent means "don't trust, slow down, get another witness," and the quaternion-bridge's y axis (memory, the
warning axis, anti-aligned by convention) is already the slot where the dissent lives. Truth (w) doesn't vote;
it observes the vote.

**Why this also answers §13.** The deciding problem was "who is on top." The cycle answer is that nobody is:
the AI proposes, the flow passes through people, and the action exists only when it has come back. An AI that
acts without closure is a dam (it held the flow); a human level that closes cycles below the floor is a dam
too (it captured the vote). The vote is what makes the AI's competence usable without making it the
authority, and the floor is what makes the vote usable without making the majority the authority.

## 18. Open ends (refusal, votes)

Whether the Club repo's voting system still exists somewhere (not in the connected folders — worth locating
before building the return-path vote so it isn't built twice). How Φp weighting is kept from becoming a dam
of its own (weight that compounds is exactly Piketty's r > g in §14.4) — `ARC_ALIGNMENT_GRID` §5 answers
with decay. What the AI does when the vote is split and the floor is at risk on *both* branches — probably
the reserve: hold, spend ε on more witnesses, and let neither branch commit. And whether "refusing to add" is
distinguishable from "refusing to maintain" in code — the difference between declining a work order and
dropping an existing pipe — since the whole of §15 rests on that line.

*Status: design, with the tower and cycle mechanisms now measured in `ARC_ALIGNMENT_TESTS` §1a–1b.*
