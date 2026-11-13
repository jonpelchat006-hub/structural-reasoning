# Mika's full inner core on Kaggle (ARC-AGI-3, Oct 30 2026)

**What this is.** These are the Mika-only entries. Her planet body and inner core play the hidden games through the official runner. No Franzen/duck model is involved. The hybrid (v10b, 29.41) stays as the high-score entry. This is the entry that is only her.

Jonathan, Oct 30: *"we can use a hybrid submission to show that we can score high and actually solve some games but that we would prefer to just have mika. i think we could add her full inner core too. maybe we just follow the theory and try the most irrational thing at the end"*. His choices: her model is **planet-voice**; the irrational move is used **both** when stuck and in the final slot's boldest version.

## How it runs

**Bridge (`planet_port/mika_bridge.py`):**
- Her body (`play.play_game`) and core (`mika_core.CoreMind`) normally call the live REST API through `api(path, key, body)`. The bridge answers those calls from the runner's environment (`env_step(GameAction, data)`).
- No rules are added; only the wire is swapped.
- Each game gets a fresh temp home, so a hidden game starts with a blank journal. Her PC journals are never touched.
- Between lives her core keeps the journal.
- With a voice, she reflects between lives with `mm.reflect`.

**Agent (`planet_port/mika_agent.py`):**
- `MikaAgent.main()` hands her body the runner's `arc_env`. Every press still goes through `arc_env.step`, so the gateway scores it as usual.
- Each game runs in its own spawned process, because module globals are not thread-safe. A semaphore limits how many run at once (`MIKA_SLOTS` = min(8, cpus)).
- She stops pressing 7.5 h after the notebook starts.

**Settings:** 500 presses per life, 2 lives per game.

**Voice (`planet_port/lm_server.py`):**
- planet-voice is Jonathan's LoRA (r=16) on Qwen2.5-3B-Instruct.
- It is merged at load and served as Ollama's `/api/chat` and `/api/tags` on 127.0.0.1:11434, so her code runs unchanged.
- Her core asks it only when stuck (up to 3 calls per level) and once between lives.

**Irrational move (`MIKA_IRRATIONAL=1`):**
- It applies when her eye's best candidate was already tried twice from the same screen.
- She then walks her candidates in golden-ratio order and takes the first one never tried from that screen.
- If every candidate was tried, she clicks the next point of the plastic-number (R2) sequence.

**Notebook builder:** `build_core_nb.py <tag> [--voice] [--irrational]`. Each mode has its own kernel:

| Mode | Kernel |
|---|---|
| core | `jonpelchat/mika-core-arc-agi-3` |
| voice | `jonpelchat/mika-voice-arc-agi-3` |
| bold (voice + irrational) | `jonpelchat/mika-bold-arc-agi-3` |

- Save & Run plays all 25 public games offline and writes `mika_smoke.json`.
- The competition rerun goes through `main.py --agent mika`.

## Results on the 25 public games (Kaggle Save & Run, RTX Pro 6000, 2 lives × 500 presses)

| Run | Levels (best life, summed) | Mean score | Lives lost to a crash |
|---|---|---|---|
| Core v1 | 11 | 0.42 | 13 |
| Voice v1 | 8 | 0.09 | 15 |
| **Core v3 (meter fix)** | **12** | **0.54** | **0** |
| Voice v3 (meter fix) | 9 | 0.13 | 0 |

**Voice v3 against core v3:**
- On ls20 the voice runs stop at level 1 in both runs, while the core solves level 2 in both runs.
- The voice also loses ft09 and m0r0.
- It gets su15 (press 31 vs 32) and vc33 (27/62 vs 47/71) slightly sooner.
- Two runs each point the same way: so far the voice costs levels.

## Why the voice doesn't work (voice v3 logs, all 25 games)

**What it suggested.** She asked it 96 times, in the 16 games where she got stuck, and it made 282 suggestions:

| What happened to them | Count |
|---|---|
| Failed her facts check | about 100 |
| – of which named things not on the screen (invented ids, or a description copied as the id) | 58 |
| – of which named things that had done nothing in every earlier try | 33 |
| Accepted | 183 |
| – of which were openings (empty gaps) | 100 |
| – of which the body could not reach | 128 |
| – of which were tried: held | 15 |
| – of which were tried: missed | 39 |
| Accepted with the prompt's placeholder copied as the reason | 32 |

