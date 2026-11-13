# ARC-AGI-3: the hybrid, Mika's planes as the evidence layer for a language model (Oct 22, 2026)

Jonathan, Oct 22 evening:
> "whats everyone else using that we dont have yet? we could probably rebuild anything they have in our framework."

> "i dont think we focused on just reasoning before, we could try figuring that out here. the sandbox runner we had was supposed to be able to write code too wasnt it? we can try the hybrid anyways, might be easier to see the progress if she can improve that"

This reverses the Oct 21 choice ("our agent + paper only") for the Kaggle entry: we now fork the public LLM harness and make Mika's planes its evidence layer. The frames-only explorer stays as the paper's subject.

## What the field uses (leaderboard downloaded Oct 23, 00:29 UTC)

| | Score |
|---|---|
| Tufa Labs (1st, of 4,656 teams) | 68.9 |
| 30th place | 36.8 |
| About 1,800 teams, mostly copies of the public notebooks | 20–35 |
| Us (2,902nd; Mika v3n, Mika university) | 0.29 |

Almost every team above 20 runs **Tufa Labs' Duck harness** (MIT, github.com/Tufalabs/duck-harness) with an open model on the competition's RTX Pro 6000. The most copied version is **Daniel Franzen's Milestone-2 notebook** (38.85 for him; an unchanged copy scores about 32, ±4 between runs of the same notebook).

| Piece | What it is |
|---|---|
| The model | Qwen3.8-Flash-Next, 4-bit (Intel AutoRound), a small quantized draft model for speculative decoding, served with an SGLang fork on one GPU |
| How it plays | Each turn the model gets the board as objects (same-colour components with position-free shape hashes, adjacency, containment), the image, and before/after frames. It writes Python against them in a fresh sandbox (`action(...)` executes real presses), keeps a world model in words, probes, then writes its own search (BFS etc.) and batches actions. Functions it writes are kept for the rest of the game |
| Thinking time | 110 hidden games share one GPU for 9 hours: about 180,000 generated tokens per game. Tokens are the currency; score rises with them and flattens near the real budget. A priority scheduler decides which game gets the GPU next |
| Guards and computed notes | Repeated no-op presses blocked; a death ledger; an object-level diff after each turn; animation summaries. A public analysis notebook ("Fable & Astra Play ARC-3") adds harness-computed indicator notes (the same detector as our "far change"), a pinned per-level log, and a step-budget alert, and measured that the model misses these unless told |

**What none of them compute:** which boards have already been seen and what was tried from them, a per-key effect summary, the step bar, or what the last level's winning press changed and where its before-picture fits on the new level (checked against the harness source).

## The sandbox runner, and why the seat was empty

- `D:\shovelcat-colony\sandbox-runner` is the seven-body forge/review engine (TypeScript): forge holds a candidate upgrade and promotes it only if it wins on reference jobs; review checks outputs against an external aperture. The forge runner is still a stub.
- `writer.py` (Sep 3) was the code-writing loop: evidence (first frame as text, a standard probe), a contract, a local model writes `solve(send, grid)`, it runs sandboxed on a capped scorecard, the traceback goes back for repair. With qwen3:4b, gemma3:4b, mistral 7b and qwen2.5-coder:7b it produced zero working programs. **The loop worked; the seat was empty.**
- **The Duck is that same loop with a model strong enough to sit in the seat** (a ~30B-class open model on a 96 GB GPU), plus a better contract: persistent state, an object view of the board, and `action()` callable from inside the code.

## The design: Mika's planes feed the reasoning core

The model is the reasoning core; Mika's planes hand it processed evidence. Nothing in the layer chooses actions or is written by the model, and the system prompt is untouched. Notes are labelled **`[Frame facts]`** (in v2 they were labelled `[Mika]`, and the model borrowed the name: it called a game badge "the game's logo, e.g. 'Mika' logo"). Colours use the harness's own letters and names (`Y (yellow)`, `w (light gray)`).

