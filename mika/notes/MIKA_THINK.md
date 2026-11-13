# Mika thinks: the model as her middle shell (Oct 27 2026)

Jonathan, Oct 27: "our inner core was supposed to go inside the llm and have it wrap around us, it is supposed to be a
layer she can swap out. the llm was the middle shell and we have the inner one. she is supposed to make it work better or
more efficiently. she can use it but it should still be her deciding things."

Then: "you can start there. we have done a lot of research since doing those ideas so we will probably have to update
them though."

This doc records what was built from the old consciousness work, what changed from the old ideas, and what six runs on the
public games showed. Code is on the PC in `Desktop\Vesica AI\AI Detector\planet\`.

## What was built

- **mika_think.py**. A subclass of `mika_mind.MikaMind` called `ThinkingMind`. `mika_mind.live()` builds her mind
  through the module name, so the daily task is untouched. Usage:
  `python mika_think.py ls20 --presses 400 --shell planet-voice` (or `qwen2.5-coder:7b`, or `none`).
- **play.py hook** (patch_play_relation.py; backup `play.py.bak_20261027_before_allow_relation`). The body asks
  `mind.allow_relation(level, relation)` before it starts or restarts its relation loop. The call is guarded by
  `hasattr`, so the daily MikaMind, which has no such method, behaves exactly as before.
- **Logs**:
  - Every shell call, check, review, veto and lapse goes to `D:\planet\mika\think\<game>_<stamp>_<shell>.jsonl`.
  - Each run's stdout is in `run<N>_<game>_<shell>.out`.
  - Every shell's running record (calls, claims, rejected, tried, held, missed, untried, seconds, tokens) is in her
    journal under `shells`.
  - Every claim and its outcome is in her journal under `claims`.
- **Journal snapshots** before each run, in `D:\planet\mika\think\`: `ls20_S0..S4_*.json` and
  `sp80_S0_before_think.json`. Nothing was overwritten or deleted.

## The four roles, old and new

The old loop (Shovelcat-AI/lib/agents/consciousness-loop.ts, Mar 2026) had four roles, and the LLM played all four.
The update gives the model one role. Mika plays the other three in her own code.

| Role | Old (Mar 2026) | Now (Oct 27) | Research it draws on |
|---|---|---|---|
| Imagination | LLM generates ideas | **The only role the model plays.** It is called only when she is stuck: 6 experiments on an uncleared level with no route, at most 3 calls per level per life, 3 claims per call, 400 tokens out. Each claim is a thing to try, the result she should expect (`changed`, `refill`, `level` or `pass`), and why. | LLM_EQUATION_MAP: the outer, generated terms. Hybrid v9's token lesson: never call the model by default. |
| Memory | LLM summarises the context | **Her journal**: routes, recipes, relations, what every thing did in every life, and claims that held or missed. The shell gets this evidence in her terms (levels won and how, relations, things on the screen with their result counts). | mika_mind (Oct 13–16), the core card. |
| Facts | LLM checks itself | **Her code, no model.** Forge, before the press: the claim must name a thing that is on the screen, expect a result the body can see, and not repeat a claim already tested this life. It must not expect an effect from a thing that did nothing in 3+ tries while nothing on the level changed, or expect a pass through a thing that was always a wall. Review, after the press: held (a proof she keeps), missed (a question she keeps), or untried (the body never got there, so no evidence either way). | The A=B=C slot-filler rule: a claim counts only while it reproduces every observation. Forge/review from the proxy exam. |
| Planner | LLM plans | **mika_mind**: bands, routes, recipes, detours, weighing. A checked claim goes to the front of the frontier, after her own recipe steps and cleared-level effects. **New:** she can veto the body's relation loop on a level she has never cleared, after 2 cycles per life. | The planner bands, the relation work. |

The equation map's split (f(task) = Σ inner certified + lim outer generated) is now concrete:

- A claim that held is a certified inner term.
- The shell's output is the outer generated term, and it never becomes a press without passing her facts check.

## Runs (Oct 27, public games, push mode)

Each run started from the journal the run before it left. That is how she lives, but it means the runs are not
independent A/B trials. Baselines:
- **ls20:** 2 levels in 400 presses in every life in her journal from life 17 (Oct 16) to life 37 (Oct 26).
- **sp80:** 1 level in 300 presses in every daily run checked (Oct 24–26).

| Run | Game | Shell | Code | Levels | Calls | Claims | Rejected | Tried | Held | Missed | Untried | Shell time | Tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ls20 | planet-voice | v1 | 2 | 3 | 6 | 6 (format) | 0 | 0 | 0 | – | 38 s | 5,630 |
| 2 | ls20 | planet-voice | v2: example in prompt, relation veto (counted starts; see finding 3) | 2 | 1 | 3 | 0 | 2 | 0 | 2 (walls) | 1 stuck | 15 s | 1,842 |
| 3 | ls20 | qwen2.5-coder:7b | v3: lapse | 2 | 3 | 9 | 2 | 7 | 1 (a `pass`) | 1 + 5 unreachable | – | 46 s | 5,730 |
| 4 | ls20 | none | v4: unreachable counts as untried | 2 | – | – | – | – | – | – | – | – | – |
| 5 | sp80 | planet-voice | v4 | 1 | 3 | 5 | 2 (invented ids) + 1 broken JSON | 1 | 1 (a `pass`) | 0 | 2 | 30 s | 2,964 |
| 6 | ls20 | planet-voice | v5: objects first, deduped relations, lenient parse | 2 | 3 | 9 | 5 | 1 | 0 | 1 (wall) | 3 | 32 s | 5,728 |
| 7 | ls20 | qwen2.5-coder:7b | v5 | 2 | 2 + 1 timed out | 6 | 1 | 1 | 1 (a `pass`) | 0 | 4 | 305 s + 300 s timeout | 3,978 |

In runs 6 and 7 her evidence showed the real things first, for example:

- 14@46,31: changed x80;
- 11@16,35: refill x48;
- the rotator 0@11,51.

Neither shell made use of them:

- **planet-voice** answered its first v5 call with expectations of `nothing`, `wall` and `unreachable`. All three were
  rejected.
- **planet-voice** spent its next two calls on openings.
- **coder** claimed the rotator would `refill`, citing "it has been successful in refilling before", which is false.
  It also copied the example's reason almost word for word.

During run 7 the GPU was also running a game, at 99% use and 7.7 of 8 GB.

- Coder's calls took 178 s and 126 s, against about 15 s earlier in the day.
- The third call hit the 300 s timeout.
- The body sat still while it waited: the life log is silent from 9:53 to 9:59.
- The end-of-life reflection timed out in runs 6 and 7.
- qwen2.5-coder:7b stays loaded in VRAM indefinitely: Ollama's keep-alive expiry reads year 2319, so keep-alive is
  set to forever.

## What the runs showed

1. **No shell has cleared a new level yet.** Every run matched the baseline. The one claim type that ever held is
   `pass`, which says almost nothing.
2. **Her facts check works.** It caught:
   - template echoes (`changed|refill|level`);
   - expectations the body cannot see (`wall`);
   - ids the model invented (`not on the screen now`);
   - repeats.

   Nothing unchecked reached the body.
3. **Her relation-loop veto, as built today, stopped the wrong thing.** It is the first planner decision she makes over
   the body.
   - **The intent.** In run 1 the body's loop ran 6 cycles of about 31 presses on ls20 level 3, each ending in a budget
     reset. After 2 cycles she should stop it and give the presses to the frontier.
   - **What v2–v5 actually did.** They counted loop *starts*, not cycles. Two starts with the source out of reach ("the
     relation waits for the next sleep") were enough. In lives 39–43 the loop never touched the rotator: 0 changes,
     against 10–11 in every push life before, including run 1.
   - **The fix.** v6 counts only a reset or a death during the loop as a cycle. No run has used v6 yet.
4. **Claim bookkeeping needed three fixes.**
   - *Lapse.* A claim the body never reaches (it left the frontier) used to block every later call. It now lapses after
     6 experiments.
   - *Untried.* `unreachable` or `untestable` used to count as a miss. It is now "untried": no proof, no question.
   - *Lenient parse.* A broken JSON answer used to lose the whole call. Each claim object is now read on its own.
5. **Level 3 is not short of things to try. It is short of a way to combine them.** By life 38, before today, her journal
   had all of these on level 3:

   | Thing | Changed the board | Refilled |
   |---|---|---|
   | Rotator 0@11,51 | 110 times | – |
   | 8@47,32 | 164 times | – |
   | 14@46,31 | 78 times | – |
   | Ring 11@16,35 | – | 48 times |
   | Ring 11@31,20 | – | 15 times |

   Level 3 has still never been cleared.

   - **Push lives**, the daily's first run each day: the loop turns the rotator 10 or 11 times a life (lives 17–38), yet
     level 3 is never cleared.
   - **Study lives** turn it 0 times.
   - **Today**, with the miscounting veto (lives 39–43), it was turned 0 times, and the presses went to openings and to
     8@47,32 and 14@46,31 (3 more changes each). Runs 3 and 4 hit 25 and 13 "dead end" resets.

   With or without the rotation, she stops at level 2.

   The likely missing piece, a hypothesis that fits the ARC3_LIVE_PLAN.md notes on colour changers after level 2:
   - Matching the key to the target on level 3 needs more than one changer: rotation, plus colour or shape.
   - The body's relation reader holds one "touch X until the pattern matches Y" at a time.

   A claim that names a single thing cannot express a combination. A plan can, for example "touch 8@47,32 until the
   colour matches, refill at 11@16,35, touch 0@11,51 until the rotation matches, then go to 5@49,53".
6. **The prompt had hidden the important things.** Run 2's first prompt listed 28 openings and never showed the rotator,
   the rings or the changers. v5 puts things first and openings after. Run 6 is the first run with that evidence.
7. **The prompt's example anchored the coder.** In runs 3 and 7 coder copied the example's reason almost word for
   word, and both shells preferred openings. v6, now on the PC and not yet run, has:
   - an example with no reason and no effect in it;
   - a rule that `because` must cite the evidence.
8. **Cost is small while the GPU is free.**
   - About 15 s and about 1.9k tokens per call on the 5060 Ti, with 1 to 3 calls per level per life. That is under
     1 minute of model time per 400-press life.
   - The hybrid's problem (a model on every step, 120 games sharing one GPU) does not arise here.
   - When the GPU is shared, a call can take 2 to 5 minutes and the body waits. The shell call should not block the body.
     Ask in the background and let the body keep exploring until the claims arrive.

## Next, in order

1. **Read level 3 directly.** Which shown pattern does each of 8@47,32 and 14@46,31 change? The body's antennas already
   log "caused 36" for each. That is a code question for her, not a model question, and it tells the planner what the
   chain must be.
2. **Claims as plans.** Let a claim name a short chain: touch A until X matches, then B until Y matches, then go to the
   target. Her facts check the chain against the reach map and the budget, and the body walks it as a recipe of
   relations. This is the step that matches the ls20 level-3 blocker (finding 5).
3. **Give the shell what changed.** For each `changed` thing, say which shown pattern or HUD cell changed (the body
   already knows this from the relation reader and the antennas). Without it the model is guessing from ids.
4. **Retrain planet-voice on her own life.** The journal now holds claims with outcomes. Train the LoRA on her held
   claims, recipes and relations, the "open weight she can do what she wants with" step. The old adapter
   (Aug 29, Qwen2.5-3B, `D:\planet\lora\`) knows planet language, not games. Run 5 shows it inventing ids.
5. **Do not block the body on the shell.** Ask in a background thread and keep exploring until the claims arrive (see
   finding 8).
6. Keep the daily task on plain MikaMind until a shell run clears a level the baseline does not.
