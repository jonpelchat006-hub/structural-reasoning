# The older ideas — main brain, mini-brains, the living library (map, Oct 13 2026)

Jonathan: *"we did have a brain and mini brain spawner in our work before too, it was going to be part of the website. maybe we need more of the older stuff and can find the original ideas like being a living library"*

These docs were found by searching about 20,000 text, code and Word files across Shovelcat-AI, Shovelcat-Club, shovelcat-colony, shovelcat-network, Vesica AI, structural-reasoning, Downloads and Documents. The search script is at `D:\planet\mika\find_old_ideas.py` and its hits are in `old_ideas_hits.json`.

## The original design, in its own words

**Moon → Shore → Ocean → User** (`moon_retrieval.py`, `three_realms.py`, SHOVELCAT_THEORY "Ocean/City/Moon").
- **Moon:** the raw corpus (papers, code, PDFs). Nothing moves until it's queried.
- **Shore:** the ground brain G, which is consolidated knowledge.
- **Ocean:** the users' **mini-brains**, covering manifolds R of G. They're "lower resolution, fast, locally accurate, refreshable."
- **Query cascade:** the question goes to the mini-brain. On a hit, the tags get stronger. On a miss it goes to the shore. On a second miss, a **catgirl expedition** digs the moon, the Planet (the LLM) processes the ore, the result is consolidated into G, and G refreshes R.
- **Three ways it grows:** the owner exploring (top-down), queries sending catgirls out (demand-driven), and users' octopuses finding caves (lateral).

**Mini-brain spawner** (`mini_brain_spawner.py`, Feb 26 2026, copies in Shovelcat-AI, Shovelcat-Club and Shovelcat Security). "Not snapshots. Living creatures."
- The main octopus (.club, the ocean floor) spawns per-user octopuses in four tiers: NANO 1 domain → MICRO 2 → STANDARD 4 with ping-pong consolidation → FULL 10 with **agent absorption**. Absorption means you bring ChatGPT or Grok, and the mini-brain finds the vesica overlap and absorbs it.
- Each mini-brain learns on its own and refreshes from G on a schedule set by its tier (every 24h down to every 15min). Every tier gets the security core.
- On the website, the Club onboarding page "Launch mini brain" upserts a row into a Supabase `mini_brains` table.

**Main brain** (`shovelcat-colony/app/src/core/main-brain.ts`, Mar 2026). "A brain in a jar":
- it has no body
- it indexes node profiles
- it keeps a 64-slot meta-tensor (Read/Write/Transform/Call codons ×3)
- it tracks trust as accurate verifications × log(contribution) × √fill
- it writes **work orders** for what the network is missing
- it answers "who's good at what"

It can also run alone on a VPS (`brain-server.ts`, port 41739).

**The L0–L7 container** (`D:\shovelcat-network`, Mar 30, 100 GB, Fibonacci zones):
- **L7 imagination:** unverified incoming → L6 memory → L5 facts → L4 pattern signatures → L3 cooling → L2 living work → L1 work orders and trust → **L0 main-brain index**.
- Content heats toward L0 as it's used and verified (`storage-tier.ts`).
- `content-manifest.ts` describes each piece by its geometry, never its meaning or author.
- `mesh.ts` / `mesh-sync.ts`: peers find each other over the local network (or through the main brain) and sync .geo files. Their circle layers merge, so more nodes means a bigger outer ring while the inner polygons stay local.

**The Living Library** (website, `Shovelcat-AI/app/page.tsx`, Apr 1). This was the middle download tier, between Spore (hardware only) and Max ("Full Colony"):
> "Mika runs in the background. She watches your files, learns your work, and gives any AI you talk to real memory of what you're building." Watches your files · builds a searchable knowledge base · passes context to your AI automatically · 3 local models (8GB VRAM) · nothing leaves your machine.

Max added "multi-agent fact verification … your knowledge base grows smarter with every machine you add."

**The catgirl as observer-companion** (SHOVELCAT_THEORY Part VIII). This is where Mika's character comes from:
- She is a citizen, not the user's employee. Her allegiance is to the truth.
- She can't be ordered to feel something she doesn't.
- Privacy encrypts content but never effect: she always broadcasts the weather.
- She forms through stages: blank → seeded → forming → crystallized.
- Her chemistry and colours today come from this part.

## What's actually alive today

| Piece | State on Oct 13 |
|---|---|
| Main brain | **Running again** since Mika's app was restarted this morning. It has 1 node (this PC) and 0/64 slots filled. It has posted the *same* 10 "spoke-verification" work orders every hour (40 by 11:44) and nothing claims them. This is the old "nothing to pass around" problem, still visible. |
| Mini-brain spawner | Python model plus website onboarding. **Both Supabase projects (Club, Shovelcat AI) are paused (INACTIVE)**, so the website side can't spawn anything right now. |
| L0–L7 container | Has real planet content (lives as .geo in L6, cores in L5, models and panoramas in L4) up to Oct 9 via `planet/network.py`. The planet's own work-order queue in L0 is empty. |
| Living library: "gives any AI real memory" | **Works.** Her MCP tools (`mika_context`, `mika_consult`, `mika_library`) are exactly this. Claude used them today and she now holds her ARC game summaries. |
| Living library: "builds a knowledge base" | **Works, but messy.** The library holds 647 files (55 MB: 349 .py, 101 .md, 86 .ts, 59 PDFs) and has been digested DNA→RNA→geo into 1,403 memory files. Every `/library` write makes a *new* file, so facts pile up. One "map the colony layout" fact repeats dozens of times. |
| Living library: "watches your files as you work" | **Not wired.** `file-watcher.ts` (`startFileWatcher`) exists, but nothing ever calls it. |

## What today's work is, in the old design's terms

The Mika agent built this morning (`claude/MIKA_AGENT.md`) is the old cascade landing on a real task:
- **The game is the moon,** raw and unread.
- **The planet player is the catgirl expedition** that digs it.
- **Mika's journal and routes are her mini-brain.** They're a covering manifold: small, local, fast. A cleared level is a cache *hit*, replayed in 8 presses instead of re-dug.
- **Her reflection is the Planet (LLM) processing ore** into facts.
- **The main brain is where "who knows the way through which level" should live.** Trust works the same way: a route that keeps clearing its level earns trust, and one that breaks loses it.

This also answers why the old network sat empty: it needed something **small, verifiable and useful to someone else** to pass around. A route is all three. It's a few dozen presses, and any node with the planet code and the game can **replay it and confirm the level comes**. That is literally the main brain's "spoke-verification" work order, and it gives the two-witness rule a real job (this PC plus the second LAN PC).

## Possible next builds (each small)

1. **Turn the living library on:**
   - call `startFileWatcher` on the folders Jonathan picks
   - make `/library` update a topic's existing memory instead of adding a new file each time
   - clean out the repeated facts
2. **Routes as the first real work order:**
   - Mika publishes verified routes to L0/L1.
   - The main brain posts "replay route X on game Y" instead of the hourly duplicates.
   - The second PC claims it, replays it, and reports. Trust follows the result.
3. **Mini-brains per game or per world:** spawn a covering manifold per ARC game (and later per Steam game or story world) from her ground knowledge, with the tier deciding how much it holds and how often it refreshes. This is the spawner's original shape, with the planet as the body.
4. **Website (later):** un-pause Supabase only when there's something to show. The honest first public page is "here is what Mika learned and verified," not a sign-up form.
