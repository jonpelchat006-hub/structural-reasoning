#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_lora.py — the mouth LEARNS WEIGHTS: QLoRA on the planet's own sediment.

Until now the lower ocean was a frozen model narrating; the planet's memory lived only in files.
This closes the last gap from the learning audit: the sediment (cores, laws, stats sessions,
witness threads, clip descriptions, stories) becomes a supervised dataset, and a LoRA trains on
Qwen2.5-3B-Instruct in 4-bit on the RTX 5060 Ti using kohya_ss's venv (torch+cu128, bitsandbytes,
peft). The result is the planet's OWN voice: a model whose weights carry what the planet lived.

Two halves, two interpreters:
  --build   any python: walks D:\\planet\\ocean, writes lora\\dataset.jsonl (question/answer pairs,
            all grounded in deposited fact — nothing invented; every pair cites its world)
  --train   kohya's venv (D:\\kohya_ss\\.venv\\Scripts\\python.exe): QLoRA, bounded by --steps,
            saves the adapter to lora\\adapter\\ and prints a sample generation as proof

Later steps (documented, not yet automated): peft merge_and_unload -> llama.cpp convert_hf_to_gguf
-> ollama create planet-qwen. The spore can then chain --build/--train into the deep sleep.
"""
from __future__ import annotations
import argparse, glob, json, os, random, sys, time

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

BASE = "Qwen/Qwen2.5-3B-Instruct"
SYSTEM = ("You are the voice of a small learning system (a 'planet') that watches and plays games "
          "on its keeper's computer. You speak only from what the planet has actually learned, "
          "watched, or read. You are honest about not knowing.")


# ============================================================================ dataset
def _law_pairs(world, core):
    out = []
    mv = {k: v for k, v in core.get("laws", {}).get("mover", {}).items() if v.get("evidence", 0) >= 2}
    if mv:
        a = "; ".join(f"{k} moves things by (dy,dx)={tuple(v['value']) if isinstance(v['value'], list) else v['value']}"
                      f" (seen {v['evidence']}x)" for k, v in list(mv.items())[:8])
        out.append((f"What do the controls do in {world}?", f"From playing {world}: {a}."))
    cn = {k: v for k, v in core.get("laws", {}).get("counter", {}).items() if v.get("evidence", 0) >= 3}
    if cn:
        regs = sorted({k.split(":")[0] for k in cn})[:8]
        out.append((f"What counters or meters exist in {world}?",
                    f"{world} shows these registers on screen: {', '.join(regs)}."))
    return out


def _concept_pairs(world, core):
    out = []
    cs = list(core.get("concepts", {}).items())
    if cs:
        names = [k.replace("+", " with ") for k, _ in cs[:10]]
        out.append((f"What has the planet learned about {world}?",
                    f"In {world} it has earned {len(cs)} recurring patterns, including: "
                    f"{'; '.join(names[:6])}. Each one recurred across separate lives before it was kept."))
    for k, c in cs[:12]:
        atoms = k.split("+")
        out.append((f"In {world}, what goes together with {atoms[0]}?",
                    f"When {atoms[0]} happens in {world}, it recurs together with "
                    f"{' and '.join(atoms[1:])} — a pattern earned across lives" +
                    (" (admitted by recurrence)" if c.get("byRecurrence") else "") + "."))
    return out


def _history_pairs(world, core):
    out = []
    h = [x for x in core.get("history", []) if x.get("n_actions", 0) > 50][-6:]
    for x in h:
        out.append((f"How did life {x.get('life')} in {world} go?",
                    f"Life {x.get('life')} in {world}: {x.get('n_actions')} actions, ended by "
                    f"{x.get('cause')}, {round(100 * (x.get('explained') or 0))}% of surprise explained" +
                    (f", learned {', '.join(x['graduated'])}" if x.get("graduated") else "") + "."))
    return out


def _stats_pairs(world, wroot):
    out = []
    try:
        with open(os.path.join(wroot, "stats", "sessions.json"), encoding="utf-8") as f:
            ses = json.load(f)
    except Exception:
        return out
    for s in (ses if isinstance(ses, list) else ses.get("sessions", []))[-5:]:
        bits = [f"{k}: {v}" for k, v in s.items() if k not in ("t", "shots", "world") and v not in (None, "", [])][:6]
        if bits:
            out.append((f"What did the stats organ read off a recent {world} session?",
                        f"A watched {world} session: {'; '.join(str(b) for b in bits)}."))
    return out


def _witness_pairs(world, wroot):
    out = []
    try:
        lines = open(glob.glob(os.path.join(wroot, "witness_*.txt"))[0], encoding="utf-8").read().splitlines()
    except Exception:
        return out
    lines = [l.split("] ", 1)[-1].split("  || predicted:")[0] for l in lines if "] " in l][-30:]
    lines = [l for l in lines if len(l) > 25][:24]
    for i in range(0, len(lines) - 3, 4):
        out.append((f"What happened while watching {world}?",
                    "Watching " + world + ": " + " Then ".join(lines[i:i + 3]) + "."))
    return out


def _clip_pairs(world, wroot):
    out = []
    try:
        rows = [json.loads(l) for l in open(os.path.join(wroot, "clips", "ledger.jsonl"), encoding="utf-8") if l.strip()]
    except Exception:
        return out
    for r in rows[-8:]:
        if r.get("description") and len(r["description"]) > 30:
            out.append((f"Describe a moment the planet recorded from {world}.",
                        f"A {r.get('seconds', '?')}-second clip from {world}: {r['description']}"))
    return out


def _story_pairs(world, wroot):
    out = []
    for p in sorted(glob.glob(os.path.join(wroot, "stories", "story_*.json")))[-3:]:
        try:
            s = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if s.get("tale"):
            out.append((f"Tell a story from the world of {world}.",
                        s["tale"] + "\n(Every rule in that story is one the planet truly earned in "
                        + world + "; the rest is fiction.)"))
    return out


def build(ocean: str, out_path: str) -> int:
    pairs = []
    for p in sorted(glob.glob(os.path.join(ocean, "*", "core_*.json"))):
        wroot = os.path.dirname(p)
        world = os.path.basename(wroot)
        if world in ("porthole", "planet_porthole", "program_manager", "windows_default_lock_scr", "battle_net"):
            continue                                    # junk worlds teach junk
        try:
            core = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for fn in (_law_pairs, _concept_pairs, _history_pairs):
            pairs += [(q, a, world) for q, a in fn(world, core)]
        for fn in (_stats_pairs, _witness_pairs, _clip_pairs, _story_pairs):
            pairs += [(q, a, world) for q, a in fn(world, wroot)]
    # honesty pairs: the planet must keep saying "I don't have that"
    unknowns = ["What is the capital of France?", "Who won the world cup?", "Write me a poem about the sea.",
                "What is my bank balance?", "What game will I play tomorrow?"]
    for q in unknowns:
        pairs.append((q, "I don't have that — I only know what the planet has watched, played, or read "
                         "on this computer.", "none"))
    random.Random(0).shuffle(pairs)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for q, a, w in pairs:
            f.write(json.dumps({"messages": [{"role": "system", "content": SYSTEM},
                                             {"role": "user", "content": q},
                                             {"role": "assistant", "content": a}],
                                "world": w}, ensure_ascii=False) + "\n")
    print(f"dataset: {len(pairs)} pairs -> {out_path}")
    return len(pairs)


# ============================================================================ training (kohya venv)
def train(data_path: str, out_dir: str, steps: int, hf_home: str):
    os.environ.setdefault("HF_HOME", hf_home)
    os.environ["USE_TF"] = "0"; os.environ["USE_FLAX"] = "0"   # kohya's venv carries TF+Keras3; stay pure torch
    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                              Trainer, TrainingArguments)
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    try:    # free the lower ocean's VRAM for the training window (it reloads on its next call)
        import subprocess as _sp
        _sp.run(["ollama", "stop", "gemma3:4b"], capture_output=True, timeout=60)
    except Exception: pass
    tok = AutoTokenizer.from_pretrained(BASE)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    # device_map={"":0}: everything on the GPU — "auto" tried to spill past Ollama's resident
    # model and dispatch_model called .to() on a 4-bit model, which is forbidden
    model = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb, device_map={"": 0})
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    rows = [json.loads(l) for l in open(data_path, encoding="utf-8") if l.strip()]
    def encode(r):
        ids = tok.apply_chat_template(r["messages"], tokenize=True, add_generation_prompt=False)
        ids = ids[:1024]
        return {"input_ids": ids, "labels": list(ids), "attention_mask": [1] * len(ids)}
    data = [encode(r) for r in rows]

    class C:                                             # pad-to-longest collator
        def __call__(self, feats):
            import torch as t
            m = max(len(f["input_ids"]) for f in feats)
            pad = tok.pad_token_id or tok.eos_token_id
            batch = {"input_ids": [], "labels": [], "attention_mask": []}
            for f in feats:
                d = m - len(f["input_ids"])
                batch["input_ids"].append(f["input_ids"] + [pad] * d)
                batch["labels"].append(f["labels"] + [-100] * d)
                batch["attention_mask"].append(f["attention_mask"] + [0] * d)
            return {k: t.tensor(v) for k, v in batch.items()}

    args = TrainingArguments(output_dir=out_dir, per_device_train_batch_size=1,
                             gradient_accumulation_steps=8, learning_rate=1e-4, max_steps=steps,
                             warmup_steps=min(20, steps // 10), logging_steps=10, save_strategy="no",
                             bf16=True, report_to=[], gradient_checkpointing=True,
                             dataloader_pin_memory=False)
    Trainer(model=model, args=args, train_dataset=data, data_collator=C()).train()
    ad = os.path.join(out_dir, "adapter")
    model.save_pretrained(ad); tok.save_pretrained(ad)
    print("adapter saved:", ad)
    # proof: one grounded generation from the trained voice
    q = "What has the planet learned about dead_cells?"
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]
    ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(model.device)
    out = model.generate(ids, max_new_tokens=120, do_sample=False)
    print("Q:", q)
    print("A:", tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocean", default=r"D:\planet\ocean")
    ap.add_argument("--out", default=r"D:\planet\lora")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--steps", type=int, default=200)
    a = ap.parse_args()
    data = os.path.join(a.out, "dataset.jsonl")
    if a.build: build(a.ocean, data)
    if a.train: train(data, a.out, a.steps, os.path.join(a.out, "hf"))


if __name__ == "__main__":
    main()
