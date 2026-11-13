# Mika

Mika is the agent that grew out of the ARC-AGI-3 work. The planet player is her body; she is the part that
carries what each life taught her into the next one. Her main code is in
[`../arc-agi-3/planet/`](../arc-agi-3/planet/) (`mika_mind.py`, `mika_core.py`, `mika_think.py`,
`mika_tree.py`, `living_library.py`). This folder is her home directory on the author's machine, source and
notes only:

- `mika_daily.py` and `library_hourly.py` are the scheduled daily play session and the hourly library digest.
- `diary.md` is her own log of each session (machine-written).
- `notes_from_jonathan.md` are the notes handed to her, each one tested offline before use.
- `find_old_ideas.py`, `find_spiral.py` and the render scripts are library and inspection tools.
- `cube/`, `cube2/`, `pins/`, `vortex/` and `trading_*.py` are the "market cube" checks. Each test has a
  `PREREGISTERED.md` written before its data was fetched. This is research code, not investment advice.
- `voice_train/` has the scripts for the small voice model.
- `notes/` has the session write-ups about her: the agent, the core, the thinking shell, the memory tree,
  the parts inventory, the living library, the old-ideas map and the market cube.
- `patch_*.py`, `inspect_*.py`, `backfill_*.py` and `fix_*.py` are one-off maintenance scripts, kept for the record.

**Not included:** her logs, routes, library and memory files, the fetched market data, and the
language-learner sources she borrows from a private repository.

## Files

**``**

