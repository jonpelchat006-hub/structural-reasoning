"""lm_server.py - Mika's voice served the way her code already asks for it: Ollama's /api/chat and /api/tags on
127.0.0.1:11434. On her PC Ollama answers; on Kaggle (no internet, no Ollama) this answers instead, so her imagination
(mika_think's shell) and her reflection between lives (mika_mind.reflect) run unchanged.

    python lm_server.py --base <model dir> [--adapter <LoRA dir> | --adapter none] [--name planet-voice] [--port 11434]

Text models (planet-voice: Jonathan's LoRA on Qwen2.5-3B-Instruct) load with AutoModelForCausalLM. Models that read
pictures (Gemma 4: the folder has a processor_config.json) load with AutoProcessor + AutoModelForImageTextToText, and an
Ollama-style "images" list (base64 PNG) on a message is shown to the model. One model on the GPU, one answer at a time
(a lock); format "json" is helped by starting the answer with "{"."""
from __future__ import annotations
import argparse, base64, io, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NAME = "planet-voice"
LOCK = threading.Lock()
STATE = {"model": None, "tok": None, "proc": None, "calls": 0, "seconds": 0.0, "images": 0}


def load(base, adapter):
    import torch
    vision = os.path.exists(os.path.join(base, "processor_config.json")) or os.path.exists(os.path.join(base, "preprocessor_config.json"))
    dev = "cuda" if torch.cuda.is_available() else None
    if vision:
        from transformers import AutoProcessor, AutoModelForImageTextToText
        STATE["proc"] = AutoProcessor.from_pretrained(base)
        STATE["tok"] = getattr(STATE["proc"], "tokenizer", STATE["proc"])
        model = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.bfloat16, device_map=dev)
        print(f"lm_server: vision model {type(model).__name__} from {base}", flush=True)
    else:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        STATE["tok"] = AutoTokenizer.from_pretrained(adapter if adapter and os.path.exists(os.path.join(adapter, "tokenizer_config.json")) else base)
        model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16, device_map=dev)
        print(f"lm_server: text model {type(model).__name__} from {base}", flush=True)
    if adapter and adapter.lower() != "none":
        try:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, adapter)
            model = model.merge_and_unload()
            print(f"lm_server: adapter merged from {adapter}", flush=True)
        except Exception as e:
            print("lm_server: adapter NOT applied (" + str(e)[:300] + "); serving the base model", flush=True)
    model.eval()
    STATE["model"] = model


def _image(b64):
    from PIL import Image
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def chat(messages, fmt=None, options=None):
    import torch
    tok, model, proc = STATE["tok"], STATE["model"], STATE["proc"]
    options = options or {}
    prefix = "{" if fmt == "json" else ""
    n_new = int(options.get("num_predict") or 400)
    temp = float(options.get("temperature") if options.get("temperature") is not None else 0.4)
    imgs = []
    if proc is not None:
        msgs = []
        for m in messages:
            content = []
            for b in (m.get("images") or []):
                try: imgs.append(_image(b)); content.append({"type": "image"})
                except Exception: pass
            content.append({"type": "text", "text": m.get("content") or ""})
            msgs.append({"role": m.get("role", "user"), "content": content})
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True) + prefix
        if imgs:
            try: ids = proc(text=[text], images=[imgs], return_tensors="pt")
            except Exception: ids = proc(text=[text], images=imgs, return_tensors="pt")
        else:
            ids = proc(text=[text], return_tensors="pt")
    else:
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True) + prefix
        ids = tok(text, return_tensors="pt")
    ids = ids.to(model.device)
    t0 = time.time()
    with LOCK, torch.no_grad():
        out = model.generate(**ids, max_new_tokens=n_new, do_sample=temp > 0, temperature=max(temp, 1e-3), top_p=0.9,
                             pad_token_id=getattr(tok, "pad_token_id", None) or getattr(tok, "eos_token_id", None))
    gen = out[0][ids["input_ids"].shape[1]:]
    text_out = prefix + tok.decode(gen, skip_special_tokens=True)
    if fmt == "json" and "}" in text_out:
        text_out = text_out[: text_out.rfind("}") + 1]
    dt = time.time() - t0
    STATE["calls"] += 1; STATE["seconds"] += dt; STATE["images"] += len(imgs)
    print(f"lm_server: call {STATE['calls']}: {int(ids['input_ids'].shape[1])} in, {len(gen)} out, {len(imgs)} image(s), {dt:.1f}s", flush=True)
    return {"model": NAME, "message": {"role": "assistant", "content": text_out}, "done": True,
            "prompt_eval_count": int(ids["input_ids"].shape[1]), "eval_count": int(len(gen))}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/tags"):
            return self._send({"models": [{"name": NAME, "model": NAME}]})
        if self.path.startswith("/api/stats"):
            return self._send({k: v for k, v in STATE.items() if k in ("calls", "seconds", "images")})
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        if self.path.startswith("/api/chat"):
            try:
                return self._send(chat(body.get("messages") or [], body.get("format"), body.get("options")))
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
        if self.path.startswith("/api/generate"):
            try:
                r = chat([{"role": "user", "content": body.get("prompt", ""), "images": body.get("images") or []}], body.get("format"), body.get("options"))
                return self._send({"model": NAME, "response": r["message"]["content"], "done": True})
            except Exception as e:
                return self._send({"error": str(e)[:300]}, 500)
        self._send({"error": "not found"}, 404)


def main():
    global NAME
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", default="none")
    ap.add_argument("--name", default="planet-voice")
    ap.add_argument("--port", type=int, default=11434)
    a = ap.parse_args()
    NAME = a.name
    load(a.base, a.adapter)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"lm_server: {NAME} on 127.0.0.1:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
