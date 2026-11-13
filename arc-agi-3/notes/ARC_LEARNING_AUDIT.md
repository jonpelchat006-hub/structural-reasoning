# Learning audit — what the planet actually learns, measured (Aug 29)

*Jonathan: "it just keeps repeating the same thoughts. how much is it actually learning? maybe it can
use the sandbox we made, or giving it tools... or you could try using everything we have to see
what's missing." This doc is the answer, from the machine's own numbers, worst news first.*

## 1. The repeating thoughts: diagnosed and fixed

The Dota witness thread held 23 near-identical lines — every one a copy of gemma's throat-clearing
("Okay, here's my analysis based on the provided information and the visual:"). The parser took the
FIRST line of each answer as the observation; gemma always opens with preamble; so the wake filled
with preamble, which then rode back in as context and locked the loop harder each pass. The PREDICT
parser was worse: it matched gemma's echo of our own instructions, so "predictions" like "ion came
true or failed, say so in passing" were fragments of the prompt reflected back. The antenna said so
honestly the whole time: 4 fed / 49 broken. Fixed: strict OBS:/PREDICT: format, preamble and
instruction-echo filters, and a dedupe law — a look that repeats the last memory does not grow the
line (the wake records movement, not water sitting still). The poisoned thread was wiped. Also: the
session was landing in the junk 'porthole' world because the world box wasn't set — the porthole
world name matters.

## 2. How much is it actually learning? The numbers

Per world: lives | concepts | open ends | insights | practice hand-accuracy first→last:

- warframe: 100 | 64 | 0 | 0 | 0.23→1.0 (24 pts) — REAL learning early; the 1.0 is partly the
  majority class ("wait" while he stands in menus), prequential vs majority was 0.57 vs 0.58: the
  hand model is barely above baseline. Honest grade: weak-real.
- overwatch: 57 | 2 | 0 | 0 | 0.19→0.61 — the clearest genuine hand-model improvement.
- dead_cells: 44 | 38 | 0 | 0 | 0.41→0.16 (DECLINING — recent points straddle the chord-vocabulary
  change that invalidated old models until retrain; watch whether it recovers).
  Concepts 11→38 in one day: the margin-band fix is doing real work on real data.
- dota_2: 91 | 2 | 0 | 0 | no practice points at all. NINETY-ONE LIVES, TWO CONCEPTS. The world he
  watches most is the world it learns least — the atom vocabulary (mover/counter/body, tuned on
  platformers) barely fires in a MOBA, and the witness that was meant to carry Dota understanding
  was eating preamble.
- battle_net: 47 | 60 | — a MENU produced more "concepts" than Dota: co-occurrence in a static
  window makes concept-shaped noise. Red flag for concept QUALITY, not just quantity.
- Insights fired on real game worlds: ZERO. The only open ends live on junk worlds (planet_porthole
  12/12 cap, porthole 7). The creativity organ runs on window-manager noise, not on games.

What genuinely accumulates today: laws with evidence (movement displacements per key), stats
registers (torch/stress/xp/souls/gold as budgets, with outcome links), concepts (only since the
band fix), panoramas/depth maps, the witness thread (only since the parse fix), story teach-back
scores. What does NOT learn: the gemma layer itself — frozen weights narrating; whatever it
"understands" evaporates except what lands in a file. The planet's real memory is the files; the
LLM is a mouth, not a mind.

## 3. What's missing, found by walking everything we have

The machine holds, outside the planet: D:\shovelcat-colony with **sandbox-runner** (the seven-body
forge/review engine: forge = hold a candidate tool upgrade, run it against reference jobs from
production history, promote only if it wins; review = check outputs against an external aperture;
coupled by the φ_close ring — review failures become forge specs), **spore-node**, TOOL_SPEC_64.md
(64 tools derived from the codon table), the shovelcat-network zones (stitched already), kohya_ss
(LoRA training — the distillation path that was blocked by no-torch may be unblockable here), and
the Demo/detector code. The colony had the missing organ built all along:

**The planet can perceive and act, but it cannot EXPERIMENT ON ITSELF.** Every improvement so far
was made by Claude (the clouds) editing code. The sandbox-runner is the shape of self-improvement:
a place where a candidate change — a witness prompt, a threshold, a new atom extractor, a tool —
is run against RECORDED history (we have 289+ lives, 67 clips, threads) and promoted only when a
measured number improves. The planet already has the fitness functions (antenna feed rate,
prequential accuracy, teach-back score, sediment ratio) and the job plumbing (work orders in
L0-origin). What it lacks is the forge loop connecting them.

## 4. The build list this audit orders

1. DONE: witness parse fix + dedupe + wipe of the poisoned thread.
2. Forge job for the sleep: adapt sandbox-runner's loop (or a thin python port of its law) —
   candidate witness-prompt / threshold variants replayed against stored clips; fitness = antenna
   feed rate on held-out stretches; winner promoted into a config the porthole reads. First
   self-improvement loop, gated by measurement (the ratchet, finally load-bearing).
3. Dota needs MOBA atoms: the stats organ already reads kills/gold/xp — those readings should enter
   the EVENT stream as atoms (counter.gold.up etc.) so mine_candidates has something real to chew.
   91 lives of Dota deserve more than 2 concepts.
4. Concept quality gate: translatability/drain audit over the registry; battle_net's 60 menu-
   concepts are the test case for a junk filter (a concept earned only in a world where nothing
   was ever at stake should rank below one that survived deaths).
5. The chord-change regression in dead_cells hand models: confirm retrain recovers accuracy.
6. LoRA via kohya_ss: the distill loop can finally train weights, not just prompts — the only
   path by which the mouth itself learns.

## 5. The honest one-line answer

How much is it actually learning? Laws, registers, and (since today) concepts: really, but
shallowly and unevenly — strongest exactly where the games are simplest, near zero on Dota, with
zero insights on any real world yet, and no mechanism that improves the system by itself. The
repeating thoughts were a parser bug feeding the wake its own preamble, now fixed and honestly
scored by the antenna. The missing organ has a name and a folder: the forge. It was built in the
colony months ago and has been waiting to be stitched in.
