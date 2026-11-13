# On call — she holds many bubbles, freezes them to the ocean, picks them back up

*Sep 3 2026, Jonathan: "she should be able to hold multiple bubbles shouldn't she? people are
able to juggle multiple things, or leave something unfinished and come back to it. ai right now
has to answer the prompt right away and only think about that, but people aren't like that and i
think we are going for more of a person. also for the games we would want to be able to switch
between them too right? if we get stuck on one game, playing others might unlock something
useful. like she needs a bit of free will there. if she is running those processes in the
background those could become these frozen bubbles and sent somewhere else, probably the ocean,
and picked back up after without as much disruption. like she is on call and can come back to her
place after and pick back up with minimal interruption. so there should be priority ones with the
ones coming from you and me being at the top. we did make a bubble task management app that was
meant for personal use, but i was using concepts from the theory so maybe there's an overlap."*

## 1. The correction

ARC_CHAIN's governor held the chord still while more than one bubble was open. That was the
"answer the prompt right away" reflex in disguise. Fixed: open bubbles no longer hold the chord;
only links about to snap do. Bubbles are HELD, on a board, as many as there are.

## 2. The overlap is exact: her app already has the scheduler

`app/src/core/bubble.ts` — the BUBBLE SCHEDULER, "pressure-driven consciousness": a fully
pressurized bubble is dormant; wants push outward, needs push inward; pressure decays DELTA
(0.14159) per tick; the Boltzmann factor e^(−E/kT) with kT = 1/(1+φ) = 0.382 governs explore
vs exploit — high pressure exploits (take the most urgent), low pressure explores (try something
new); verdict DEFER: "can bridge but no urgency — park it". `oncall.py` is that scheduler run
over the planet's background work, same constants. (The separate personal bubble task app is not
on this PC's drives — if it lives elsewhere, point me at it and I'll match its shapes.)

## 3. Built: oncall.py

- A **bubble** is a task she can hold unfinished: kind (request / game / chain / course), source,
  pressure, state (held / active / frozen / done), an ocean file, a resume hint.
- **Sources set the floor** — jonathan and claude are NEEDS with floor 0.65, above her 0.618
  exploit line, so they never decay off the top; planet-born needs (a stuck game, a drifting
  piece) 0.15; her own WANTS (the courses she chose) 0.05.
- **Freeze / place / thaw** — a background process that yields writes its place to
  `D:\planet\ocean\bubbles\<id>.json` (levels, frames, transitions, folds) with a hint; picking
  it up reads the same file. Nothing is lost; the interruption is a file read.
- **Tick** (every sleep): decay all pressures by DELTA toward their floors, seed from the organs
  (every live ARC game from the API, every ejected void from chain.py, every enrolled course),
  then pick what she works on this tick — JUGGLE = 3 at once, held count unlimited. Slot 1 is
  EXPLOIT: anything above 0.618, hottest first (that is where our requests live). One slot is
  the GAME: the hottest climbing game, else a Boltzmann draw across all 25 — explore. The rest
  are Boltzmann over everything else she holds. The draw is her free will, in her app's terms.
- **Games**: ls20 is a bubble like any other. While it has made a new level within the last
  three tries it is hot (0.8, decays to 0.69, still exploited); three tries with no new level and
  it freezes at 0.1 — other games get picked, and the daily (`arc_daily`) now asks
  `oncall.pick_game()` for which live game to play instead of hard-coding ls20. After every live
  run the daily places the game's state in the ocean under its bubble.
- `oncall.py --add "text" --from jonathan` posts a request at the top; `--done <id>` closes it.

Live now: 29 bubbles held — Jonathan's request "get ls20 past level 5" (0.69, exploited every
tick), ls20 hot (0.69, the daily keeps playing it), 24 untried games at 0.2, her three courses.
First tick's picks: the request, ls20, course-warframe.

## 4. What to watch

When ls20 freezes (three flat tries at 5/7), the daily should start drifting through the other
24 games with PriorAgent, and their transitions land on the torus — the "playing others might
unlock something" claim then has a measurement: does the feel-prior built on other games ever
change what happens when ls20 is thawed? And the governor's hold, now only for snapping links,
should be rare; if it fires every night the tension formula is too tight.