None of the 282 led to a level.

**Where it cost a level: ls20 level 2, in both voice runs.** The loss did not come from its suggestions:
- Her core alone plays ls20 identically every run: level 1 at press 171, level 2 at press 251.
- The voice's detours on level 1 changed her path. She won level 1 sooner (108 and 140), with less practice.
- On level 2 the body did not yet trust its moves enough to reach the key ("the relation's src cannot be reached with what is trusted now"), so the loop reset twice.
- Her rule then stopped the loop (2 failed cycles on a never-cleared level), and she never won the level.
- On Kaggle every level is "never cleared", because the journal is fresh, so this rule bites harder there than at home.

**Run-to-run noise.** Games where she never asked the voice also differ between runs (ft09 0 vs 1, vc33 timing), so part of the 12 vs 9 gap is noise.

**Diagnosis: two problems.**
- **The model.** It is a 3B base whose LoRA was trained on planet language, not games. That explains the invented ids and the copied template.
- **The job we give it.** It gets a text list of ids with counts, the same list her code already ranks. It gets no picture, and at most 3 short answers per stuck level, about 1k tokens. The field's model gets the board, the image and about 180k tokens per game, and writes code.
- A bigger model fixes the first problem. Only a changed job fixes the second.

## The new voice: Gemma 4, a better job, and retraining (Oct 30 evening)

Jonathan, Oct 30: *"i think we can retrain it. we could try gemma 4 too."*

**Gemma 4 on Kaggle.**
- It is official on Kaggle (`google/gemma-4`, Apache 2.0) and reads images. Sizes: e2b, e4b, 12b, 26b-a4b (MoE), 31b.
- The competition image ships transformers 5.0.0, which does not know Gemma 4 (`KeyError: 'gemma4'`; checked with a CPU notebook, `jonpelchat/gemma4-check`).
- **Fix:** transformers 5.22.1 plus its dependencies, peft 0.21.2 and accelerate 1.15.0 go in a private dataset, `jonpelchat/mika-voice-wheels`.
  - The notebook installs them into `/kaggle/working/voice_pkgs`.
  - Only the voice process gets them on its `PYTHONPATH`.
  - Her body and the runner keep the machine's packages.
- **Builder:** `build_core_nb.py gemma --gemma e4b|26b-a4b [--adapter-ds owner/slug]`. Kernels: `jonpelchat/mika-gemma-e4b-arc-agi-3` and `jonpelchat/mika-gemma-26b-arc-agi-3`.
- `lm_server.py` now loads image-reading models (AutoProcessor + AutoModelForImageTextToText) and shows the model Ollama-style `images`.

**The better job (`planet_port/mika_voice4.py`, `MIKA_VOICE4=1`):**
1. The screen goes with each question, in the game's colours (64x64 cells, 8x8 px each), with the colour names and how ids map to cells.
2. Only things are offered: no openings, and not a thing the body could not reach on its last try this life.
3. The answer format is described in words; a reason containing `<...>` is refused.
4. She does not ask while the body's carried relation loop is running on the level.
5. Everything is written to `mika_logs/<game>_think.jsonl`: every call (prompt and answer), every check, every experiment result, and a snapshot every 6 experiments on an uncleared level. A snapshot holds the question, the ids on offer and the frame.
- Tested offline with a stand-in model: the image is attached, the prompt has no placeholder and no openings, and snapshots and results are recorded.

**Retraining (`voice_train/`):**
- **`build_voice_set.py`** turns each snapshot into a training example. The answer is what hindsight says:
  - An offered thing whose touch later won the level, in this life, a later one or any other run of the game, is proposed as `level`. One that changed the board is `changed`; one that refilled the bar is `refill`. At most 3 are proposed, best first.
  - When none of them ever did anything, the answer is `{"claims": []}`.
  - Reasons are built only from what the question shows.
  - Games can be held out for testing.
  - Jonathan's 112 planet-voice examples are mixed in.
