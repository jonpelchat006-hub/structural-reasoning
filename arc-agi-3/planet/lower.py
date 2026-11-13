#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lower.py — the LOWER OCEAN's models (Ollama, on Jonathan's PC): the counterpart of the
clouds, filtering from BELOW. The clouds (Claude) filter what comes in from outside —
papers, searches, the raw screen. The lower models filter what rises from the inside
toward the core, in two jobs the language learner already specified:

  reproducers — independent BUILDERS for the reproduction test (concept-registry.ts:
                "wire an Ollama ensemble"): each model reconstructs a candidate concept
                from its encoding; agreement across models = triangulation; their
                disagreement = fiber width. A concept nobody can rebuild does not graduate.
  narrator    — the estuary: turns a life's atoms into a few sentences. It may only use the
                atoms it is given (grounded by construction); anything else is a leak.

Slow and cheap, between lives — never in the frame loop. Any failure (Ollama down,
model missing, timeout) degrades to "no builders", never to a crash.
"""
from __future__ import annotations
import json, re, urllib.request
from typing import Dict, List, Optional, Set

OLLAMA = "http://localhost:11434"


def _ask(model: str, prompt: str, timeout: float = 60.0, json_mode: bool = False,
         num_predict: int = 300, think: bool = False) -> Optional[str]:
    """think=False switches off qwen3-style hidden reasoning (it otherwise eats the whole budget)."""
    body = {"model": model, "prompt": prompt, "stream": False, "think": think,
            "options": {"temperature": 0.2, "num_predict": num_predict}}
    if json_mode: body["format"] = "json"
    try:
        req = urllib.request.Request(f"{OLLAMA}/api/generate", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("response", "")
    except Exception:
        return None


def _ask_image(model: str, prompt: str, image_b64, timeout: float = 90.0,
               json_mode: bool = False, num_predict: int = 300) -> Optional[str]:
    """Image(s) + prompt to a multimodal lower-ocean model (gemma3 sees). Failure -> None."""
    images = image_b64 if isinstance(image_b64, list) else [image_b64]
    body = {"model": model, "prompt": prompt, "stream": False, "images": images,
            "options": {"temperature": 0.1, "num_predict": num_predict}}
    if json_mode: body["format"] = "json"
    try:
        req = urllib.request.Request(f"{OLLAMA}/api/generate", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("response", "")
    except Exception:
        return None


def available(models: List[str]) -> List[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            have = {m["name"] for m in json.loads(r.read().decode()).get("models", [])}
        return [m for m in models if m in have or any(h.startswith(m) for h in have)]
    except Exception:
        return []


def reproduce(model: str, encoding: List[str], vocabulary: List[str], timeout: float = 60.0) -> Optional[Dict[str, float]]:
    """A builder sees a SHUFFLED encoding (the atoms that co-occurred, plus distractors from the
    vocabulary) and must say which atoms form one concept. Returns a definition or None."""
    prompt = ("You are reconstructing a concept from an agent that plays games by looking at a screen. "
              "Atoms are events the agent's senses can detect. Below is a bag of atoms; some of them "
              "belong together as ONE recurring situation, the rest are distractors.\n"
              f"Bag: {json.dumps(encoding)}\n"
              f"Full vocabulary of atoms: {json.dumps(vocabulary)}\n"
              'Answer with JSON only: {"concept": [atoms that belong together], "name": "short name"}')
    out = _ask(model, prompt, json_mode=True, timeout=timeout)
    if not out: return None
    try:
        d = json.loads(out)
        atoms = [a for a in d.get("concept", []) if isinstance(a, str)]
        return {a: 1.0 for a in atoms}
    except Exception:
        return None


def narrate(model: str, atoms_by_count: Dict[str, int], summary: Dict) -> Optional[str]:
    """Grounded narration: only the atoms listed may be mentioned."""
    prompt = ("You narrate, in first person and plain words, one life of a small agent playing a game it "
              "does not understand. You may ONLY refer to the events listed (with how often they happened) "
              "and the numbers given. Do not invent objects, names or reasons. Three sentences.\n"
              f"Events: {json.dumps(atoms_by_count)}\nNumbers: {json.dumps(summary)}")
    out = _ask(model, prompt)
    return out.strip() if out else None


def advise(model: str, atoms_by_count: Dict[str, int], concepts: List[str], map_summary: str,
           actions: List[str], context: str = "an unknown place") -> Optional[Dict]:
    """The FIRST-PERSON observer: 'what would someone actually be doing here?' It sees only what the
    eyes reported (atoms, graduated concepts, the map's size) — never the screen, never the game's
    name — and returns a tendency over the available actions plus one sentence. Untrusted: it only
    tilts the hand, and the coach keeps the tilt only if it raised the drive (new ground, fewer deaths)."""
    prompt = (f"You are a person in {context}, seen from a side view, controlling a small figure with these keys: "
              f"{json.dumps(actions)}. What you have noticed so far (event: how often): {json.dumps(atoms_by_count)}. "
              f"Things you have learned to recognise: {json.dumps(concepts)}. Map: {map_summary}. "
              "Normal people walk far more than they jump, look before they leap, and keep going in the direction "
              "where the world keeps opening up. Give a tendency for each key as a number 0..1 and one short sentence "
              'about what you would try next. JSON only: {"tendency": {key: number}, "why": "..."}')
    out = _ask(model, prompt, json_mode=True)
    if not out: return None
    try:
        d = json.loads(out)
        t = {k: float(v) for k, v in d.get("tendency", {}).items() if k in actions}
        return {"tendency": t, "why": str(d.get("why", ""))[:200]} if t else None
    except Exception:
        return None
