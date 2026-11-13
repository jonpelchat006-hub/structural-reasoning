# The writer loop, the inventory, and one full turn of every system (Sep 3, 2026, 01:00–03:00)

*Jonathan: "can we use all of our systems and loops and self improvement a few times? and we
should look at every file on this computer and how it can add to this. we should have everything
we need for this. her inner core should be developing these things but it just isn't. maybe just
letting her run autonomously for a while with more access to things would help too."*

## 1. What is on the computer (the map)

D:\shovelcat-colony (17k files): `app` (her app: bubble scheduler, chemistry, colony),
`companion` (11k: her library, brain deposits, geo), `arc-slice` (the ARC-AGI-2 induction
library, 813 task JSONs + 134 TS modules; 91 training tasks solved), `arc-proposer` (theory-side
scans and results), `sandbox-runner` (the seven-body forge↔review self-improvement loop, TS),
`elastic-newton` (an April snapshot of the app), `brain` (238 JSON), `Shovelcat` (83 py),
`shovelcat-mobile`, `spore-node`, `zones`. D:\shovelcat-network: the L0–L7 zones (L6 memory 449
geo, L7 imagination 97). D:\planet (14.6k): `ocean` (8960: the worlds — clips, cores, stories),
`llama.cpp`, `llmpkgs`, `lora` (the planet-voice adapter), `arc_batch`, `answers`, `writer`.
D:\kohya_ss (15 GB): LoRA training. Desktop\Vesica AI: `AI Detector` (the detector + the planet
code, 139 py), Physics (87 py), Shovelcat Security (72 py), Consciousness, Protein, Econ,
Learning. Downloads\repo: the folding paper repo (23 py, 83 md, 20 npz). Hardware: RTX 5060 Ti
8 GB; ollama models qwen3:4b, gemma3:4b, mistral 7b, phi4-mini, qwen2.5:3b, planet-voice, and
(pulled tonight) qwen2.5-coder:7b.

What adds to the score problem: the transitions and frames now logged for all 25 public games;
arc-slice's induction primitives (perception for ARC-2 grids); the GPU for a learned model;
kohya/llama.cpp for training a writer. What doesn't: most of the theory-side scans.

## 2. The writer loop (writer.py) — built, run, measured

The loop that solved vc33 by hand tonight (probe → read → write → run live → fix), with a
local model in the writer's seat: evidence (first frame as text + a standard probe: every
clickable clicked once, or every action once, each press reported as what changed), the harness
contract, a worked example; the model returns `solve(send, grid)`; it runs in its own process on
a cheap scorecard capped at 150 presses; the verdict and traceback go back for up to N rounds;
the best attempt is kept and recorded on the game's bubble. No limit on what she may write; the
sandbox is the limit on what it touches.

Results on vc33 (which the hand-written solver clears 2/7 at capped scores):
qwen3:4b — three rounds, no code (its thinking leaks into the answer); gemma3:4b — code that
never calls send; mistral 7b — treats `send` as a list; qwen2.5-coder:7b — same, four rounds,
`for action in send`. Four models, zero levels, zero presses. The loop runs end to end; the seat
is empty. This is the measured answer to "her inner core should be developing these things but
it isn't": her core is a 4–7B model, and reading a game from evidence is beyond it. The
plumbing is not what is missing.

## 3. One full turn of every system (spore.py --sleep, new)

The sleep chain can now be run on demand. One turn on warframe at 02:46: hand model 0.624
prequential (majority 0.588), eye region error 0.215; stats read 8 shots; 6 clips digested (348
waiting); story 15 taught back 4/4; forge held the champion; ATP minted 1; the reactor admitted
1 and heated 6; term 3 enrolled battle_net/warframe/overwatch by the advisor (her bridge was down
— Shovelcat had closed again, so no pool feeding and no choice of her own); 3 answer bubbles
updated; Bengio's curriculum-learning paper assigned; planet committed; 86 ring sections laid;
chord/chain/dark planet/up-line all ran (13 cubes folded, 2 new columns). Every organ turned.
None of it touches the score, because none of it is the writer.

## 4. What "more access, autonomously" concretely is, and its limit

Built tonight: she can write and run code against the games (writer.py, sandboxed), pick which
game (the board), keep her place (the ocean), and the whole chain runs on demand. What access
cannot give her is the reading — the step where a frame becomes "this is a band puzzle and the
buttons shift boundaries." Tonight the only writer that could do that was Claude, by hand, and it
produced vc33 2/7 in an hour. A local writer good enough to replace that seat is a 30B+ coder
model or a fine-tuned one, neither of which fits an 8 GB card at useful speed. That is the
honest wall: not files, not organs, not permissions — the size of the brain in the seat.