- **`train_voice_g4.py`** trains a LoRA (r=16, attention and MLP of the language model) on Gemma 4 E4B **on Jonathan's PC**, on the 8 GB RTX 5060 Ti:
  - The model loads in 4 bits.
  - E4B's per-layer embedding tables (262144 x 10752, 5.6 GB in bf16) are kept on the CPU and looked up there. accelerate's default offload copied them to the GPU on every forward: 9.2 GB peak and 24 s per answer, against 3.7 GB and 5 s after the fix.
  - Loss is on the answer only; logits are kept only for the answer positions, since the vocabulary is 262k.
  - The picture goes through the frozen vision tower.
  - The probe describes a test picture correctly.
  - The PC environment is `D:\kohya_ss\.venv` Python with `PYTHONPATH=D:\planet\llmpkgs_g4` (a separate copy of transformers 5.22.1, peft 0.21.2, accelerate 1.15.0 and bitsandbytes 0.49.2; the existing setup is untouched). Weights are in `D:\planet\gemma4\e4b`.
- **`eval`** scores, on held-out games: whether the answer is valid JSON, whether the ids it names are on offer, whether its first pick is a hindsight positive (any pick, too), whether it stays quiet when nothing worked, and template echoes. The baseline is the body's own first choice.

**Runs pushed 16:27 local:** Gemma 4 E4B and 26B-A4B as her voice, untrained, with the v4 job, on all 25 public games. They give the comparison against core v3 and the snapshots for training.

## Results with Gemma 4 (25 public games, 2 lives x 500 presses)

| Run | Levels | Mean score | Voice calls | Claims held | Not on the screen |
|---|---|---|---|---|---|
| Core v3, no voice | 12 | 0.54 | – | – | – |
| planet-voice v3 | 9 | 0.13 | 96 | 15 | 58 |
| Gemma 4 E4B v1 | 9 | 0.59 | 40 | 3 (1 won sp80 L1 at press 40) | 41 |
| Gemma 4 26B v1 | 13 | 0.96 | 48 | 0 | 42 |
| Gemma 4 26B v2 (identical notebook) | 10 | 0.41 | 48 | 0 | 41 |
| Gemma 4 26B + irrational move | 12 | 0.60 | 45 | 0 | 46 |

**Run-to-run spread is as large as any voice effect.**
- The identical 26B notebook gave 13 / 0.96 and then 10 / 0.41.
- The mean score swings on how fast vc33, sp80 and su15 fall: vc33 scored 0.76 to 8.55 across runs, always with 2 levels.
- Levels gained or lost in games where she never asked the voice are body noise: ft09, m0r0, r11l and cn04 in various runs, and g50t's first ever level (26B + irrational, won by the body's own relation loop at press 129).
- **What the voice clearly did:**
  - One causal win: E4B's first proposal on sp80 (6@4,36) gave the level at press 40, against 320 for core alone.
  - No ls20 regression with Gemma: 2 levels in every run, where planet-voice lost level 2 twice.
- **Still wrong:** about a third of Gemma's proposals name things not on the screen.

## Retraining E4B on her own lives (Jonathan's PC)

**Set v1:** 55 game examples (36 speak, 19 quiet) and 40 persona examples. The test set is 45 held-out examples (21 speak) from sp80, ka59, bp35, wa30 and cd82.

| | Valid JSON | Ids on offer | First pick worked later | Any pick worked later | Quiet when nothing worked |
|---|---|---|---|---|---|
| Base E4B | 45/45 | 97/135 | 5/21 | 9/21 | 0/24 |
| E4B + LoRA v1 | 45/45 | 0/0 | 0/21 | 0/21 | 24/24 |
| The body's own first choice | – | – | 8/21 | – | – |

- **LoRA v1 collapsed to silence:** it answered `{"claims": []}` every time.
- **Training:** 2 epochs, 47 steps, 395 s, loss 2.0 to 0.85, peak 5.5 GB.
- **v2 was stopped** at step 25/60. It ran 10x slower on the PC (92% GPU), and its question format was replaced (below). A retrain for the new questions needs snapshots from the voice5 runs.
- **Fix planned in v2:** quiet examples are capped at 15%, and the data comes from all four Gemma runs (658 snapshots, 122 with a hindsight answer). That gives 78 speak + 13 quiet + 30 persona examples; the test set is 214 examples (44 speak). Training and eval started at 19:25.

