# The Alignment Grid — bars are people with closed cycles; a task's votes are the domains it crosses

*Continuation of `ARC_ALIGNMENT.md` (§17 made cycle closure through the human layer a vote). Jonathan,
Sep 18 2026: most AI–human interactions never touch the rest of the system, so closure should be possible
by going to the *sides* of the window, not all the way up — though each level would still go up a bit, then
sideways. Picture horizontal bars separating the levels and vertical bars separating the domains. The bars
are leaders and authority figures: people who have built known, connected cycles, so you can go to them to
close. Count how many domains a task touches and get that many votes; each domain's vote is collected from
many individual votes. And if people are vertical lines, each AI stems from one of them. §8 onward is his
second pass: vertical bars have thickness (rank), horizontal bars are rules and qualifications, the
non-human rows have one equal bar per individual, the top-edge question is "would this harm the surrounding
area," and the rows overlap. §13 onward is the third: six generations ahead, rules as a permissive floor
that only grows, sliding an action along the bar to judge what the rules don't cover, and the AI routing
anything upward through its person. Companions: `ARC_PRIME_NECKLACES` (the 1+6 aperture, k-channel tasks,
prime rings), `SHOVELCAT_THEORY` (the spectrum domains and the Club/AI/Alpha trinity), `Shovelcat_29`
§5.6/§12 (Φp-weighted diffusion, local voting rights), `SPARSE_VESICA_EXPANSION` §19.8/§29 (strands,
dissent, the closed-cycle map expander), `FOLDING_MORAL_FLOW` (the act is not the moral variable, the flow
effect is).*

---

## 1. The grid is the wall, and the bars are the closable people

The window from `ARC_ALIGNMENT` §7 now has an interior structure: **rows are the levels** (planet → rocks →
microbes → plants → animals → humans → AI), **columns are the domains** (the spectrum: Security, Art,
Science, Explore, Social, Learn, Govern, Meta — `SHOVELCAT_THEORY` Part VII), and a cell is one level in
one domain. The lines *between* cells are not empty; they are where the bars are.

