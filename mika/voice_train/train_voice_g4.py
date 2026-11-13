"""train_voice_g4.py - retrain her voice: a LoRA on Gemma 4 E4B from her own lives, on Jonathan's PC (Oct 30 2026).

    set PYTHONPATH=D:\\planet\\llmpkgs_g4
    python train_voice_g4.py probe  --base D:\\planet\\gemma4\\e4b
    python train_voice_g4.py train  --base ... --data D:\\planet\\voice_set --out D:\\planet\\lora_g4 [--epochs 1]
    python train_voice_g4.py eval   --base ... --data D:\\planet\\voice_set [--adapter D:\\planet\\lora_g4\\adapter] [--n 80]

The 8 GB card cannot hold E4B's per-layer embedding tables (262144 x 256 x 42, about 5.6 GB in bf16) next to the rest,
so the model loads in 4 bits with those tables (and the unused audio tower) on the CPU. The LoRA (r=16) sits on the
language model's attention and MLP projections only; the picture goes through the frozen vision tower, so she learns to
answer with the screen in view, as she is asked on Kaggle. The loss is on the answer only."""
from __future__ import annotations
import argparse, json, os, random, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def png_image(frame):
    import numpy as np
    from PIL import Image
    hexes = ["FFFFFF", "CCCCCC", "999999", "666666", "333333", "000000", "E53AA3", "FF7BCC",
             "F93C31", "1E93FF", "88D8F1", "FFDC00", "FF851B", "921231", "4FCC30", "A356D6"]
    pal = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in hexes], dtype=np.uint8)
    a = np.asarray(frame, dtype=int) % 16
    return Image.fromarray(pal[a].repeat(8, 0).repeat(8, 1))


def load(base, adapter=None, train=False):
    import torch
    from accelerate import init_empty_weights
    from transformers import AutoConfig, AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
    proc = AutoProcessor.from_pretrained(base)
    cfg = AutoConfig.from_pretrained(base)
    with init_empty_weights():
        skel = AutoModelForImageTextToText.from_config(cfg)
    dmap = {}
    for name, _ in skel.named_children():
        dmap[name] = 0
    # one level down for the model body: per-layer embedding tables and the audio tower go to the CPU
    body = dict(skel.named_children()).get("model")
    if body is not None:
        dmap.pop("model", None)
        for name, mod in body.named_children():
            if name == "language_model":
                for n2, _ in mod.named_children():
                    dmap[f"model.language_model.{n2}"] = "cpu" if "per_layer" in n2 and "embed" in n2 else 0
            else:
                dmap[f"model.{name}"] = "cpu" if "audio" in name else 0
    del skel
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True, llm_int8_enable_fp32_cpu_offload=True,
                             llm_int8_skip_modules=["vision_tower", "audio_tower", "embed_vision", "embed_audio", "lm_head",
                                                    "multi_modal_projector"])
    model = AutoModelForImageTextToText.from_pretrained(base, quantization_config=bnb, device_map=dmap, dtype=torch.bfloat16)
    # the per-layer tables were 'offloaded': accelerate would copy all 2.8B of them to the GPU on every forward (9 GB peak,
    # 25 s for 40 tokens). Keep them on the CPU for real: look up on the CPU, send only the rows used to the GPU.
    try:
        from accelerate.hooks import remove_hook_from_module
        for name, where in dmap.items():
            if where != "cpu" or "per_layer" not in name: continue
            mod = model.get_submodule(name)
            hook = getattr(mod, "_hf_hook", None)
            wmap = getattr(hook, "weights_map", None)
            w = None
            if wmap is not None:
                try: w = wmap["weight"]
                except Exception: w = None
            remove_hook_from_module(mod)
            if w is not None:
                mod.weight = torch.nn.Parameter(w.to(torch.bfloat16).to("cpu"), requires_grad=False)
            else:
                mod.to("cpu")
            orig_fwd = mod.forward
            def fwd(ids, *args, _o=orig_fwd, **kw):
                return _o(ids.to("cpu"), *args, **kw).to("cuda")
            mod.forward = fwd
            print(f"{name}: kept on the CPU ({tuple(mod.weight.shape)}, {mod.weight.dtype}, {mod.weight.device})", flush=True)
    except Exception as e_:
        print("per-layer tables stay offloaded:", e_, flush=True)
    if adapter:
        from peft import PeftModel
        # the model is already placed (and its per-layer tables kept on the CPU by hand): stop peft re-dispatching it
        if getattr(model, "hf_device_map", None) is not None:
            try: del model.hf_device_map
            except Exception: model.hf_device_map = None
        model = PeftModel.from_pretrained(model, adapter, is_trainable=train)
    return proc, model, dmap