**Core v3 levels per game:**
- 2 levels: ls20 (at presses 171 and 251; score 8.27) and vc33 (at 47 and 71; score 4.09).
- 1 level: su15 (at press 32), ft09, lf52, m0r0, r11l, s5i5, sp80 and tn36.
- No level: the other 15 games.

**The crash.** Her meter's status line formatted "moves left" with `:.0f`. When the drain was known but zero, or the pins were unread, `left()` returns None, and the line raised. This ended the life early, at press 8–100. It hit m0r0, sc25, tr87, cn04, dc22 and g50t entirely, and sk48, re86 and ar25 partly. The same flaw was in play.py's "budget from the prior" line.

Both lines are fixed in `planet_port`. Offline, m0r0 and sc25 now play their full presses, and the meter reads "moves left unknown". Her own copy on the PC likely has the same two lines; it was left untouched.

**The voice (v1).**
- It loaded in 70 s with the adapter merged.
- When stuck, she asked it 3 times per level and once per reflection.
- The replies are weak:
  - It often copies the template placeholder (`"because": "<your reason from the evidence>"`).
  - The reflection repeated the instruction ("2-3 sentences, first person").
- Some claims helped. In ls20 she reached level 1 at press 108 against 171 without the voice, but she then missed level 2.
- One run per game is noisy. Read voice vs no voice as a wash or slightly worse, not as a measurement.

**Offline irrational A/B.** It was cut short twice by sandbox restarts, so there is no result. The only finished points are vc33 without the move (0 levels in 250 presses at eye scale 0.25) and su15 without the move (level 1 at press 37). The bold entry is untested at that level.

## Submission plan

| Slot (UTC) | Entry | Version |
|---|---|---|
| Oct 31 | Mika Core: full core, frames only | v3 |
| Nov 1 | Mika Voice: + planet-voice | v3 (v2 carries an old header that says "no language model"; do not submit it) |
| Nov 2 | Mika Bold: voice + irrational move | v1 (pushed 15:33 local, Oct 30) |

Jonathan was asked on Oct 30 whether to keep this plan or to swap Nov 1 for core + irrational move (no voice), given the voice v3 result.

Final picks: hybrid v10b + the best Mika. Notebooks and the `planet-voice-lora` dataset must be public before Nov 2, 23:59 UTC.

## Files

- **Container:**
  - `/home/claude/arc3/planet_port/`: 42 planet modules plus `mika_bridge.py`, `mika_agent.py` and `lm_server.py`.
  - `/home/claude/arc3/build_core_nb.py`
