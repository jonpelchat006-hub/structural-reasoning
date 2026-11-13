# The sleep organs — digester, trainer, chatbot, distiller, spore, eyes, stats, network, border, flower, porthole (Aug 27–28 2026)

*Everything the planet does BETWEEN lives. All in `Vesica AI\AI Detector\planet\`, ocean root `D:\planet\ocean\`.*

## Channel model that shaped it (Jonathan, Aug 27)
Valves gain a dimension going out: kissing rings = points (keys, instant), a little distance = a line
(text, the speech pressure line, the plan stream), further out = a tube (audio: time × spectrum; video:
time × a 2D face) that the screen plays end to end. Going down toward the core each stage loses a
dimension: video → per-frame atoms → threshold events → laws (a few numbers). Feeding grows the core in
COUNT of invariants, not in dimension. Aug 28 additions: most learned volume lives in the ORTHOGONAL
(context) shells — the core (laws/physics) is nearly measure-zero; rings as widening circles of concern
(self → other → community → society) — body species=self, movers=other, concepts=community,
library=society. "IQ" here = two measurables: shell fill (crystallized) and core↔wall transfer speed
(fluid; lives-to-explained-threshold in a NEW world — run once 3-4 worlds have history).
Teaching direction (Aug 28): stances = demonstration (F8), shadowing (=practice mode), side-by-side
(Darkest Dungeon testbed), coaching, teach-back (F10/reproduction); each yields a prequential curve, so
"which stance teaches fastest" is an experiment to pass on to people.
Prime necklaces + the human roof + the flower-as-view-down-the-tube: see ARC_PRIME_NECKLACES.md.

## 1. digester.py — food
Documents as LINES; threshold/projection/closure bubbles; per-doc digest + .geo; `core_library.json`.
**Run:** 110 docs, 6954 terms, 1014 definitions, kept 825 KB of 4.6 M chars.

## 2. train.py — classical offline training
sklearn MLPs, prequential. hand = behaviour cloning (features incl. mouse delta), human steps ×4;
eye = per-region change predictor. Loaded by the player as untrusted tilt + practice scorer.

## 3. chat.py — the planet's own chatbot
gemma3:4b; tf-idf retrieval over library/narrations/cores/stats; answers only from sediment; misses →
letters. Answers "what was my kda in my last dota game" → "12/3/18" from the watched ledger.

## 4. distill.py — copying the clouds, honestly
Question mining → mailbox → dataset → `planet-gemma3` (prompt copy; LoRA gated on torch). Loop closed once.

## 5. spore.py — the spore's first real AI function
φ-ceiling levels dormant/observe/practice/play; φ rule by measurement; hysteresis both ways; junk-window
filter + 15 s stability gate. Human keys + mouse recorded as expert data. **Survives reboots now:**
`D:\planet\spore_start.bat` copied into the user Startup folder (schtasks was access-denied).
**Watches:** Dota 2 (31 lives), Overwatch (21+, second session through the new stack: eye prequential
0.28 vs 0.70 nothing-changes), Warframe (79), Darkest Dungeon (17).

## 6. rotation.py — the rotation eye
Mouse-driven sheet slide: learned gain, panorama ring, closure = turn width (FOV never told), HUD layer
by stillness. Synthetic: gain 0.512/0.5, ring closed at exactly 900 px, HUD exact.

## 7. stats.py — the stats organ (per-game register learning)
Raw shots every 20 s + at deposits; gemma3 vision enumerates EVERY visible number display → ledger →
skeptical sessions (majority-vote KDA, fabrication signatures, deaths ≤ 40) → `registers.json`: each
label classified budget / accumulator / constant / rare; importance = activity × budget × outcome-link ×
session evidence; co-movement; outcome link needs ≥3 resulted sessions (deaths↔defeat is how KDA EARNS
importance). Synthetic verified; existing noisy ledgers still read all-budget until real sessions.

## 8. rawmouse.py — Raw Input (the Warframe lesson)
WM_INPUT hidden window + INPUTSINK; sees physical mouse motion under cursor lock; verified registered.

## 9. network.py — the stitch into shovelcat-network
Planet sediment → the March-2026 zones (lives .geo → L6-memory, cores/stats/library → L5-facts,
models/panoramas → L4-spacetime, node profile → L0-origin); work orders open→claimed→done polled by the
sleeping spore. First publish: 242 files, 190 .geo loops. The core is the thing passed around.

## 10. border.py — mail arrives at the border
rain.json's context + hypotheses encoded into the eye's 32-symbol alphabet, scrolled as a 2-row ticker
on the frame's top border with tones; same species read mail as game; masked out of the atlas; unread →
charge → lightning. Nothing bypasses perception.

## 11. translation.py — the translation eye
Keys → parallax → depth: rotation-compensated per-region block match, EMA → depth map, layers far/mid/
near/unseen. Synthetic: near and far rows exact; ~58 ms, every 2nd translation look. `depth_<world>.npz`.

## 12. The flower-usage curve
Per look: which of the seven channels engaged (choose() marks its channels, events the rest) → per-life
histogram/mean/mode + mean-on-surprise → core history. Dry run already matches the prediction: mode 2,
mean ~2, surprise steps 3.5.

## 13. porthole.py — the planet's window (built Aug 28, Jonathan's design)
An always-on-top frame whose CENTER IS A HOLE (Windows transparentcolor): whatever is placed underneath
shows through, and the eye captures exactly that screen rectangle (Eye/Player gained `rect_fn` — the
porthole is the window). Showing it something is a physical act: drag a YouTube video, a game, a document
under the hole; "fullscreen hole" covers the play screen. The world name comes from an entry box
('youtube', 'inside', 'reading' each get their own ocean). Side panel = the roof's channels in tabs:
THOUGHTS (live narration tail), CHAT (the planet's own chatbot inline), STATUS (actions, drive, map,
rotation, depth, flower). A HAND checkbox lets it act in that space (Hand with hwnd=None presses the
focused window — click the thing under the hole first); hands-off it reads your keys/mouse as expert
data as usual. The spore ignores the porthole window. Deployed + launched Aug 28 18:06.

## Next
Real session through the full stack; watch something through the porthole (a video = the first
non-interactive world: camera/mover species on footage, no hand); teaching-stance experiments on Darkest
Dungeon; transfer-speed measurement; coalition-shear test at ≥6 worlds; LoRA when torch is installed.