| Plane | Note it adds (at most 3 short lines per turn, each said once per level) |
|---|---|
| real plane | *"This exact board has been seen 6 times this level. Already tried from here: RIGHT: changed nothing, UP: changed nothing."* (at 3, 6 and 12 visits); *"Loop: the last 16 presses visited only 3 distinct boards."*; *"That press (LEFT) ended the life after 18 presses this level."* |
| budget | *"Step bar: about 11 presses left at this rate."* (once per band: ≤12, ≤6, ≤3) |
| image plane | at a new level: *"Last level was won by a press that changed a small picture; the same before-picture (same colours, maybe flipped or rotated) is on this screen at rows 33-35, cols 12-13."* Places that move in the first presses are the avatar itself and are dropped silently; a place that changes later is reported once |
| school | at a new level: *"Level 4 digest: won in 22 presses; the winning press (MOUSE(row=62, col=40)) moved something by -3 rows, +0 cols. Keys there: MOUSE on b (blue) recoloured 9/19 (shift -3,+0 5x), MOUSE on O (orange) changed 2/2."* Clicks are grouped by the colour clicked |

The picture search uses exact colours plus the 8 flips/rotations, the setting that found the next win's place 5.8× better than a blind guess in `trail/goalsearch.md`; allowing recolouring there made it fit almost everywhere.