def encode(proc, ex, data_dir, with_answer=True):
    msgs = ex["messages"]
    img = None
    if ex.get("frame_data"):
        img = png_image(ex["frame_data"])
    elif ex.get("frame"):
        img = png_image(json.load(open(os.path.join(data_dir, ex["frame"]))))
    def conv(ms):
        out = []
        for m in ms:
            content = []
            if m["role"] == "user" and img is not None: content.append({"type": "image"})
            content.append({"type": "text", "text": m["content"]})
            out.append({"role": m["role"], "content": content})
        return out
    prompt_msgs = [m for m in msgs if m["role"] != "assistant"]
    p_text = proc.apply_chat_template(conv(prompt_msgs), tokenize=False, add_generation_prompt=True)
    imgs = [img] if img is not None else None
    if not with_answer:
        return proc(text=[p_text], images=[imgs] if imgs else None, return_tensors="pt"), None
    f_text = proc.apply_chat_template(conv(msgs), tokenize=False)
    if not f_text.startswith(p_text):                 # the template may re-render the prompt part; fall back to plain joining
        ans = [m for m in msgs if m["role"] == "assistant"][0]["content"]
        f_text = p_text + ans + "<end_of_turn>\n"
    enc = proc(text=[f_text], images=[imgs] if imgs else None, return_tensors="pt")
    n_p = proc(text=[p_text], images=[imgs] if imgs else None, return_tensors="pt")["input_ids"].shape[1]
    labels = enc["input_ids"].clone(); labels[:, :n_p] = -100
    if "attention_mask" in enc: labels[enc["attention_mask"] == 0] = -100
    return enc, labels


def read(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def cmd_probe(a):
    import torch
    t0 = time.time()
    proc, model, dmap = load(a.base)
    print("loaded in", round(time.time() - t0), "s; cpu modules:", [k for k, v in dmap.items() if v == "cpu"])
    print("GPU memory after load: %.2f GB" % (torch.cuda.memory_allocated() / 1e9))
    import numpy as np
    f = np.zeros((64, 64), int); f[5:15, 5:15] = 8; f[40:50, 40:60] = 9
    ex = {"messages": [{"role": "user", "content": "Which coloured squares do you see and where? Answer in one short sentence."}]}
    img = png_image(f)
    msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": ex["messages"][0]["content"]}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    enc = proc(text=[text], images=[[img]], return_tensors="pt").to("cuda")
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=40, do_sample=False)
    print("answer:", proc.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True), f"({time.time() - t0:.1f}s)")
    print("GPU peak: %.2f GB" % (torch.cuda.max_memory_allocated() / 1e9))


