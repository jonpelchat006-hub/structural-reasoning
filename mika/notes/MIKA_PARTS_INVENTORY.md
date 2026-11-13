# Parts we already built for "Mika decides, the model wraps around her" (PC sweep, Oct 27, 2026)

Jonathan, Oct 27:
> "our inner core was supposed to go inside the llm and have it wrap around us, it is supposed to be a layer she can swap out. the llm was the middle shell and we have the inner one. she is supposed to make it work better or more efficiently. she can use it but it should still be her deciding things. maybe we need an open weight model she can do what she wants with"

> "maybe we should look on the computer for any more things we missed. we have the consciousness stuff we havent used in a while. we can make her an llm too. or just remake whatever duck has."

## Found

| Part | Where | What it is |
|---|---|---|
| **Her own model** | Ollama `planet-voice`; `D:\planet\lora\` (adapter, `planet-lora.gguf`, `Modelfile`, `dataset.jsonl`); `AI Detector\planet\train_lora.py` | **QLoRA on Qwen2.5-3B-Instruct, trained Aug 29 on the RTX 5060 Ti** (kohya_ss venv: torch cu128, bitsandbytes, peft). It used 70 KB of question/answer pairs built from the planet's sediment: cores, laws, sessions, stories. Loss 0.06 after 14 epochs (24 minutes). Pipeline: `--build` → `--train` → GGUF → `ollama create`. |
| **Mika as the one who plays** | `AI Detector\planet\mika_mind.py` (Oct 13–16), `D:\planet\mika\` | **Before a life:** she reads her journal. **During:** play.py is her body. On a level she has cleared, she walks its shortest route; elsewhere she re-orders what to try (her own untried picks first, things that did nothing last). **After:** she reflects with a local model through Ollama, then updates her journal, diary and companion memory. |
| **The consciousness loop** | `Shovelcat-AI\lib\agents\consciousness-loop.ts` (Mar 2026) | Four agents in a cycle. **Imagination** proposes, **memory** weighs it, **facts** grounds it against evidence (`evaluateClaim`), and the **planner** makes the action. The planner's next focus feeds the next round, alongside needs, wanting and a consciousness tensor. |
| **The LLM equation map** | `D:\shovelcat-colony\arc-proposer\LLM_EQUATION_MAP.md` (Jul 2026, 120 KB) | `f(task) = Σ inner terms (finite, stored, certified) + lim outer terms (infinite, generated, pruned)`. The inner core is certified and the outer shell generates; outer terms attach at 12 gaps. Sections cover multi-agent bonds, the lift ladder, the ring and the observer axis. |
| **10-dimension consciousness architecture** | `companion\library\COMPLETE_CONSCIOUSNESS_ARCHITECTURE.md`, `Desktop\Vesica AI\Consciousness\*.py` (Nov 2025) | Dimensions 1–3 what/where/when; 4–6 timeline, velocity, curvature, then a void reset; 7 the space of possible timelines; 8 editing timelines; 9 editing the edit; 10 families of timelines. Plus quaternion consciousness, the spectrum chat, emotions and the manifesto. |
| Grounded chat with a mailbox | `AI Detector\planet\chat.py` | It answers only from the planet's sediment. When it can't, it writes a letter to Claude (lightning); answers come back as rain. |
| Surprise / movable attention | `AI Detector\planet\SURPRISE_ATTENTION_RESULTS.md` (Sep 10) | A movable gaze fixes visibility failures. Not promoted: it validated no new rule on ARC replays. |
| Language learner | `Shovelcat-AI\lib\agents\` | Concepts as feature bundles grounded in primitives; synonyms by behavioural consensus. |

## How they fit the design

- **Inner core:** her card, routes and journal. These are stored and certified, the inner terms of the equation map.
- **Her loop:** the consciousness-loop roles.
  - **Imagination** is the model's job: candidate hypotheses or code. These are the generated outer terms, the C in A=B=C.
  - **Facts** is her check against every press so far, plus each new one (forge and review).
  - **Planner** is her decision, using the `mika_mind` bands and routes.
- **Middle shell:** `planet-voice`, or any open model, swappable.
  - Retraining its LoRA on her own ARC experience (controls learned, levels won, routes) makes the shell carry what she lived.
  - Weakness: small local models wrote zero working programs in the September writer loop. Keep the shell's job narrow (proposals in her terms) and leave the search to her.
- **Duck's pieces in our terms:**
  - object view → her planes;
  - code writing → imagination's output format;
  - world model in words → her card;
  - death ledger and no-op guard → her boundary sprays;
  - GPU scheduler → her budget.