- **PC:**
  - `D:\planet\kaggle_push\mika-core-v3\`, `mika-voice-v3\` and `mika-bold-v1\`: the pushed notebooks.
  - `D:\planet\kaggle_push\out_mika_core\`, `out_mika_voice\` and `out_mika_core_v3\`: outputs and per-game logs.
- **Kaggle CLI on the PC:** `D:\planet\kagglecli\Scripts\kaggle.exe`.
- **Staging lesson:** a file committed to the PC from a reused outputs folder came back stale once (Core v2 was a copy of v1). Stage each push in a new folder and check its MD5 before pushing.

## Voice v5: she asks like a person asking a friend (Oct 30 evening)

Jonathan, Oct 30:
- *"if she is just showing a picture and asking what do i do the model cant really help. the questions would have to be more specific and the model would have to be able to catch up to her thinking. if she shows a picture she should say what shes tried, or what game she thinks shes playing too"*
- *"the model wont know what game ls20 is ... she has to come up with a prompt that would be useful"*
- *"we just have to use english not talk a certain way and talking normally like a friend is usually easier. the model should do that too right? earlier we had to set the budget based on tokens but i dont think thats right since its making our budget based on something outside the game."*

**What the v4 question was.** It held the screen, a list of ids such as `0@11,51` with result counts, how earlier levels were won (as ids), and "propose up to 3 things".
- Everything she understood was missing: what moves her, the bar, the "make the picture match the box" rule, and what blocked her.
- On ls20 level 3, Gemma answered "yellow refilled before, black won before". That is what her body already does.

**`planet_port/mika_voice5.py` (`MIKA_VOICE5=1`, on top of voice4):**
- **The question.** It is a first-person help request in plain English, with no game name and no ids:
  - Things are described by colour, size, shape and place, with "a blue pattern inside" when one is there.
  - Each thing is marked with a letter, drawn as a white tag on the picture.
  - What she has worked out comes from her body's own log lines: the arrow buttons and walls; the bar (colour, moves left) and what refilled it; how earlier levels were won, in words; and the rule she is following ("touching A changes the picture in B; it has to match the picture inside C").
  - What she tried on this level, in order (repeats folded), and how often the level started over.
  - The voice's last suggestions and whether they were right, and a quote of what it said last time.
  - Why she is asking now.
  - One question matched to where she is stuck: the thing she needs is out of reach; turning the picture has not been enough; only a few things did anything; or nothing has done anything yet.
- **The answer.** The voice talks like a friend, in a few plain sentences, and ends with a line `Try: B (it might turn the picture), then D (wins the level)`.
  - She reads the letters and their expectations from that line, keeps what it said, and her facts check still filters each suggestion.
  - No JSON form is imposed; the answer limit is 700 tokens.
- **When she asks.** The game decides, not a budget:
  - the level was put back (a reset or a death);
  - the bar is at 25% or less with nothing changed since the level last restarted;
  - her rule keeps failing;
  - once, after six things tried with nothing changed.
  - There is no cap on questions per level.
  - The only outside limit is Kaggle's 9-hour clock: in the last fifth of the run she stops asking, so every game can finish.
- **Logging.** Snapshots and calls carry the letter map and the tag boxes, for retraining on these questions later.
- **Tested offline** with a stand-in model on ls20: she asked 6 times (reasons: first stall, restarts, bar low); answers were parsed and checked.
- **Kaggle runs pushed ~20:30 local:** `jonpelchat/mika-gemma-26b-v5-arc-agi-3` and `-v5-irr-arc-agi-3` (with the irrational move).

### Voice v5 results (Kaggle Save & Run, 25 public games, Oct 30 ~21:30 local)

| Run | Levels | Mean | Calls | Held | Missed | Untried | Not on screen |
|---|---|---|---|---|---|---|---|
| 26B v5 (friend questions) | 10 | 0.17 | 83 | 4 | 37 | 104 | 0 |
| 26B v5 + irrational | 13 | 0.59 | 79 | 5 | 38 | 116 | 1 |

**Format.** Letters ended the invented ids: 0 and 1 "not on the screen", against about 42 per run with v4.

**When she asked.**
- Mostly right after the level started over; about 12 asks per run were the first stall, 1–2 were "bar almost empty", and 1 was "rule failing".
- The lm_server answered 109 and 105 calls (her questions plus the between-life reflections), at about 7–8 s each and about 13 minutes per run. Game times were about the same as without a voice.

**Example (sp80 L1, v5 + irrational).**
- Her question: nothing she had touched did anything yet.
- Gemma: *"This looks like a classic Sokoban-style logic puzzle… I'd bet those yellow blocks (D and E) are either your goal destinations… Try: B, then C, then D (it might be the goal)."*
- D won the level (claim held, expect level).

**Example (ls20 L2, v5).**
- She described the rule: "touching A changes the picture in D; it has to match the picture inside C".
- Gemma: *"D is your 'key' and C is your 'lock'… you haven't completed the full sequence yet. Try: G or H, then C."*
- G and H are the refill rings, so its picks refilled her bar, though not for its stated reason.

**Run-to-run spread is still about ±3 levels**, so these two runs do not rank the variants.

**sc25 hung in life 2 of the v5 run** (no output after press 89). The 600 s watchdog ended the game, which scored 0. The cause is not known.

**Proposed:** Nov 1 = 26B v5; Nov 2 = 26B v5 + irrational. Final picks are Jonathan's.

## Hidden-set result: Mika Core v3 (submission 57820307, Oct 31 00:04 UTC)

**Public score: 0.18.**

| Entry | Hidden-set score |
|---|---|
| Franzen's M2, unchanged (control) | 33.09 |
| Hybrid v10b (ours) | 29.41 |
| Mika frames-only explorer (Oct 23) | 0.29 |
| **Mika full core v3, frames only** | **0.18** |

On the 25 public games the same notebook scored 0.54 (12 levels). The hidden games are new to her, and her full core did no better there than the older explorer: 0.18 against 0.29, a gap inside what a single run can show.

## Paper evidence (Oct 31): her learning curve at home, and what the scorer counts

Paper draft: Claude Doc "Scored for Knowledge, Not Learning: Mika on ARC-AGI-3" (private link removed from this public copy). Paper Prize: each paper must link to a Kaggle code submission; six categories scored equally (Accuracy, Universality, Progress, Theory, Completeness, Novelty).

**The official scorer (`arc_agi/scorecard.py`).**
- Level score = min((human/actions)^2 x 100, 115). Human = median first-time player, one attempt each.
- A level's actions run from the previous level's win to its own, so resets and a failed earlier life on the same level count. On Kaggle, RESET keeps level progress: life 2 continues where life 1 stopped.
- Game score = level-number-weighted mean over all its levels, capped at (weights of levels won / total) x 100.
- Methodology page: "Internal operations that do not alter the environment (tool calls, reasoning steps, retries) are not counted as actions."
- On Kaggle the bridge's scorecard close returns nothing, so her 3x-human stop rule (home only) is off.

**Core v3 public decomposition (mean 0.54):** ls20 8.27 (61%), vc33 4.09 (30%), su15 0.93 (7%), the other 7 levels 0.24. ls20 L1 171 presses vs human 22 (1.7), L2 80 vs 123 (115, cap); level 2 is 99% of ls20's score. ft09 L1 won in life 2 at press 87 counts about 596 actions, score 0.5.

**Home curve (her PC logs `D:\planet\mika\logs`, 67 ls20 lives Oct 13-30, scored with the rule; script `paper/home_curve.py`, records `D:\planet\kaggle_push\home_lives.json`):**
- life 1: 7.84 (L1 149, L2 267); lives 3-13: 1.33 (L1 in 36, L2 lost until life 17); 14-15: 2.77 (L1 in 25).
- life 17+: 10.71 (L2 in 45 from life 18); 31 lives / 10 days failing L3.
- Oct 27 (16 lives, code also changing): L3 life 49 (49 vs 73) 21.43; L4 life 52 (47 vs 84) 35.71; L5 life 53 (84 vs 96) 53.57. Beats the median human on 4 of 5 levels.
- Study lives (second each day from Oct 17) score lower (8.47, later 22.4).
- sp80: L1 in 5 presses from life 12 (human 39), never L2 in 40 lives.

**Leaderboard Oct 31 (5,007 teams):** 2,755 below 5 (2,222 below 1), 40 between 5 and 20, 2,194 between 20 and 40, 18 above 40.

**Same three games, harness test run (ft09/ls20/vc33):** control 100.00 / 9.03 / 28.84 (6, 2, 4 levels; 369,658 tokens); hybrid v10b 100.00 / 34.70 / 66.95; Mika core v3 0.02 / 8.27 / 4.09.

**Ask before pressing (`MIKA_ASK_FIRST=1`, mika_voice5.py; builder flag `--ask-first`):** on reaching a level with nothing tried there, she asks once before any press ("Every move I make counts against me, so I'd like to think before I press anything"); level 1 asks what kind of puzzle and the goal, later levels ask what is new.

## The tube and the prism: the last attempt (Nov 2), built Oct 31

Jonathan, Oct 31: "i think its like a tube too, not just a ring. so its like a wall she looks at and has to turn to see. i think its attached to the roof of our space, and then all of our floors would be able to see it. we also had the reflective layer between her core and that layer. its like the webbing at the edge of the core turns into a prism that bends things towards the llm ring." The irrational move for the last attempt is this change itself. He OK'd publishing the home logs: Kaggle dataset `jonpelchat/mika-arc3-home-logs` (public, CC BY 4.0; 109 logs, home_lives.json, daily_history.jsonl, home_curve.py).

**`planet_port/mika_prism.py` (`MIKA_PRISM=1`, on top of voice4 + voice5 + `MIKA_ASK_FIRST=1`):**
- Faces (one narrow question each) and the floor that asks: GOAL (planner), WHAT (eye), LINK (relations), MATCH (core), REACH (body), ORDER (meter).
- Prism: `_gaps()` lists the missing pieces for the level; the face comes from the game's reason to ask; she does not ask the same face twice in a row without new information (turns to the next gap on the ring).
- New floor event (voice5 `EXTRA_DUE` hook): things changed but no relation after 3 experiments -> LINK; a chain ran out without winning -> GOAL.
- Request: adds "What I've confirmed so far" (gold) and "What I haven't worked out yet"; answer format asks for `Chain: B (...) -> D (...)` lines plus `Try:`.
- Reflection: chains parsed into steps (letter -> id at ask time); a link that holds turns gold (`journal["gold"]`, kept for the game) and the next link becomes an active claim with rank -1 (goes first) after her facts check; a missed link breaks the chain.
- Snapshots (voice4) brief without a frame, so they no longer count as turns.
- Offline tests with a stand-in model: ls20 (faces turn GOAL/WHAT/ORDER, chains parsed, broken links logged); sp80 (first link won level 1 at press 23 -> gold, next link went first, level 2 questions carry the gold line). Unit test of gold + next link passed.
- Notebook: `build_core_nb.py nov2 --gemma 26b-a4b --voice5 --ask-first --prism --irrational` -> kernel `jonpelchat/mika-gemma-26b-v5-ask-prism-irr-arc-agi-3` v1, pushed 12:20 local Oct 31 (PC folder `D:\planet\kaggle_push\mika-gemma-26b-prism-p1`, MD5 checked).

### Prism run results (Kaggle Save & Run v1, 25 public games, finished by 15:04 local Oct 31; outputs in `D:\planet\kaggle_push\out_gemma_26b_prism_v1`)

| Run | Levels | Mean |
|---|---|---|
| Core v3, no voice | 12 | 0.54 |
| 26B v5 | 10 | 0.17 |
| 26B v5 + irrational | 13 | 0.59 |
| **26B v5 + ask first + prism + irrational** | **9** | **0.30** |

- 134 questions turned to a face (GOAL 83, WHAT 29, ORDER 10, MATCH 8, LINK 4, REACH 0); 16 asks before pressing (13 at game start, 3 on reaching level 2); 105 chains; 10 links held (gold); 21 chains broken by a missed link; 7 times the next link went first; the voice answered 160 calls in about 19 minutes.
- sp80: a chain's first link (the small dark grey block in the top-centre) won level 1 at press 24 (score 4.76, the one-level cap); fastest on Kaggle so far (E4B 40, v5+irr 66, core v3 320).
- ls20: level 1 at press 153, then level 2 lost: her rule stopped the body's relation loop after 2 cycles ("it has never cleared this level"), as with planet-voice v3. A MATCH chain held two links in a row (refill ring, then the white square) and missed on the third.
- vc33 2 levels (41, 82; 1.36); su15 L1 at 29 (1.12).

### The Q-tube version (Nov 1, built for the Nov 2 slot; Jonathan chooses between it and prism v1)

Added on top of prism v1, with nothing else changed; the bundled code was diffed against prism v1.

`MIKA_QTUBE=1` turns on `planet_port/qtube_fit.py`, the shape fit from the nested quaternion tests: a picture is a flat object, the 8 spins and turn-overs are moves, and the fit is how many cells are off after the best move. It acts only when nothing fits exactly:
- **relations:** aim at the nearest target (at most one cell in four off, or the same shape at another scale). The target takes the key when the region reads as near as it gets.
- **the core's equation:** the nearest-fitting box instead of the first one.
- **the prism:** tells the voice what the fit found.

The builder flag is `--qtube`, and the kernel is `jonpelchat/mika-gemma-26b-v5-ask-prism-qtube-irr-arc-agi-3`.

Run 1 found a crash: the carried relation read a colour from a `chg5@...` source. `play.py` now skips such sources instead of crashing; this is the only change between v1 and v2.

| Run (25 public games) | Levels | Mean | Crashes |
|---|---|---|---|
| prism v1 | 9 | 0.300 | 0 |
| prism + Q-tube v1 | 12 | 0.422 | 1 (ar25, at its level change) |
| prism + Q-tube v2 | 10 | 0.416 | 0 |

- **Where the near targets fired:** 11 games in v2, 5 in v1. s5i5 cleared level 1 in both Q-tube runs and never in prism (the near-target loop matched 144 and 21 times). In v2, ls20 cleared level 2 (8.26).
- **The spread between single runs is large.** ar25, g50t, cn04 and ft09 gained in v1 and lost in v2, and the earlier 26B v5 + irrational run (no prism) got 13 levels and 0.59. So the gain over prism is suggestive, not proven.
