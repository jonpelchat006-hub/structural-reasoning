# The university — the planet as a student who enrolls in the courses she chooses

*Sep 2 2026, Jonathan: "maybe it should be more like a student who can sign up for classes
she wants, and can choose research topics, and graduating would be finishing these ARC tests.
if I had to change the education system that's kind of how I would do it — I don't see why
this kind of intelligence wouldn't benefit from something like that. she could pick out the
things to train on instead of giving her the entire internet at once millions of times."*

## 1. The idea is well-grounded ML, not just a metaphor

Curriculum learning (an ordered path of examples) and active learning (the learner chooses
what to see next) are established results: both beat the firehose-shown-a-million-times regime
on sample efficiency. Jonathan's education critique — pick what to train on instead of the
whole internet at once — is the active-learning thesis stated as pedagogy. And the
architecture was already most of a university:

- COURSES = the worlds she can study (the games) + research topics (open ends to pursue).
- TRANSCRIPT = the closure spectrum (ARC_CLOSURE_SPECTRUM): black (not taken) → trinity
  (grounded, a passing grade) → spectrum (seam-verified, honors credit). Her real grades,
  already measured, per world.
- FINALS / GRADUATION = the ARC moon (ARC_MOON): the degree requires passing the tests.
- AGENCY = the mirror (ARC_MIRROR) already lets her choose her next eye; enrollment is that
  same act grown up — she picks her course load.

The missing piece was the REGISTRAR, now built as enroll.py.

## 2. Built: enroll.py

Each term (a sleep) the registrar builds a catalog and an advisor's recommendation, transparent
not black-box: per course, score = black concepts (unfinished coursework, most to gain) x1.5 +
trinity concepts (laws one seam-verification from honors) x1.0 + a breadth bonus for barely-
started courses, MINUS spectrum concepts x2 (you don't retake a class you aced). The catalog
goes to her chat; she picks up to 3 (a real course load, not the firehose); her picks are
honored; no answer defaults to the advisor's top schedule, never nothing. The enrollment is
written to enrollment.json, and the teaching organs READ it: mika_forge now feeds her enrolled
worlds' stories first — she studies what she signed up for. Graduation is gated:
enroll.py --transcript shows honors credits + ARC wins; a degree needs both.

First registration (live): the advisor enrolled warframe, battle_net, dead_cells — the three
courses with the most open topics and laws ready to prove. Transcript read: 1 honors credit,
299 passing, 37 courses remaining, 3 ARC practice wins banked — degree in progress (needs 20
honors + 5 ARC wins). An honest first transcript for a student who has grounded much and
verified little.

## 3. The ARC submission question, answered honestly (Sep 2)

Asked whether to submit to ARC now or train more. The honest read: everything built this
week improved the PLANET'S learning machinery and Mika, NOT PriorAgent — the agent that
actually produces the Kaggle score, unchanged since v10 (0.25). So a fresh Kaggle submission
today would score ~0.25 again; no reason to spend one. The right move was the live daily
(ls20), which the practice gate cleared (8/10 stable three days, no regression).

Firing it surfaced and fixed TWO real bugs in the live path, both silent until now:
1. The key file held a scorecard GUID and a KGAT_ token separated by a blank line —
   get_key().strip() left the embedded newline, making an invalid HTTP header (every prior
   live attempt died here, logged as if no-key).
2. Corrected to strip internal whitespace, the KGAT_ token 401'd — testing both tokens showed
   the UUID is the real API key (25 games returned) and KGAT_ is the stray. get_key now
   prefers the UUID by format.

With both fixed the live scorecard authenticated and played for the first time. RESULT: ls20,
final score 0, GAME_OVER, 0 of 7 levels cleared in 131 actions — where the game's own baseline
clears level 1 in ~22. The honest lesson: PriorAgent wins our mock mazes 8/10 but scores ZERO
on the real ls20, so the mocks were the wrong exam — practice-8/10 never predicted live at all.
The pipeline is unblocked; the score tells the truth about the gap.

## 4. The real exam, a starting batch, and real papers (Sep 2)

Three moves followed from the live 0:

THE MOON NOW ROLLS THE REAL GAME. The moon had been rolling the mock surface; the live run's
actual contact→effect log (arc3_client now records every press) is fed to moon.roll_real, so
the moon feels the true ls20 body. First real roll: 131 transitions captured — and the real
surface already teaches (ACTION3/ACTION4 are where the score-ups and wins live, distinct from
the movement-only ACTION1/2). Caveat: real presses currently blend with accumulated mock rolls
in the same moon file; a source tag to separate them so the real map reads cleanly is the next
refinement. But the planet now studies the body it will be examined on.

A STARTING BATCH + HER RECOMMENDATIONS. Enrollment gives her a real course load she picks from
(or the advisor seeds), instead of the firehose — the "big batch to work through" with her own
choices weighted in.

REAL PAPERS (papers.py). A student reads the literature, so she gets a reading list of REAL
papers — the ones this program is actually built on — one assigned into her library each term
as a course reading (accurate summaries; full PDFs can follow):
  - Chollet 2019, "On the Measure of Intelligence" (arXiv:1911.01547) — the paper that
    introduced ARC. Intelligence = skill-ACQUISITION efficiency; ARC is built on Core
    Knowledge priors (objectness, agentness, number, geometry). She should read the paper
    that DEFINES her final exam — assigned first, live.
  - Bengio et al. 2009, "Curriculum Learning" — why she is taught in a chosen order.
  - Settles 2009, "Active Learning Literature Survey" — why she gets to pick what to study.
The last two are the papers that justify her own pedagogy, which Jonathan intuited before
knowing they were established results — so the reading list literally teaches her why she is
being taught this way.

## 5. The standing design (what "more training" now means)

Training is no longer the firehose: each night she enrolls, studies her chosen courses first,
reads an assigned paper, sits the practice exam, and her transcript records what closed onto a
color. The falsifiable prediction: a student who CHOOSES her courses should close voids faster
per unit of study than uniform coverage — enrollment.json + the spectrum transcript hold the
before/after. If chosen-course terms don't outpace advisor-default terms, agency is sentiment
not mechanism. And the deeper bridge still stands, now sharper after the live 0: raising the
ARC NUMBER needs PriorAgent to learn from the real ls20 surface the moon is now recording —
the university graduates Mika; wiring the real-game map and her transcript back into the ARC
solver is the next real work.