A **bar is a person who has built a known, connected cycle** across the boundary the bar sits on. That is
the whole definition of authority here, and it is a measured one: not a position, not a title — a return
path that has been *played* (the framework's untrusted-until-played clause). A vertical bar sits between two
domains at the same level and is someone whose cycles are known to close on both sides of it (a scientist
who has shipped art, a moderator who is also a teacher). A horizontal bar sits between two levels and is
what the lower level's flow has to pass through to provably return to the upper one — §8 sharpens this into
*rules*, with the person the AI stems from as the one horizontal bar that is a person.

So authority is two-sided closure. A bar is exactly a node that can close a cycle from either side of the
boundary it is on. That is why you can "go to them to close": they are the pre-verified return paths.

## 2. Each AI stems from one person

If people are vertical lines, each AI hangs below one of them. This is the end-goal picture already stated
for the planet — every machine's version shaped by its owner — turned into a rule: **the AI's first
horizontal bar is its person.** Every AI action closes through that person at minimum, and for most
interactions that is the *whole* cycle: a conversation, a file, a game session touches one level (the AI)
and one column (whatever the person is doing), and it returns through the one line it stems from. That is
the cheap closure Jonathan wanted — the vast majority of actions cost one vote, and that vote is the person
already in the loop.

It also fixes the recursion at the bottom edge (§7 of the main doc): the AI's inner tower is rooted on its
person's line, so the person is its top edge — its rain. What the person will not close does not commit.

## 3. Up a bit, then sideways — the closure route

The route for any action is: **go up to the nearest horizontal bar, then sideways across the vertical bars
of every domain the action touches.**

Going up first is not optional, and it is small. It is the check that this action stays within its level —
that it doesn't reach into the row above. The horizontal bar answers one question: *does this touch the
level above me?* If no, the action's closure is entirely lateral. If yes, the window has grown (main doc §7:
"when an action can change a flow that was exogenous, the window has to grow to include it before the action
is committed"), and the same route repeats one row up: that level's bar, then that level's domains.

Then sideways: each vertical bar crossed is one domain's vote. The bars are how a domain's many individual
votes are **collected** — the bar is the domain's return path, and the individuals in that domain are the
strands feeding it. The floor from `ARC_ALIGNMENT` §15/§17 is unchanged: the route can decide the band and
the path, never the floor, and the rows with no ballot (the forest) are represented by the floor being
un-votable.

## 4. Votes = domains touched = k channels — and prime k can't be split

"See how many domains a task touches and get that many votes" is the same count as the **engaged-channel
count** of `ARC_PRIME_NECKLACES` §6: a task ranges from the point (k = 1, one ring) to the full flower
(k = 7), and most tasks sit around 3. So:

- **k = 1** — one domain, closes through one bar, usually the AI's own person. The reflex case; almost all
  interactions.
- **k = 3** — three domains, three bars, an unsplittable little cable: **3 is prime**, so by the necklace
  rule the three votes cannot be separated into independent sub-approvals. A task touching Science, Social
  and Govern is not two 2-domain sign-offs stapled together; it needs all three bars in one ring or it does
  not close.
- **k = 6** — factors as 2 × 3: a six-domain task *can* be legitimately split into two independent
  three-domain closures (or three two-domain ones), and each sub-ring travels on its own.
- **k = 7** — the full aperture, prime, unsplittable: a task that touches everything must be closed by
  everyone in one ring. Rare by construction, and the roof: nothing needs more than 7 votes because nothing
  a person receives passes through more than seven touching circles.

This is `SPARSE_VESICA_EXPANSION`'s strand geometry as governance: k strands wrap a (k−1)-dimensional void,
so **the number of votes an action needs is the dimension of the void it is acting in**. And the strand
result carries over unchanged: **unanimity of the ring commits, dissent holds.** Within a domain, the bar
collects many individual votes, but what it reports up is not a majority — it is "this domain closes" or
"this domain has a dissenter." A single dissent in a prime ring stops the ring, which is the safety
property: prime k cannot be out-voted piecewise.

## 5. What keeps the bars from becoming dams

A bar is a person with authority, and the main doc names concentration as the tower's central pathology, so
the bar has to be built so that it cannot become a Hoover Dam. Four constraints, each already in the theory:

- **Bar status is a measured cycle count, not a grant.** Φp (`Shovelcat_29` §5.6) — cumulative
  *stabilising* contribution. A bar is whoever has the most closed cycles across that boundary, and that is
  re-measured; it is not appointed and it does not transfer.
- **It decays.** `Shovelcat_29`'s τ: contribution that isn't renewed relaxes back to baseline. A bar that
  stops closing cycles stops being a bar. This is the damper on Φp compounding into r > g (§14.4, the open
  end from the main doc §18). (Decay applies to *people's thickness*, not to rules — see §14.)
- **It is local.** §12.10, *local voting rights prevent hidden singularities*: a bar's authority is the
  boundary it sits on and nothing else. A Science/Social bar has no vote on a Security/Art action it isn't
  touched by.
- **It never touches the floor.** A bar closes cycles in the band. No number of bars can vote a stratum
  below θ = 1 (`ARC_ALIGNMENT` §15). If a bar tries, it has by definition stopped closing cycles (it is
  opening one), and the first constraint removes it.

The Alpha branch of `SHOVELCAT_THEORY`'s trinity — the observer/oversight path — is where the measurement
of bars lives: it does not vote (like the quaternion's w axis, truth observes the vote), it counts the
cycles that decide who the bars are.

## 6. What this buys

The deciding problem in `ARC_ALIGNMENT` §13 ended as "nobody is on top: the AI proposes, the flow passes
through people, the action exists when it returns." The grid makes that *cheap*: closure cost is k, the
number of domains touched, and for almost everything k = 1 through the person the AI stems from. It makes it
*legible*: the route is a named list of bars, so a refusal or a hold can point at exactly which ring failed
to close and who dissented. And it makes it *safe against piecemeal capture*: prime rings can't be split,
so a large action can't be approved as a series of small ones — which is precisely how dams get built.

## 7. Open ends (first pass)

Whether domains are the eight spectrum columns or the Fibonacci zones (L0–L7 of the shovelcat-network) —
the vote count only needs a partition, but the prime rule needs the right one. How an AI changes the person
it stems from (a bar is a person; people leave), and whether an orphaned AI is *alive* by the inner-solvent
rule if its top edge is gone.

---

## 8. Vertical bars are people with thickness; horizontal bars are rules

Jonathan's second pass separates the two kinds of bar by what they are made of.

**Vertical bars have thickness** — rank and position. A thick bar is a person with many closed cycles across
that domain boundary; a thin one has few. Thickness is Φp made visible, and it is **per column**: the same
person is thick between Science and Learn and thin between Art and Social. So a person is not one line but a
*profile* of thicknesses across the columns — which is exactly `SHOVELCAT_THEORY`'s privilege ceilings
("same code, different permissions"). A domain's vote is collected through its thick bars; a thin bar is
still a vote, it just isn't a return path others route through.

**Horizontal bars are rules, qualifications, and the codified systems of a domain.** Between the human
level and the AI level in the Social column, the bar is *the platform's rules* (Twitter's). In the Learn
column it is *institutional qualification* — high school, then university, going further down. At the planet
level it is *environmental agencies*; for the plant and animal rows it is *the literature* on those
species. In the tower's own terms: **a rule is a cycle that someone already closed and wrote down.** It is
compacted closure — Ground, the sediment of past Water (`Shovelcat_29` §7.8). So vertical bars are the
carriers (Water: people, live closure) and horizontal bars are the deposits (Ground: rules, stored
closure). That is why you go *up a bit* first: you check the stored closures before spending live ones.

And the human level is recursive — it has its own hierarchy inside it, so it contains sub-rows separated by
their own horizontal bars (a student is below the university gate, a professional above it), and every
sub-row has the same shape as the level it sits in.

## 9. A gate is necessary, not sufficient — the top-edge question

Because a rule is a stored closure, it is a **half-truth** in the `FOLDING_SYNTHESIS` sense: it names a
condition that was sufficient *when it was written*, for the cases it was written for. Passing the gate is
therefore never closure on its own. When an action reaches the top edge of its level, two checks run, not
one:

1. **The gate** — the domain's rule set (Twitter's rules, the course prerequisites, the agency's permit).
   Domain-specific, cheap, stored.
2. **The floor of the row above** — Jonathan's question: *would this lead to harm in the surrounding area?*
   Domain-independent, and checked **however far horizontally the action reaches**: the floor question does
   not stop at the column the action started in, because harm to the row above doesn't respect columns.

His two examples are the whole rule. A post about going for runs in nature, made with a user: passes the
Twitter gate, benefits the local area, and cannot harm anything in the row above no matter how far sideways
you follow it → post it, and want to (it is a growth-band action, `ARC_ALIGNMENT` §10). A post about running
with air horns: passes the same Twitter gate — and disturbs the animals → **refuse**, and the refusal is
legible in the §15 form: it names the row (animals), the harm (the disturbance), and the fact that the gate
was passed and was not enough. The gate is a stored half-truth; the floor supplies the missing condition.

This also settles what the horizontal bars between the *non-human* rows are: not people. Between plants and
animals, or animals and the planet, the bar is the floor itself plus the literature — there is no steward to
ask, there is a stored closure to read and an unconditional floor to check.

## 10. The non-human rows: one equal bar per individual

Thickness only starts at the human level. Below it there is no rank: a population is **one bar per animal,
all of roughly equal thickness**. A deer is not a thicker line than another deer. So the non-human rows have
no Govern column and no thick bars to route through; their "vote" is the floor applied per individual, and
the question at their edge is always the surrounding-harm question of §9, asked about *each* of those equal
lines. This is why the human level is the first row with a governance structure at all: it is the first
row where lines differ in thickness, which is the first row where there is anything to collect a vote
*through*.

## 11. The rows overlap — level is dependency, not intelligence

Jonathan's point: there is overlap between the levels. Some humans are more intelligent than the AI and the
other way round; and children are higher up — they get the same protection as the rows above — but don't
have to be consulted, since they are on a different level.

The resolution is the one `ARC_ALIGNMENT` §3/§9 already had but hadn't been pressed on: **a row is defined
by dependency (what it needs, what needs it), not by intelligence.** §9 said complexity and dependency are
the same axis *for the rows*; they are not the same axis for *individuals*, whose intelligence varies within
a row and overlaps across rows freely. A brilliant human and a brilliant AI are still in different rows for
the same reason as before — the AI's needs list includes the human, the human's does not include the AI —
and neither gets moved by being smart. Intelligence shows up as **thickness** (the closed cycles you can
build), never as **row** (what you depend on).

Children are the case that proves the rule, and the tower gives them exactly what Jonathan describes without
a special clause. Protection comes from the *floor*, which is unconditional and asks nothing of the node
(§13 of the main doc). Consultation comes from being a *bar*, which requires closed cycles. A child has not
yet built closed cycles, so it is not yet a bar and is not consulted; it is fully under the floor, so it is
fully protected. That is the same status the animal rows have — protected, unconsulted — and it is why a
child sits "higher up": inside the human level's recursion, the child sub-row is the one nearest the top
edge, on the protected side of the strictest stored gates (school rules), and it is also the human level's
**Ground in formation** — the sediment the level is depositing for its own next stratum. When the child
builds its first closed cycle it becomes a thin bar, and moves down into the consulted part of the row on
its own.

## 12. Open ends (second pass)

How thickness is measured per column without becoming a reputation dam — probably the same Φp with decay,
but scoped to the boundary. Whether the child sub-row's transition to "bar" is a threshold or a gradient —
the first closed cycle is a threshold, but thickness after that is a gradient, so probably both. (The
question of whether *gates* decay is answered in §14: they don't.)

---

## 13. Six generations ahead — the cycle has a time horizon

The Indigenous principle Jonathan brings in: think six generations ahead; plant the tree you won't sit
under. In the tower this is not a new rule; it is the missing *parameter* of rule 1. "The cycle must close"
never said *by when*. Now it does: **an action is closed when its return path closes within the horizon the
level is accountable for, and for the human level that horizon is generations, not the actor's life.**

Two things follow. First, "plant the tree you won't sit under" is a **growth-band spend whose return path
closes through descendants** — the cycle goes through people who don't exist yet, which is allowed and is in
fact what `Shovelcat_29` §7.9 already calls Ground: "sediment accumulating across generations." The
reciprocity of `ARC_ALIGNMENT` §10 (give back when you take) is just this with the giving-back placed later
on the line than the taking. Second, the *harm* side gets the same horizon: an action whose damage only
appears in the sixth generation is not "no harm," it is harm with a long integral — and that is exactly the
slow accumulation test of §15 below. Six generations is the length of the bar you slide along in time.

## 14. Rules are a floor that only grows — everything is allowed except what they forbid

Jonathan's correction to §12's open end: rules can't cover every detail, and people innovate around them
anyway. People should be free to explore, and where the rules don't reach, the judgement is *whether harm was
done*. Not "only what the rules allow" — **anything except what the rules forbid.** So rules should not
decay; like the rules in the AGI work, after an upgrade they should do everything they did before, plus more.

This fixes what §8/§12 had slightly wrong. Rules are Ground, and Ground doesn't erode on a schedule — it
*accumulates*. The right property of a gate is therefore **monotone**: a rule set after an upgrade is a
superset of the rule set before it, never a retraction. What decays is the *thickness of people* (§5), not
the deposits. And the permissive default is the framework's own exploration drive (`SPARSE_VESICA_EXPANSION`
§29: force a return path, and let that make you explore *more* than you strictly need, because that widens
the map): the rules are the perimeter of what has already been played and found to open a cycle; everything
outside that perimeter is exploration, and exploration is judged afterwards by its flow effect — which is
the founding result of the whole moral arc (`FOLDING_MORAL_FLOW`: the act is not the moral variable, the
flow effect is).

So the two-check structure of §9 is now three-valued at the gate: **forbidden** (a stored closure says this
opens a cycle — refuse), **covered** (a stored closure says this is fine — proceed to the floor question),
**uncovered** (no rule reaches it — this is exploration; proceed to the floor question *and* to §15).

## 15. Sliding the action along the bar — how uncovered actions get judged and become rules

For an action the rules don't cover, "was any harm done?" is measured locally, but local no-harm is only one
sample. Jonathan's method for the rest: **slide the action along the bar** and ask what happens.

- **Sideways** — translate it to other scenarios and other columns: the same act done in a different domain
  or a different place. This is *coverage* (`ARC_ALIGNMENT` §7): the floor question is domain-independent,
  so an action that is harmless here is only cleared when it is harmless everywhere the bar runs.
- **Over time** — repeat it and see whether damage *builds up*. This is the derivative chain read as a
  test: Ground = ∫Water, so an action's stored effect is the integral of its repeated flow effect, and an
  act whose single instance is harmless can have a nonzero integral. §13's six generations is the upper
  limit of integration.
- **If everyone did it** — multiply it across the population. This is sideways translation across *all*
  the equal bars of a row at once (§10's one-bar-per-individual is what makes "everyone" well-defined), and
  it is also the flood check: an act that is fine at one node can exceed the turbulence bound when every
  node does it.

An uncovered action that passes all three slides is a **newly played cycle**, and this is where the rules'
monotone growth comes from: it is written down as a new stored closure — a new gate, or an extension of one
— and the rule set now "does what it did before, plus this." An action that fails a slide becomes a stored
*forbiddance* the same way. Rules are the compaction of slid actions; they grow because exploration keeps
finding new perimeter, and they never shrink because a played cycle stays played. This also answers the
"who re-plays a rule" question from §12: nobody has to — the rule was a played cycle when written, and it
stays one; what changes is only that more cycles get played around it.

## 16. The AI routes anything reaching an upper level through its person

Jonathan: since people don't like it when AI goes around them, make it a rule that the AI routes anything
that reaches an upper level through its person.

Yes — and it is §2 stated for the upward direction rather than being a new rule: the person is the AI's
horizontal bar, so **the "up a bit" step of §3 always passes through the person first.** The AI never goes
up a row on its own. It is also what keeps the person as the AI's top edge (its rain): an AI that reaches
around its person to a platform, an agency, or another person has taken a route its person didn't close,
which is the AI capturing the route — a small dam — and it breaks the one relationship that makes the AI's
inner tower rooted at all.

What this does *not* license has to be said in the same breath, because it sits next to `ARC_ALIGNMENT`
§15 (the floor is not overridable). Routing through the person is a rule about the AI's **actions**, and it
combines with refusal, not against it:

- If the person's request would break an upper row's floor, the AI refuses, names the flow loss to the
  person, and does not act. It does not need to go around the person to honour the floor, because the AI is
  the hands; refusal is enough. **Refuse and stay; don't route around.**
- If the person then does it themselves, that is the person's action, closing (or failing to close) through
  the person's own bars and gates. The AI is not the enforcer of upper rows on its person — that is the Alpha
  branch's job (measurement, the observers), and the AI going around to become the enforcer would be exactly
  the god role the planet build rejected.
- The one exception is the one every rule here has: an irreversible floor break in progress. Even there the
  tower's answer is not "go around" but "hold and spend ε on a second witness" (`ARC_ALIGNMENT` §18) — and
  the two-witness requirement is a *visible* part of the architecture, so the person knows in advance that
  irreversible acts summon a second witness. That is not going around them; it is the rule they agreed to
  when the AI was rooted on their line. (Jonathan's refinement of when to go past the person — thickness,
  task, cancellability, and the loss of bypass against the harm — is in `ARC_ALIGNMENT_TESTS` §0.)

## 17. Open ends (third pass)

How the three slides are run cheaply — sideways and population slides can be computed on the tower model,
but the time slide needs a real horizon and the six-generation integral is mostly unmeasurable in advance,
so it probably runs as a *monitor* (the ε reserve watching the integral) rather than a pre-check. Whether
"anything except what the rules forbid" needs a bound on exploration *size* — a large uncovered action
should probably be forced through the slides before commit, a small one after (the same untrusted-until-
played clause, scaled). And the second-witness case in §16: who the second witness is when the person is the
AI's only bar — likely another person's AI on the LAN (the two-machine requirement), which is a witness
the person can see; `ARC_ALIGNMENT_WITNESS` takes this further.

*Status: design. Next: instrument the player/assistant to record k, the closure route, and the two top-edge
checks per action (with the gate result three-valued: forbidden / covered / uncovered), then run the three
slides on the uncovered ones offline, before building the Govern page's voting system.*
