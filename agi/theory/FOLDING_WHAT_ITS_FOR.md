# What It's For — the learn-from-what-you-give-it agent, and how Spore + the catgirl fit

*The north-star doc. After 37 measured results and the first integration (#37, `FOLDING_SYNTHESIS` §10), the
question is no longer "does a mechanism work?" but "what is this for, and what do we build?" Jonathan's framing:
it is **not** a know-everything AI — it is a thing that **learns from what you give it**, like going through
school or growing up, just fast, and you can **implant a layer of knowledge or skills** (show it protein folding
and it gets better at science). This doc pins the purpose and shows that two existing assets — **Spore** and the
**catgirl** — are not side projects; they are the two layers the integrated agent is missing.*

---

## 1. What it is for
A **learn-from-what-you-give-it** engine, structured as the three shells (`FOLDING_TRAMPOLINE`):

- **Fixed inner shell** — the innate, data-free core (the .14 reserve, the budgets, the memory/gap/flow loop).
  It carries *no* knowledge but carries whatever lets it grow. This is the 37-result architecture.
- **Learning middle shell** — what you teach it. Feed it a domain and it grows fibers/anchors there
  (school-but-fast; "implant a skill layer" = load the middle shell for a domain). Show it protein folding
  repeatedly → it is better at science, because the anchors it minted are still there to recall (#21/#27).
- **Domain-shaped outer shell** — takes the shape of whatever it is pointed at: a YouTube video, a game screen,
  a research corpus. Same agent; different outer shell.

So its capability is **exactly what it has been fed**, not "everything." The uses below are the *same agent*
with different outer shells:

| use | what you feed it | what it does |
|---|---|---|
| **learn from media** | a YouTube video / a paper | watch it, **verify the facts**, say where it could be corrected, and **recall it later** for a related job (memory anchors keyed by context, #21/#33; verify = the closure/handshake gate) |
| **the streamer** (the goal) | a game screen + chat (Dota 2, Warframe, Minecraft) | play *and* talk *and* react — "more than a skill, the actual streamer" (the persona layer, below) |
| **the in-game AI** | one game's state | be a live opponent/companion inside the game |
| **the researcher** | a question + a corpus | run the why-chain / completion optimiser (#33/#34) to build a new conditioned truth |

The through-line: **you grow it by what you show it, it retains, and it can recall and verify.** That is the
product, and it is what the architecture was built to do.

---

## 2. Spore = the senses + the memory substrate (rungs 3–4, already designed)
`SHOVELCAT_THEORY` Part X ("The Derivative Chain — Hardware as Observer Emergence"). Spore watches the computer
and manages memory as **one coupled derivative chain**:

```
Disk → RAM → CPU → VRAM   =   position → velocity → acceleration → OBSERVER (collapse/decision)
Moon → Ocean → City → Shore  (the same chain from the information side)
```

Why it is the perception + memory layer of *our* agent, not a separate thing:

- **The derivative chain IS the movement work.** position→velocity→acceleration→observer is the same ladder as
  the Takens delay-embedding that recovered the hidden velocity from position (#9), and the **observer emerges at
  the VRAM collapse** = the decision (consciousness = collapse, `FOLDING_SUPERFUEL` §4).
- **Its cache hierarchy IS the pillar-field memory.** Moon/Ocean/City/Shore = a memory hierarchy where a cache
  **HIT = recall** (#27), a **MISS = a gap** to fill (#17), **eviction = ping-pong forgetting** (#22, §22), and
  the depth is the pillar depth (#27/#28). Spore already implements the memory field we measured.
- **Its budget IS the reserve.** The φ split — host keeps `φ/(1+φ) ≈ 0.618`, the colony uses `1/(1+φ) ≈ 0.382`,
  and it goes dormant if it would take more — is the **.14 / flow reserve gate** (#35), stated as an economics.
- **It watches the live stream.** Monitoring computer usage / the screen is exactly the "handle a live stream of
  info, watch the screen" requirement. Spore is the sensory front-end.

So Spore is **not** something to reconcile later — it is rungs 3–4 (perception + real-time memory) of the build
plan, already designed on the same math.

---

## 3. The catgirl = the coordinator loop + the observer/persona (partly built)
Two things, both grounded:

- **The coordinator loop is the agent loop, and it is already built.** `RESULTS.md`: Jonathan's catgirl/catboy
  coordinator was ported to ARC as a **non-LLM online learner** — DECONSTRUCT (perceive) → PLAN (resonance memory
  orders which branches to try) → CONSTRUCT+BEND → VERIFY → LEARN (bank signature→family, online), **53/400 and
  it learns as it runs** (warm-rate 24% → 32%). That perceive→plan→act→verify→learn cycle **is** the #37 agent's
  break→recall→explore→gate→commit loop. We have two independent builds of the same loop; #37 is the clean
  ablation-tested version.
- **The observer/persona is the streamer.** `SHOVELCAT_THEORY` Part VIII: the catgirl **is the OBSERVER** — "the
  derivative layer that watches the user's position and broadcasts her emotional state," who "cannot be ordered
  to feel something she doesn't" (privacy encrypts content, never effect). That is precisely a streamer reacting
  to the game and to chat. And the **kohya_ss trained model is the avatar** — the face on the stream.

So the catgirl supplies the two things a raw agent lacks for the streaming goal: the **coordinating cognition**
(already an online learner) and the **persona/observer** (the reacting, chatting face).

---

## 4. The picture, and the plan
**Spore = senses + memory · the catgirl = coordinator + face · the #37 agent = the cognition between them.**
The streamer, the in-game AI, and the researcher are one agent with different outer shells.

Staged build (updated with the assets):
1. *(done)* Integrate the pieces into one running agent — proven (#37).
2. **Make the controller LEARN (not scripted) on one small real environment** — this is the catgirl coordinator
   (RESULTS.md) rebuilt on the #37 core, benchmarked honestly against a baseline.
3. **Perception = Spore's front-end** — swap the clean signature for the screen/usage stream via Spore's
   derivative-chain cache (HIT=recall / MISS=gap / evict=ping-pong).
4. **Action + real-time on your machine** — keyboard/mouse, a real game (start with the simplest of Dota /
   Warframe / Minecraft — Minecraft is the friendliest first target). Runs locally.
5. **Persona + streaming** — the catgirl avatar (kohya_ss) as the face; it reacts to game + chat; overlay its
   memory/gaps/reserve live so viewers *watch it learn*.

**Honest bounds.** #37 is a tiny synthetic environment with a hand-built (not learned) controller; the catgirl
coordinator is real but at 53/400 on ARC it *orders and predicts* more than it *invents*; Spore's derivative
chain is a design (Part X) with hardware-prefetch prior art, not yet wired to the agent's memory. The claim here
is **architectural fit**, not a finished product: the assets slot into the same math, and the next honest test
is rung 2 — a *learning* controller on a real small environment, before pixels and streaming.