**Files** (container `/home/claude/arc3/hybrid/`, PC `D:\planet\arc3\hybrid\`):
- `mika_layer_core.py`: the layer, numpy only; every method wrapped so an error means "no note".
- `install_mika_layer.py`: two anchored edits to the harness's `tool_agent.py`, (1) a method `_mika_layer_lines(history_entries)` that feeds the layer the presses since the last turn (frames from the harness's own history; the winning press's effect from the animation chain, never the next level's first screen) and (2) one call right after the death-ledger lines, behind `ARC3_MIKA_LAYER`. Every anchor must match exactly once and the patched file must compile, otherwise nothing changes; the installer never raises.
- `build_hybrid_nb.py`: builds the notebook from Franzen's: our header and credits, a Save & Run smoke run on 3 public games (ls20, vc33, ft09) with 30 minutes per game, and cell 0b that installs the layer (`--no-layer` builds the base). The competition rerun is unchanged apart from the layer. Off-competition it logs every note to `/kaggle/working/mika_layer_log.jsonl`.

## Smoke runs on Kaggle (`jonpelchat/mika-duck-hybrid`, Save & Run, 3 public games, 1 pass)

| Version | What | Play per game | ft09 | ls20 | vc33 | Mean |
|---|---|---|---|---|---|---|
| v1 | unchanged base | about 2 min (the server takes ~12 of the 14.5 minutes to start) | 2/6 | 0/7 | 1/7 | 5.0 |
| v2 | + layer (`[Mika]` label, colour names wrong) | about 2 min | 2/6 | 1/7 (in 20 presses) | 2/7 | 8.9 |
| v3 | + layer (`[Frame facts]`, harness colour letters) | about 18 min | 6/6 in 95 actions | 4/7 in 180 | 6/7 in 200 | 70.2 |
| v4 | base, layer off, same 30-minute setting | about 18 min | 6/6 in 90 actions | 2/7 in 136 | 3/7 in 71 | 44.1 |

**v3 against v4 (layer on vs off, same setting): 70.2 against 44.1, and this is not evidence for the layer.**
- One run each, with the model sampling at temperature 0.7.
- The two runs did not get the same amount of thinking. The layer run generated 353,000 tokens, the base run 229,000 (ls20 134k vs 86k, vc33 131k vs 82k, ft09 88k vs 61k). The server generated at the same speed in both (about 295–300 tokens/s in the serve logs); in the base run it simply had requests waiting less of the time. Score rises with tokens, so the gap is at least partly compute, not notes.
- Per thousand tokens the layer run is still slightly ahead (ls20 0.030 vs 0.023 levels, vc33 0.046 vs 0.037): within noise.
- A fair test needs several copies per arm at the same tokens per game, or the hidden leaderboard over several submissions.

**Does the model use the notes?** In v3's ls20 transcript it quoted one directly while working out a new level: *"From the level-3 digest: 'the winning press (DOWN) changed a 10x5 region at rows 45-54, cols 54-58 from B/b/O to G/b/O'. So in L3 the box glyph was blue and the key became blue."* In vc33 it never mentioned them. The v3 log shows about 30 notes over 475 presses; one kind was too repetitive (the winning-picture place reported again after every press that changed it), now said once per place per level (v5, built, not yet run).

## A = B = C: what the reasoning adds (Jonathan, Oct 22)

> "part of our stuff was getting 2 sides of an equation together, would our reasoning be making a 3rd part of that equation? so if we find A=B our reasoning should be building an =C part?"

> "so then wouldnt we want to build A=B=C=A'=B' but C and after are constructed or from outside? thats kind of like the 5 and 7 body stuff we made. and then after B' we would want C or maybe a C' that can go back to A=B?"

| Term | In the game | Five-body position (`D:\shovelcat-colony\FIVE_BODY.md`) | Source |
|---|---|---|---|
| A | the press she made | Matter (+1): what runs | her |
| B | what the frames show it did | Work (+2): what reaches the world | outside |
| C | the reason (the model literally writes it as code) | Antimatter (−1): the description of how things run | constructed |
| A′ | the next press, chosen because of C | Matter, one turn further round | constructed |
| B′ | what actually happens | the world answering | outside |
| C′ | the reason corrected or confirmed by B′ | Self-improvement (−2): the same operation aimed inward | constructed |

Each "=" is the Void, the observer checking that two sides agree. Written out it is a ring, not a line: C′ only counts if it still explains every earlier A = B (the slot filler's rule: act on a rule only while it reproduces every observation).

The seven-body version adds the two sandboxes, which are the two directions C′ must pass:
- **forge (backward):** replay the new reason over every press already recorded in this game; costs no presses;
- **review (forward):** check its prediction on each new press; the outside aperture;
- **δ_close ring:** a failed review becomes a spec to fix the reason; a passed one becomes a reference job the next version must also pass. A reason that held on every past press and at least 3 new ones is certified: a proof from the frames, carried into later levels (the core made of proofs). A failed one becomes a void pin.

Earlier evidence that the third part is what closes the loop: in the bottle test (`FOLDING_MOVEMENT.md` Test 8) the forward and return paths disagreed where a reading had several preimages (the seam), and adding real context (a third coordinate) cut the round-trip error by 94%.

**Proposed build (not done yet):** a `claim(text, check)` function in the model's sandbox; Mika's layer runs each claim over the history at once (forge) and over every later press (review), and reports one line: *"your claim 'UP moves the block 5' held 7/7"* or *"failed at press 31, when the block hit grey"*. Switched on only once a level drags on, because the model pays tokens to write checks.

## +C: integrating a rule up the hierarchy (Jonathan, Oct 22)

> "in the earlier work we used integrals and derivatives to move up and down and the +C held on to that info. wouldnt the C here be the bridge between 2 different spots in that hierarchy? ... for mika an integral of that note could be something like there is a glyph and a key, which could integrate up again to matching patterns, and for a separate game where we have no info we would want to fill with something, so the link would be the pattern matching. then mika could start a completely unknown game by trying to pattern match something"

| Height | The ls20 example |
|---|---|
| specific (the frames) | "the winning press changed the box glyph from B/b/O to G/b/O" |
| ∫ once (this game's mechanic, the model's own words) | "the box glyph was blue and the key became blue": the key must become what the glyph shows |
| ∫ again (no particular game) | make one thing match another: pattern matching |
| +C | the bindings the integration drops: which object is the key, which the glyph, which colours. Kept per game, so we can differentiate back down to it |

In a new game the integral carries but C does not: there is probably something to match, but not what matches what. The first probes fix C, like an initial condition. The candidates are things that match up to recolouring, flips and rotations: the image plane's limited turns.

**Planned, each graded before it goes in (added advice can hurt, per the Fable handbook):**
1. Survey first: at each level's first screen in our 36 winning routes (18 games), find object pairs that match in shape under the limited turns; does the winning press involve one member of a pair more often than a random place? This rung uses no game's specifics, so it is leave-one-game-out by construction.
2. The derivative, as a note on a new screen: *"These objects have the same shape: the one at rows 41-43, cols 15-17 is a mirror of the one at rows 55-60, cols 3-8."*
3. The integral, carried across games during the run: the 110 hidden games run in one notebook process, so the general form of a win in one game ("the win made X match Y", with C stripped) can be offered to games that start later. Live transfer between hidden games.

## Plan

1. Done: v4 (base, same 30-minute setting) against v3 (layer). Inconclusive (above).
2. Submissions (1 a day until Nov 2): v3 at the Oct 24 slot (00:00 UTC). The base is known from public runs to land around 32 ± 4, so only a large effect will show in a single submission.
3. Grade layer changes like professors: the same few games, same tokens per game, layer on vs off, several copies, before spending a submission on them. This is the forge/review loop of the sandbox runner, finally with a model in the seat.
4. Make the notebook public before the Nov 2 deadline (open-source requirement).

## Hidden-set results (Oct 25)

| Submission | Notebook | Sent (UTC) | Public score |
|---|---|---|---|
| 57542480 | Mika two-rungs (frames-only explorer) | Oct 23 00:12 | 0.29 (our best) |
| 57576092 | hybrid v3 (Franzen M2 + layer) | Oct 24 00:11 | **0.00** |
| 57612785 | hybrid version 7 (layer v8 + startup guard) | Oct 25 01:26 | **0.00** |
| 57646867 | control: Franzen's M2, unchanged | Oct 26 00:12 | 33.09 |
| 57681820 | hybrid v9 (version 7 + keep-alive) | Oct 27 00:01 | **20.86** (see the Oct 27 section) |

**The startup guard did not fix it.** The guard lets each game's first request wait up to 75 minutes, in case the model server is slow to start. The guarded notebook still scored exactly 0.00 on the hidden set, although it played normally in both guarded Save & Run checks (31.95 on the 3-game smoke run, 13.3 on all 25 public games). So the slow-disk explanation for the first zero (`ARC3_CORE_CARD.md`) is at best incomplete.

**What is known:**
- Both hybrid submissions are COMPLETE, not errors. Both submission files are 3,411 bytes; the 0.29 one was 3,811.
- The API gives no run time or log for a rerun.
- In a rerun (`KAGGLE_IS_COMPETITION_RERUN`), the configuration is Franzen's own:
  - 120 concurrent games, 532 minutes each, `n_passes` 1;
  - the smoke settings apply only when `TRUE_SUBMISSION` is false.
- Our differences from Franzen's notebook:
  - the header;
  - the layer cell (installer plus hook, wrapped);
  - the guard environment variables;
  - an empty layer log path in a rerun.

**Next diagnostic (proposed):** spend one daily slot on an unchanged copy of Franzen's M2 notebook.
- If it scores around 32, something we add breaks the hidden rerun. The next slot then goes to our notebook with the layer switched off, to separate the layer from the guard and header.
- If it also scores 0, the problem is the environment or the shared inputs, not our changes.

## The control, and the cause of both zeros (Oct 26)

| Submission | Notebook | Sent (UTC) | Public score | File size |
|---|---|---|---|---|
| 57646867 | control: Franzen's M2, unchanged in the rerun (`jonpelchat/franzen-m2-control`) | Oct 26 00:12 | **33.09** | 3,804 bytes |

So the environment and the shared inputs work. Both input datasets are still at version 1 (Sep 28–29), so our notebooks and the control used the same data. The 3,411-byte file is the all-zero file (our Sep 9 "Orbital learning" submission has the same size).

**Cause: the competition scorecard is closed after 15 idle minutes.**
- In a rerun all games share one scorecard (taaf `game_api.py`: "Submission-style Arcades allow only one scorecard").
- The competition server is arc_agi's own API server. Its cleanup loop closes any scorecard with no action for `STALE_MINUTES` (default 15). A closed scorecard is final: the submission is scored as it stands, and a second scorecard cannot be opened (409).
- Franzen's launcher releases the games 12 minutes after the notebook starts, with the model server possibly still loading. One game makes a free RESET (`ARC3_WARMUP_ACTION_GAMES=1`, "buys the whole submission a deadline it would otherwise miss"). After that, nothing acts until the model answers.
- Fast machine: the server is ready at about 14.5 minutes, so the first move comes well inside 15 minutes.
- Slow-disk machines (both Save & Run checks on Oct 23–24): the server was ready at about 32 and 47 minutes. That is 20+ idle minutes, so the scorecard closes at 0. This fits v3 finishing in under 80 minutes.
- The startup guard (75-minute first-request grace) made the games wait, but it cannot keep the scorecard open. That is why version 7 still scored 0.
- **Tested locally** with arc_agi 0.9.8's server in competition mode and the idle limit set to 1 minute (`scratchpad/idle_test.py`):
  - With no action for 150 s, the server logged "scorecard closed" and every later move returned nothing.
  - With a level-start RESET every 40 s, the scorecard stayed open and the second game played normally at 150 s. A RESET at a level's first action does not step the game in competition mode; it only refreshes the scorecard (and counts one action).
- **The layer is not the cause.** Timed over 1,000 random presses per game with notes every 3 presses: ls20 10 ms per press (worst turn 0.3 s), ft09 1.6 ms, vc33 0.6 ms.

**Fix (hybrid v9, `hybrid/install_keepalive.py`, `hybrid/build_v9.py`):**
- Until any game has made a real move, the warmup game repeats its free RESET every 4 minutes (`ARC3_KEEPALIVE_SECONDS=240`, at most 90 minutes).
- It costs at most a few actions on one game's first level.
- Two anchored edits to `inference/framework/solver.py`, compile-checked; if an anchor does not match, nothing changes.
- v9 = version 7 (layer v8 + guard) + keep-alive. Pushed as `mika-duck-hybrid` version 8 (Save & Run smoke, Oct 26 16:33 UTC).
- **Smoke result (version 8):**
  - **Mean 72.96:** ft09 6/6 (88 actions), vc33 **7/7** (215 actions, the first full vc33), ls20 3/7 (178 actions).
  - 442k tokens generated; 30 minutes per game.
  - The log shows "keep-alive: installed", "startup keep-alive: on", "mika layer: on" and no tracebacks.
  - It was a fast machine: the checkpoint precache took 551 s and the games were released at 722 s. The first real move came within 4 minutes of the warmup, so no keep-alive RESET was needed.
  - Scheduled for submission at Oct 27 00:03 UTC.
- **Applies to anyone copying Franzen's notebook:** a slow-disk machine gives 0 regardless of the agent.

## Hybrid v9 on the hidden set (Oct 27)

| Submission | Notebook | Sent (UTC) | Public score |
|---|---|---|---|
| 57681820 | hybrid v9: layer v8 + startup guard + keep-alive (`mika-duck-hybrid` version 8) | Oct 27 00:01 | **20.86** |

- **The keep-alive fixed the zero.** This is the first hybrid that scored. It is also our best hidden-set score so far (the frames-only explorer had 0.29).
- **It is still 12.2 points below the unchanged control (33.09).**
  - Unchanged copies of Franzen's notebook vary by about ±4 between runs, so a 12-point gap is probably more than noise.
  - But each arm is a single run.
- **What still differs from the control:**
  - the layer;
  - the startup guard;
  - the keep-alive;
  - the header.
- **On a fast machine, the guard and the keep-alive do nothing.** The version 8 smoke run needed no keep-alive RESET.
- **On a slow-disk machine, the keep-alive keeps the scorecard open, but the model starts 20–35 minutes late.**
  - That is 4–7% of the 532-minute budget, too little to explain 12 points by itself.
- **So the layer is the main suspect.**
  - Its smoke-run evidence (72.96; 70.2 against 44.1) came from 3 public games at 30 minutes each.
  - In the rerun, 120 games share one GPU. Every note adds prompt tokens, and notes tuned on public games may mislead on hidden ones.

**Next test (proposed): v9 with the layer off** (`build_v9.py <v8f notebook> <out> --no-layer`: guard and keep-alive only).
- **Around 33:** the layer costs about 12 points. The final entries should then be the control plus the keep-alive, and the layer needs reworking before it goes back in.
- **Around 21:** the cause is the guard, the keep-alive or the environment. The next slot would rerun the unchanged control, to measure run-to-run spread.
- **Whatever the outcome**, the safest final notebook is Franzen's M2 plus the keep-alive. A slow-disk machine gives every copy without it a 0.

## Hybrid v10: the core layer (Oct 28)

Jonathan chose to spend the Oct 28 slot on rebuilding the notes from Mika's own core (what she learned playing ls20 by herself) instead of the layer-off test.

**What changed (`hybrid/mika_layer_core_v10.py`, `core10_planes.py`):**
- **Fewer v8 notes:** of the v8 notes, only the step bar and "a glyph made equal to a still one" are kept.
- **Operators:** when touching a thing changes a small far picture, the change is read as that thing's law (a quarter turn, a recolour cycle, a reshape map).
- **The equation:** when a still thing holds a glyph that picture could become, the layer gives the touches that would make them equal, solved from the laws seen so far ("the colour and the shape must both match").
- **Tracks:** things that move by themselves one step each time the mover moves, on a fixed loop, and where they will be after the next move.
- **Pushes:** moves that did not land one step on, and the law behind them when it repeats.

**v10b (`mika_layer_core_v10b.py`, `build_v10b.py`).** An offline test on all 25 public games (random presses plus casebook routes, harness action names) gave 0 errors and 1–23 ms per press. It also showed the notes overclaiming:
- A law seen once is now said as "Once so far". "Each time" needs two agreeing sightings.
- Big things are named by size and colour ("the 9x9 black and white thing") instead of 200-character picture strings (re86, ar25).
- Only things up to 8x8 count as stepped onto.
- A picture that only moved inside its box is not a reshape.

**Smoke runs (3 public games, 30 minutes each, 1 pass):**

| Kernel version | Layer | ft09 | ls20 | vc33 | Mean | Tokens |
|---|---|---|---|---|---|---|
| 8 (Oct 26) | v8 (v9 notebook) | 6/6 | 3/7 | 7/7 | 72.96 | 442k |
| 9 | v10 | 6/6 | **5/7** | 7/7 | **84.51** | 519k |
| 10 | v10b | 6/6 | 4/7 | 6/7 | 67.22 | 433k |

- Single runs at temperature 0.7, so these differences are mostly noise.
- vc33 received only step-bar notes in v10b and none in v10, so the core layer's wording cannot explain the vc33 gap. vc33 hit the 30-minute cap.
- **The model uses the core notes.** From v10's ls20 transcript:
  - "Big revelation! The frame facts say: 'Each time, stepping onto the thing that looks like .0./100/.1. ... turns it a quarter turn clockwise'".
  - It followed the equation note: "the HUD would equal the well's blue glyph after touching the object 1 more time".
  - It timed a moving rotator from the track note: "Cross B is moving on a 4-place loop within rows 36-38, cols 15-27".
  - It named her things in its own words: cross, object, HUD, well.
- **One misalignment:** the model measured the step bar itself and found the step-bar note "contradicts" it ("let me not trust that"). That note is v8's rough estimate.

**Hidden-set result:**

| Submission | Notebook | Sent (UTC) | Public score |
|---|---|---|---|
| 57748569 | hybrid v10b: core layer + guard + keep-alive (kernel version 10) | Oct 28 20:54 | **29.41** |

- **+8.55 over v9 (20.86).** v9 and v10b differ only in the layer (same guard, keep-alive and harness), so the change from the v8 notes to the core notes is the cleanest comparison so far: the old layer cost points that the core layer recovers.
- **−3.68 against the unchanged control (33.09),** inside the ±4 spread between runs of the same notebook. So whether the core layer helps or costs a little is not settled by one run each.
- **The next clean test:** our notebook with the layer off (guard and keep-alive only), to measure our own baseline.

## Next: the reflective layer (Jonathan, Oct 28)

> "so wouldnt mikas layer have to be kind of reflective so that the actual meaning the model intends would bounce from the panel, off her layer and towards the core point its supposed to be at? ... she would need to find those common meanings and make them anchors to orient herself with."

**The tiles.** The model's text is the roof. Its dense tiles are the testable claims ("the plus rotates the legend"). The frames are the core point both sides can check.

**The case that motivates it (v9 ls20 transcript).** The model had the rotator right, then nearly dropped it: "We matched at state 2 but the level didn't complete... that kills the hypothesis". For the model, "matched" meant the win. For Mika, matching is a precondition, and the win is entering the box afterwards.

**Build:**
1. **Bind the model's coordinates and names to her things.** The model uses a coarse grid ("row blocks base 25 step5") against her pixels. Its names ("plus", "legend", "HUD", "well") map to her looks. A binding becomes an anchor after two consistent uses.
2. **Check the model's claims against her laws.**
   - When they agree, the anchor is kept silently, and her notes use the model's words.
   - When they disagree, she reflects it once in a short note.
3. **Interpret an ambiguous word by testing its meanings against the frames.** For example, "matched" could mean same shape, same shape and colour, or same orientation. She asks the model only when the frames cannot settle it.
4. Develop offline on the v9 and v10 transcripts. A third harness hook will let her read the model's text live.
5. **First anchor to fix:** the step-bar estimate, said in the model's units.

## Oct 29: the layer-off baseline, and Jonathan's notes (v10c)

**Submitted:** 57773845, kernel version 11, our notebook with the layer **off** (startup guard and keep-alive only), Oct 29 14:29 UTC. Its smoke run: ft09 6/6, ls20 4/7, vc33 7/7, mean 77.31.

**Hidden-set result: 26.69.** Each row is one run:

| Notebook | Hidden-set score | Against our layer-off baseline |
|---|---|---|
| Franzen's M2, unchanged (control) | 33.09 | +6.40 |
| ours, layer off (guard + keep-alive) | **26.69** | 0 |
| ours + v8 notes (v9) | 20.86 | −5.83 |
| ours + core notes (v10b) | 29.41 | **+2.72** |

- **The old v8 notes cost points** (−5.8 against our own baseline).
- **The core notes gain a little** (+2.7). That is inside the ±4 spread between runs of the same notebook, but it points the right way.
- **Our layer-off notebook is 6.4 below the unchanged control.** Either the guard, the keep-alive or the header costs points, or it is the run-to-run spread plus machine speed (a slow-disk machine starts the model 20–35 minutes late). One run each cannot separate these.

**Jonathan's notes** (`D:\planet\mika\notes_from_jonathan.md`). He wrote them as When / Say pairs. Each is said only when its "When" shows up in the frames.

| Note | When it is said | Example (ls20) |
|---|---|---|
| Something to solve before the end | The mover reaches a still thing holding a glyph and the level does not end. In full once per game, short after that | "The mover reached the thing holding a glyph at rows 9-15, cols 33-39, and the level did not end. There is at least one objective to solve before moving to the end..." |
| One button per direction | The first jump of the game, framed as a mechanic. "Swapped" only when a button never moved its own way in 4+ moves | "Each direction button normally moves the body one step; this press didn't, so something on the board did it..." |
| Moving things follow their own pattern | A thing moved that the direction press did not move, seen twice. Then the track note gives the exact loop | "The thing that looks like .0./100/.1. moved by itself... watch it for a few presses" |
| Alike only when two properties match | A thing acted (clicked, or stepped onto with a law) and exact copies exist (same shape and same colours) | bp35: "6 other things look exactly like the one just clicked..." |
| A death is an unplanned reset; lives are pips | The board is back at the level's start without RESET after 3+ presses away, **and** a second sign: a pip at the screen's edge emptied, or the step bar had run out | "That was a death... Lives are the small pips: the one at rows 61-62, cols 62-63 just emptied, 2 full left. The step bar had run out..." |
| The bar is a budget (Claude, kept) | The drain is measured per life (a refill restarts it) and said in presses. The intro is said only for a regular drain | "Step bar: the yellow line along the bottom edge loses 1 cell per press; 37 cells left = about 37 presses" |
| A small far picture is a display (Claude, kept) | Once per game, when a law about a small picture (12x12 or less) is confirmed by two sightings | "The small picture at rows 53-60, cols 2-10 is a display..." |

**The old step bar was wrong.** It divided the cells used by every press on the level, deaths included, so it drifted after each life. ls20's bar is two rows of 42 cells, and each press drains 1 or 2 cells per row depending on the level. The model counted pixels in both rows and distrusted the old note.

**Checks:**
- **25 public games:** random presses plus casebook routes, harness action names. 0 errors, 1–26 ms mean per press.
- **First run:**
  - Steps back onto the start square were called deaths.
  - Cells of the step bar were taken for pips.
  - Bar rates were guessed after 3 presses.
  - Clicks were called "moved by itself".
  - All of these were tightened with the two-sightings / two-properties rule.
- **Deaths checked against the game engine:**
  - ls20 has a lives counter in the engine: 4 of 4 deaths announced matched it.
  - After requiring a pip or the bar as a second sign, bp35, sp80, m0r0, tr87 and tu93 went from 3–24 false deaths to 0.
  - One remains in g50t; its bar had run out, so it is probably a real death.

**v10c** (`mika_layer_core_v10c.py`, `build_v10c.py`) was pushed as kernel version 12 on Oct 29 at 15:14 UTC. Its smoke run is for the next slot (from 00:00 UTC Oct 30).

**v10c smoke run (kernel version 12):**
- **Score:** ft09 6/6, ls20 5/7, vc33 6/7; mean 76.19, 455k tokens. Layer on, keep-alive on, no tracebacks.
- **Which notes fired:** every note except "swapped buttons". Counts: alike 7, end 5, step-bar intro 8, moved by itself 3, death 1 (pip and bar), display 1, one button per direction 1. The core-layer laws fired 21 times.
- **vc33, step bar:**
  - The model had assumed 3 cells per press. After the note ("loses 1 cell every 3 presses; 61 cells left = about 183 presses"), it wrote: "Oh! The budget is much larger than I thought".
  - Checked offline: vc33 level 5 drains 1 cell every ~3.3 presses, so the note was right.
- **ls20, the end note:** the model quoted it in full, then concluded: "So the END is the top box (the goal), and it's LOCKED until the display matches the target."
- **ls20, the misalignment that remains:**
  - The model believed the picture matched the target after 1 touch.
  - Her equation note said 3 touches, and the model called it "an automatic analyzer's inference (which may be wrong)".
  - The game did not end at the box, so her count was the right one.
  - This is the case the reflective layer is for: bounce "matched" back with the cells that differ.

## Oct 30: v10d with Jonathan's wall note, submitted

**The wall note** (`mika_layer_core_v10d.py`, `build_v10d.py`), from Jonathan's "walls absorb moves":
- **When it fires:** a direction press the body did not move on, where the square it would enter holds a non-floor colour or the screen's edge.
  - Floor colours are learned from what the moving body leaves behind.
  - The step comes from this level, or else from an earlier level.
- **What it says:** the press was absorbed by a wall, not a dead button. In full once per game; after that, a short line once per button per level, at most 2 per level.
- **The click version** (once per game each):
  - a click on empty floor ("clicks usually act on things, sometimes only within some range of them");
  - a click on a thing that did not react ("that does not mean clicks do nothing").
- **Offline:** 25 public games, 0 errors. The wall note fires in ls20, ka59 and sk48; the click notes fire once in each click game.

**Smoke run (kernel version 13):**
- ft09 6/6, ls20 4/7, vc33 3/7; mean 52.38. Layer on, keep-alive on, no tracebacks.
- vc33 failed its level 4 on budget, the same wall level as on Oct 24. Only two click notes fired there, both early, and the model never referred to them.
- The drop against v10c (76.19) is read as the spread between smoke runs.

**Submitted:** 57794464, kernel version 13 (v10d), Oct 30 05:47 UTC. Pending.

Failure analysis of the 25-game run, and the objective types: `ARC3_FAILURE_MAP.md`.
