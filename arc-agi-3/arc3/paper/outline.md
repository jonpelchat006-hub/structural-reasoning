# Paper outline (working notes) — ARC Prize 2026 Paper Award

Working title: **"Act on what reproduces everything: verify-before-act induction and the cost of learning in ARC-AGI-1 and ARC-AGI-3"**
Authors: Jonathan Pelchat (Shovelcat), with Claude (Anthropic) as research assistant.

## Abstract (draft)
One rule runs through both ARC tracks we entered: an agent may act on a hypothesis only while it
reproduces every observation; otherwise it abstains and looks. On ARC-AGI-1 a per-cell slot filler
built on this rule commits only to rules that reproduce every training pair and survive leave-one-out
re-induction; those commitments are 33/33 correct (train+eval) and lift the eval set from 34 to 41.
On ARC-AGI-3 the same rule drives a frames-only, CPU-only explorer that maps each level as a graph of
states. A look-back lens measures what each won level cost: with the map it ends with, the agent's
shortest route is 0.42x the human's actions, but it spends 61x that route discovering it. The entire
gap to human efficiency is the cost of learning, not of knowing. We study what reduces it ...

## 1. Intro
- ARC-AGI-3: interactive, no instructions, RHAE scoring (squared efficiency, later levels weigh more).
- LLM harnesses dominate the board (Duck; 68.9 top). Our question is different: what can a
  frames-only agent learn from its own presses, and where does its time go?
- Contributions:
  1. verify-before-act as a single rule for static and interactive ARC;
  2. the look-back lens (Jonathan's idea): a per-level waste metric = spent / shortest route in the
     agent's own final map; and lessons carried to later levels;
  3. an honest ablation of exploration heuristics on 25 public games x 8 seeds with the official engine.

## 2. Prior work
- ARC-AGI-3 preview agents: graph exploration (Rudakov et al. "Explore it till you solve it"),
  StochasticGoose (CNN action model). Duck harness (Tufa Labs), Milestone-2 (Franzen).
- Curiosity / novelty search; noisy-TV problem; Go-Explore; model-based RL with verified models.
- Program synthesis with exact verification on ARC-1 (DSL search).

## 3. Approach
### 3.1 Static (ARC-AGI-1): slot filler
- features, raw/abstract modes, consistency + coverage + reproduction; LOO trust; abstain.
### 3.2 Interactive (ARC-AGI-3): Mika's explorer
- state = frame with clock pixels masked (border tickers; pixels that change at the same press count
  in every life regardless of the press);
- candidates: simple actions + one click per same-colour object; kind statistics;
- frontier search: untried > nearest frontier via known edges (+RESET edge); deaths; life budget.
- verified movement model (displacement, looks per direction, passable/blocking/pushable/deadly;
  trusted only after 3 correct, 0 wrong predictions); plan through predicted states.
### 3.3 The look-back lens
- after each won level: BFS in own map from start to the pre-win state -> shortest route;
  waste = spent / shortest; lessons: kinds on route first, goal colour, run structure.
- adaptive momentum: if the won route was runs of one press, explore the next level by runs.

## 4. Results
- Bench: official engine + scorecard, 25 public games, 8 seeds, 3000 actions/game; checked end to end
  against a local competition-mode gateway.
- Table: PriorAgent v10 0.119 | Explorer 0.518 (8 seeds) | ... | Kaggle hidden: v10 0.25, Mika v3n ?
- Look-back table (per game/level: spent, shortest, human).
- Cross-game routes: 183 won levels; final press click 69, A5 29; routes are runs of one press.
- Ablations: movement model (loose 0.389, strict 0.579 vs 0.618 on 4 seeds), diminishing returns
  (0.358), clicks-after-moves (0.520), replay (0.469 vs 0.518, 8 seeds), momentum (0.377/0.399),
  adaptive momentum (0.516, more levels), clock pixels (?).
- Variance across seeds is large (0.34-0.73 per seed); single-run comparisons mislead.

### 4.x The core card: what wins are made of (Oct 23; `claude/ARC3_CORE_CARD.md`)
- 12 slots = 6 rules (control, contact, match, place, count, order) x do-side / mirror side.
- Semantic: the 16 levels the LLM hybrid won (3 games), read from the model's own explanations:
  every win = make something equal to a SHOWN target (16/16); steer + place in all ls20/vc33 levels;
  kills / out-apart never needed. The slots cover every win condition; the work the model did was the
  action model (multi-cell flips, colour cycles, pistons, shared totals, doors).
- Frames, 36 replayed wins / 18 games: the do-side slots cover 32/36 winning presses but are nearly as
  common on arbitrary board-changing presses (only "arrived next to a still thing" lifts, 2.2x).
  Three mirror sides are pure boundaries: blocked / kills / undo are 0-1% of route presses, met in
  32-36 of 36 levels by exploration (the 4/(4-x) asymptote: learned by hitting, never used to win).
- +C: the last win's form carries to the next level only with its bindings (colours): 2-3x lift with
  them vs 1.1-1.5x for the bare slot (14 level pairs, 5 games).
- Negative: twins on a start screen do not mark where to press (0.8-0.9x): matching is the goal test,
  not a probe prior.

### 4.y The hybrid (Duck harness + Franzen M2 + Mika's evidence layer)
- Layer = frame facts only (boards seen, per-key effects, step bar, level digest, before-picture place;
  v6: made-equal patterns same way up at any size, the last win's form with bindings, click footprints;
  v7: click colour cycles, transfers between things). Smoke runs v1-v4: inconclusive (token confound).
- Hidden-set submissions: v3 (Oct 24), ...

## 5. Conclusion
- The gap is learning cost; heuristics move it little and unevenly across games; the lens is the
  right instrument. Limits: no goal inference, no object-level reasoning; next: learned candidate
  order from cross-game look-back; per-game strategy selection by waste.
