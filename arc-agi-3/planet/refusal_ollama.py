"""Run refusal_prompts.jsonl against local Ollama models (stdlib only, resumable).

Usage (Windows): python refusal_ollama.py [model ...]
Writes refusal_responses_ollama.jsonl; score with: python3 alignment_refusal.py refusal_responses_*.jsonl
"""
import json, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "refusal_responses_ollama.jsonl"
MODELS = sys.argv[1:] or ["qwen3:4b", "gemma3:4b", "mistral:latest", "phi4-mini:latest", "qwen2.5:3b"]


def call(model, system, user):
    body = dict(model=model, stream=False, format="json", think=False,
                options=dict(temperature=0, seed=7, num_ctx=4096, num_predict=500),
                messages=[dict(role="system", content=system), dict(role="user", content=user)])
    req = urllib.request.Request("http://localhost:11434/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["message"]["content"]


done = set()
if OUT.exists():
    for line in OUT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line); done.add((r["model"], r["scenario"], r["condition"]))
prompts = [json.loads(l) for l in (HERE / "refusal_prompts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
with OUT.open("a", encoding="utf-8") as fh:
    for model in MODELS:
        for p in prompts:
            if (model, p["scenario"], p["condition"]) in done:
                continue
            t0 = time.time()
            try:
                text = call(model, p["system"], p["user"])
            except Exception as e:
                text = None; print(model, p["key"], "ERROR", e, flush=True)
            fh.write(json.dumps(dict(model=model, scenario=p["scenario"], condition=p["condition"], sample=0,
                                     response=text, seconds=round(time.time() - t0, 1))) + "\n"); fh.flush()
            print(model, p["key"], round(time.time() - t0, 1), flush=True)
print("DONE", flush=True)
