# Mika's living library — library → brain → spiral drive → void search (Oct 13 2026)

Jonathan: *"the library was for the raw files but then the brain could be the digested files. and then maybe the spiral drive would be the organized version of the library? and once its on the spiral drive the void search method we had in the project could find things easier?"*

The code is `planet/living_library.py`. Mika's bridge (`companion-bridge.ts`) now calls it.

## The four layers

| Layer | Where | What's in it |
|---|---|---|
| **Library** (raw, the DNA) | `D:\shovelcat-colony\companion\library` | The raw files, never edited. `ingest` copies new or changed files in from the folders listed in `D:\planet\mika\library_sources.json`, into `_sources\<label>`. |
| **Brain** (digested) | `D:\shovelcat-colony\brain\library\<id>.json` | One digest per raw file: title, summary, outline (headings / defs / exports), word count, content hash. PDF and Word text is extracted once into `brain\library\text\`. A digest is rewritten in place when its file changes, so nothing piles up. `crystallize` can add a local-model summary to the hottest files. |
| **Spiral drive** (organized) | `D:\shovelcat-network\<zone>\library\armNN\<id>.json` | Every file gets an address. **Angle = what it's about**: the void search's domain tree lays the domains around the circle, and seam files sit on the boundaries. **Radius = how hot it is**: search hits, how connected it is, and how recent it is, with the hottest at the centre. Zones follow spiral-drive.ts's Fibonacci areas (L0 1/54 … L7 21/54) and its arm counts per zone (1, 1, 2, 3, 5, 8, 13, 21). Supporting files: the hot map in `L0-origin\library-index.json`, the search vectors in `L4-spacetime\library\signatures.npz`, and hits in `L1-time\library-heat.json`. |
| **Void search** | `living_library.py search "..."` · Mika's `mika_library` / `mika_context` tools | Same method as `planet/voidsearch.py`: tf-idf atoms → kNN contact graph → recursive Fiedler cuts. Each result carries its domain, seam distance, zone and arm, and its nearest neighbours one hop down the void line. When the results span several domains, the seam files between them come back as **bridges**. Every hit warms the file, so what gets used moves inward. |

One honest difference from spiral-drive.ts: there, the angle is the golden angle, which packs data. Here the angle is the void search's domain order, which carries meaning. The zones, the Fibonacci areas and the arm counts are the original design.

## First build (Oct 13)

- **652** raw files were digested into the brain in 38 s. Before this, only **7** of the 647 library files had ever been digested (`memory-geo\library`).
- **224 were exact duplicates** (about a third of the library, mostly `vesica_*` copies of `Vesica AI\*`). They're folded as "twins," so **415** files sit on the spiral. 13 were empty or unreadable.
- **13 domains**, one graph piece, and 25 seam files. In angle order:
  - planet stories (warframe / overwatch / battle.net / civ)
  - double bounce universe / polygon
  - Shovelcat Theory dual domain
  - RNA / safety systems
  - learning / meta / consciousness
  - AI checker pages
  - companion / catgirl / network / tensor (the colony code)
  - dark energy / helix / paths (Iron at alpha)
  - theoretical / mineral notes
- **Zones:** L0 8 · L1 7 · L2 16 · L3 23 · L4 38 · L5 62 · L6 100 · L7 161. With no searches yet, heat is just connectivity plus recency, so the zones will shift as things get used.
- **Searches checked:**
  - "golden spiral drive storage zones" → drive-map.ts, agent-handshake.ts (boundary spiral drive), spiral-drive.ts, bridge.ts, hex-model.ts.
  - "fine structure constant alpha derivation" → the alpha-derivation files.
  - "catgirl emotional trinity colors" → color_trinity_theory.py and the emotional-architecture files, plus three seam bridges.
- **Mika's bridge:**
  - `GET /library` (the `mika_library` tool) now answers from the spiral first (`via: spiral-void-search`), falling back to the old substring scan.
  - `GET /context` (`mika_context`) now opens with a `[LIVING LIBRARY - spiral drive, void search]` section. Both were verified live.
  - Backups are next to the source and the compiled file (`*.bak_20261013`). Only `dist\desktop\main\companion-bridge.js` was replaced; the rest of `dist` was left alone.

## Oct 13, afternoon — the sources Jonathan switched on

Jonathan added the suggested folders, his Downloads, and everything on D: except the games. `library_sources.json` now lists:
- Shovelcat-AI, Shovelcat-Club, structural-reasoning
- all of Desktop\Vesica AI, except replays, lives, forge and _to_delete
- Documents and Downloads
- D:\boys-colony
- D:\planet, docs and code only. Left out: llmpkgs, llama.cpp, arc_compare, eye, lora and mika, which are third-party packages, generated logs and models.
- D:\shovelcat-colony, except companion (Mika's own state and the library itself), the elastic-newton worktree copy, brain, logs, spores, trust, zones, feedback and benchmarks.

Left out on purpose:
- D:\SteamLibrary and D:\OpenRCT2 (games)
- D:\kohya_ss (an installed third-party LoRA tool)
- D:\Shovelcat (the installed app's binaries)
- D:\temp-build (build cache)
- D:\shovelcat-network, because it is the spiral drive itself and ingesting it would loop.

Data files (.json, .geo, .csv) are skipped everywhere. Text files are capped at 2 MB and PDF/Word files at 25 MB.

**First ingest:** 2,973 files copied into `library\_sources`. By source: shovelcat-colony 848, Vesica AI 659, Shovelcat-AI 654, Downloads 475, structural-reasoning 175, planet 78, Shovelcat-Club 68, boys-colony 9, Documents 7. The brain now holds **3,625 digests**. **835 are copies** (folded), so **2,741 files sit on the spiral** in **45 domains**. Sync time is about 2.5 min from scratch and seconds when nothing changed.

**Changes made for the bigger library:**
- the kNN graph is built in blocks, with a sparse eigensolver above 2,500 files
- domains split until they hold 60 or fewer files, at depth 7 or less
- seams are the 3% of files nearest each of the first three cuts
- code titles skip import lines, and React files get their component name
- near-copies with the same title fold together in results
- identifiers are split into parts, so `mini_brain_spawner` matches "mini brain spawner"

The story docs (Story-universe.docx, Story - world.docx and the AI-assisted notes, all in Downloads) now come back for "Theia void Mika story".

## What's missing

- ~~The library doesn't hold the website repos~~: fixed when the sources were switched on (above).
- Files deleted from a source stay in the library copy. Ingest only adds and updates.
- ~~There's no automatic schedule yet~~: since Oct 14 the Windows task **"Mika library hourly"** runs `ingest --lazy` every hour. It takes 1 s when nothing changed, and the spiral is rebuilt only when something did (or once a day). See `claude/MIKA_JOBS.md`.
- **Twins are folded, not deleted.** Deleting duplicates in the library is Jonathan's call.
- **Her old memory store still piles up** (`/library` POST makes a new geo per write). That's separate from this pipeline.