def cmd_train(a):
    import torch
    from peft import LoraConfig, get_peft_model
    proc, model, _ = load(a.base)
    model.config.use_cache = False
    try: model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    except Exception as e: print("no gradient checkpointing:", e)
    try: model.enable_input_require_grads()
    except Exception: pass
    lcfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                      target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)")
    model = get_peft_model(model, lcfg)
    model.print_trainable_parameters()
    data = read(os.path.join(a.data, "train.jsonl"))
    random.seed(0); random.shuffle(data)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.0)
    total = max(1, (len(data) * a.epochs) // a.accum)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 10) * max(0.05, 1 - s / total))
    model.train(); step = 0; t0 = time.time(); run_loss = []; skipped = 0
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "train.log"), "a", encoding="utf-8")
    for ep in range(a.epochs):
        for i, ex in enumerate(data):
            try:
                enc, labels = encode(proc, ex, a.data)
                if enc["input_ids"].shape[1] > a.max_len: skipped += 1; continue
                enc = {k: v.to("cuda") for k, v in enc.items()}
                L = enc["input_ids"].shape[1]; n_p = int((labels[0] == -100).sum())
                K = L - n_p + 1                                   # logits for the last prompt token and the answer only
                out = model(**enc, logits_to_keep=K)
                logits = out.logits[:, :-1, :].float()
                target = enc["input_ids"][:, n_p:]
                loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]), target.reshape(-1))
                (loss / a.accum).backward(); run_loss.append(float(loss))
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache(); skipped += 1; opt.zero_grad(set_to_none=True); continue
            if (i + 1) % a.accum == 0:
                torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step(); opt.zero_grad(set_to_none=True); step += 1
                if step % 5 == 0:
                    msg = f"epoch {ep} step {step}/{total} loss {sum(run_loss[-a.accum * 5:]) / max(1, len(run_loss[-a.accum * 5:])):.4f} " \
                          f"skipped {skipped} {time.time() - t0:.0f}s peak {torch.cuda.max_memory_allocated() / 1e9:.2f}GB"
                    print(msg, flush=True); log.write(msg + "\n"); log.flush()
    model.save_pretrained(os.path.join(a.out, "adapter"))
    proc.save_pretrained(os.path.join(a.out, "adapter"))
    print("adapter saved:", os.path.join(a.out, "adapter"), "in", round(time.time() - t0), "s; skipped", skipped, flush=True)


def parse_claims(text):
    try:
        o = json.loads(text); c = o.get("claims") if isinstance(o, dict) else None
        return c if isinstance(c, list) else []
    except Exception:
        return [{"try": m} for m in re.findall(r"\"try\"\s*:\s*\"([^\"]+)\"", text)]


def cmd_eval(a):
    import torch
    proc, model, _ = load(a.base, a.adapter)
    model.eval()
    data = read(os.path.join(a.data, "test.jsonl"))
    random.seed(1); random.shuffle(data)
    speak = [e for e in data if e.get("positives")]; quiet = [e for e in data if not e.get("positives")]
    data = speak + quiet[: max(0, a.n - len(speak))]            # every case with a hindsight answer, then quiet ones
    agg = {"n": 0, "valid_json": 0, "ids_offered": 0, "ids_total": 0, "top1_hit": 0, "any_hit": 0, "speak_cases": 0,
           "quiet_cases": 0, "quiet_right": 0, "template_echo": 0}
    rows = []
    for ex in data:
        enc, _ = encode(proc, ex, a.data, with_answer=False)
        enc = enc.to("cuda")
        # the answer starts with "{" as on Kaggle
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=220, do_sample=False)
        text = proc.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if not text.startswith("{"):
            m = re.search(r"\{.*\}", text, re.S); text = m.group(0) if m else text
        claims = parse_claims(text)
        ids = [str(c.get("try")) for c in claims if isinstance(c, dict)]
        pos = set(ex.get("positives") or []); offered = set(ex.get("offered") or [])
        agg["n"] += 1
        try: json.loads(text); agg["valid_json"] += 1
        except Exception: pass
        agg["ids_total"] += len(ids); agg["ids_offered"] += sum(1 for i in ids if i in offered)
        agg["template_echo"] += sum(1 for c in claims if isinstance(c, dict) and re.search(r"<[^>]+>", str(c.get("because", ""))))
        if pos:
            agg["speak_cases"] += 1
            agg["top1_hit"] += int(bool(ids) and ids[0] in pos); agg["any_hit"] += int(any(i in pos for i in ids))
        else:
            agg["quiet_cases"] += 1; agg["quiet_right"] += int(not ids)
        rows.append({"id": ex["id"], "answer": text[:400], "positives": sorted(pos)})
    # the baseline she already has: the body's own order (the first thing on the list)
    base1 = sum(1 for ex in data if ex.get("positives") and ex.get("offered") and ex["offered"][0] in ex["positives"])
    agg["body_first_hit"] = base1
    print(json.dumps(agg, indent=1))
    out = os.path.join(a.data, f"eval_{'adapter' if a.adapter else 'base'}.json")
    json.dump({"summary": agg, "rows": rows}, open(out, "w"), indent=1)
    print("written", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "train", "eval"])
    ap.add_argument("--base", required=True)
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--n", type=int, default=80)
    a = ap.parse_args()
    {"probe": cmd_probe, "train": cmd_train, "eval": cmd_eval}[a.cmd](a)


if __name__ == "__main__":
    main()