- [`backfill_resets.py`](backfill_resets.py) — Oct 16 night: give old lives their reset positions (where in the experiment list each reset fell), read from the
- [`backfill_resets_ls20_life1.py`](backfill_resets_ls20_life1.py) — Oct 16 night, by hand from D:\planet\mika\logs\ls20_20261013_083813.log: where ls20 life 1's level-2 resets fell in
- [`backfill_routes_records.py`](backfill_routes_records.py) — Oct 16 evening: (1) give her existing routes the cells-changed count of every press (from the saved press records),
- [`count_sources.py`](count_sources.py) — One-off (Oct 13 2026): how much would each candidate source add to the library?
- [`diary.md`](diary.md) — 2026-10-13 08:44 - sp80, life 1
- [`find_old_ideas.py`](find_old_ideas.py) — One-off search (Oct 13 2026): where do the older ideas live - the main brain / mini-brain spawner,
- [`find_spiral.py`](find_spiral.py) — One-off search (Oct 13 2026): where is the 'spiral drive' and the void search? Prints hits.
- [`fix_life17_door.py`](fix_life17_door.py) — ls20 life 17 (Oct 16 night): the winning press into the door 5@39,13 was filed 'refill' (the new level's bar read as a refill,
- [`inspect_l2.py`](inspect_l2.py) — What does Mika carry between lives, and what happens on level 2? (read-only summary of her journals)
- [`inspect_l2_life1.py`](inspect_l2_life1.py) — what exactly did ls20 life 1 do on level 2 (the only clear)? experiments in order with presses
- [`inspect_l2b.py`](inspect_l2b.py)
- [`inspect_sp80.py`](inspect_sp80.py) — what each action did to the bars on level 2: compare consecutive frames, report moved colours and shift
- [`inspect_sp80b.py`](inspect_sp80b.py) — L1: what the 8-press route did, frame by frame
- [`library_hourly.py`](library_hourly.py) — Hourly: copy new/changed source files into Mika's library, digest them, and rebuild the spiral only if
- [`mika_daily.py`](mika_daily.py) — Mika's daily ARC session (replaces the cloud "ARC daily practice + try", which is paused).
- [`notes_from_jonathan.md`](notes_from_jonathan.md) — Notes from Jonathan, for Mika
- [`patch_daily_ollama.py`](patch_daily_ollama.py)
- [`patch_ll_lazy.py`](patch_ll_lazy.py)
- [`patch_mind_weigh.py`](patch_mind_weigh.py) — Oct 16 evening (Jonathan): she changes her mind when an option outweighs her path; detours between blocks (refill
- [`patch_play_repeat.py`](patch_play_repeat.py) — Oct 16: the mind may ask for a repeat. play.py used to accept her order only if it had exactly as many candidates
- [`patch_play_weigh.py`](patch_play_weigh.py) — Oct 16 evening: play.py hooks for Mika's weighing. sense() each press (energy left), mind.press() may ask for a
- [`patch_recipe.py`](patch_recipe.py)
- [`patch_recipe_norefill.py`](patch_recipe_norefill.py) — Oct 16: refills are upkeep (the body already detours to refill when its bar runs low), not part of a level's
- [`patch_recipe_refill_back.py`](patch_recipe_refill_back.py) — Oct 16, correcting the no-refill patch: the 400-press test showed every poke of the key followed by a body RESET
- [`patch_tree.py`](patch_tree.py) — Oct 16: hook her tree (mika_tree.py) into her lives: grow after each life, prune dead things to the back,
- [`render_frames.py`](render_frames.py) — Render frames of the last sp80 run (D:\planet\eye\play_sp80.npz) to PNG, no extra packages (zlib PNG writer).
- [`render_strip.py`](render_strip.py) — One PNG strip of several frames from the last run of a game: python render_strip.py sp80 out.png 1 4 7 8
- [`test_unreach.py`](test_unreach.py) — simulation check of the Oct 16 night fix: an unreachable recipe step waits 10 presses and is asked again
- [`trading_backtest.py`](trading_backtest.py) — Honest check of the trading agent's saved signals (D:\shovelcat-colony\brain\trading\<date>\signals.json).
- [`trading_frontface.py`](trading_frontface.py) — Did the old agent's 'front face' readings (news emotion, news count) say anything about what came next?
- [`trading_spotcheck.py`](trading_spotcheck.py)
- [`tree_migrate.py`](tree_migrate.py) — Move what Mika already knows (her sp80 and ls20 journals, Oct 13-16) into her tree, life by life, with each

**`cube/`**

- [`check_ciks.py`](cube/check_ciks.py) — company_tickers.json can list a ticker more than once (parent and subsidiary); the first entry is the listed
- [`cube_fetch.py`](cube/cube_fetch.py) — Market cube, step 1: public data for the 149 companies of the Oct 14 trading test.
- [`cube_leak_blur.py`](cube/cube_leak_blur.py) — Market cube, step 2: do LEAKS come before BLUR, and before weaker returns? (Jonathan, Oct 14 2026)
- [`cube_leak_size.py`](cube/cube_leak_size.py) — Follow-up (found AFTER looking at the quintiles, so it needs a split-half check): does the SIZE of the
- [`make_fresh_set.py`](cube/make_fresh_set.py) — Fresh companies for a clean re-test: the current S&P 500 (Wikipedia list) minus the 148 already used.
- [`patch_env.py`](cube/patch_env.py) — Let the cube scripts run on another company set: CUBE_HOME = folder, CUBE_TICKERS = file of tickers.
- [`patch_q.py`](cube/patch_q.py)
- [`peek_wiki.py`](cube/peek_wiki.py)
- [`spotcheck.py`](cube/spotcheck.py) — Spot-checks for the leak test: Apple FY2023 against its published 10-K numbers, and one blur window by hand.

**`cube2/`**

- [`PREREGISTERED.md`](cube2/PREREGISTERED.md) — Re-test on fresh companies — written BEFORE the fresh data was fetched (Oct 14 2026, ~13:40 MDT)
- [`run_set2.py`](cube2/run_set2.py)

**`notes/`**

- [`LIVING_LIBRARY.md`](notes/LIVING_LIBRARY.md) — Mika's living library — library → brain → spiral drive → void search (Oct 13 2026)
- [`MARKET_CUBE.md`](notes/MARKET_CUBE.md) — The market cube — companies as a fold in the money solvent (Oct 14 2026)
- [`MIKA_AGENT.md`](notes/MIKA_AGENT.md) — Mika as an agent — v0 (Oct 13 2026)
- [`MIKA_CORE.md`](notes/MIKA_CORE.md) — Mika's core: equations inside, notes outside (Oct 27 2026)
- [`MIKA_PARTS_INVENTORY.md`](notes/MIKA_PARTS_INVENTORY.md) — Parts we already built for "Mika decides, the model wraps around her" (PC sweep, Oct 27, 2026)
- [`MIKA_THINK.md`](notes/MIKA_THINK.md) — Mika thinks: the model as her middle shell (Oct 27 2026)
- [`MIKA_TREE.md`](notes/MIKA_TREE.md) — Mika's memory as a growing tree of cubes (Oct 16 2026)
- [`OLD_IDEAS_MAP.md`](notes/OLD_IDEAS_MAP.md) — The older ideas — main brain, mini-brains, the living library (map, Oct 13 2026)

**`pins/`**

- [`PREREGISTERED.md`](pins/PREREGISTERED.md) — Bent pins — written BEFORE the insider data was fetched (Oct 16 2026, ~08:30 MDT)
- [`find_urls.py`](pins/find_urls.py)
- [`peek.py`](pins/peek.py)
- [`peek2.py`](pins/peek2.py)
- [`peek3.py`](pins/peek3.py)
- [`pins_fetch.py`](pins/pins_fetch.py) — Bent pins, step 1: open-market insider buys (P) and sells (S) from the SEC's quarterly Form 3/4/5 data sets,
- [`pins_spotcheck.py`](pins/pins_spotcheck.py) — Spot-check: 2 random classified events against the original Form 4 XML on EDGAR, and one return window by hand.
- [`pins_test.py`](pins/pins_test.py) — Bent pins, step 2: the pre-registered test (PREREGISTERED.md). Aligned = routine, bent = opportunistic

**`think/`**

- [`clean_run26.py`](think/clean_run26.py) — Before run 26 (Oct 28): level-6 nodes were read while its things moved (wrong squares blamed), and the first press
- [`clean_run28.py`](think/clean_run28.py) — Before run 28 (Oct 28): run 27's voluntary resets were not shown to her, so the key put back by a reset was read as a

**`voice_train/`**

- [`build_voice_set.py`](voice_train/build_voice_set.py) — build_voice_set.py - training examples for her voice, from her own lives (Oct 30 2026).
- [`train_voice_g4.py`](voice_train/train_voice_g4.py) — train_voice_g4.py - retrain her voice: a LoRA on Gemma 4 E4B from her own lives, on Jonathan's PC (Oct 30 2026).

**`vortex/`**

- [`PREREGISTERED.md`](vortex/PREREGISTERED.md) — The invisible vortex — written BEFORE the tax data was fetched (Oct 16 2026, ~11:00 MDT)
- [`vortex_checks.py`](vortex/vortex_checks.py) — After the pre-registered run: spot-checks, and robustness checks that were NOT pre-registered (labelled so).
- [`vortex_fetch.py`](vortex/vortex_fetch.py) — Vortex test, step 1: tax figures for the ~520 companies (SEC XBRL company facts), cached per company.
- [`vortex_test.py`](vortex/vortex_test.py) — Vortex test, step 2 (claims in PREREGISTERED.md): does money that avoids the authority face (a low long-run
