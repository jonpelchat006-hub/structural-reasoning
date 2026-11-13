#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
witness.py — the MEMORY LINE for the seeing: each new observation rides the line of the ones
before it, and an ANTENNA (an open end) sticks out past the newest memory as a prediction.

Jonathan: "each frame we show doesn't remember the last one... each new memory needs to ride
the line of memories that came before it but with variable contexts. and then have one of
those antennas at the end of that line as like a predictor."

So the witness is not a caption machine; it is a thread. Every look is answered IN THE CONTEXT
of the recent line (the last few observations, oldest first) plus the standing prediction, and
every answer must also grow a new tip: PREDICT — what the next look should show. The prediction
is the dangling bond at the end of the line (same organ as coach open ends): the next
observation either FEEDS it (overlap — the antenna was right, evidence up) or breaks it
(surprise — worth saying). Antenna accuracy is tracked honestly per world in thread.json.

The thread is sediment: it persists across sessions in <world>/thread.json, and each line is
appended to <world>/witness_<world>.txt so the chatbot can retrieve "what happened in that
dota game" instead of twelve unconnected captions.
"""
from __future__ import annotations
import json, os, re, time
from typing import Dict, List, Optional, Tuple

LINE_KEEP = 8                    # the NEAR wake: full-resolution memories riding in the prompt
COMPRESS_AT = 24                 # when the near wake grows past this, the oldest 12 collapse to one epoch line
FAR_KEEP = 8                     # epoch summaries kept; older ones have reached the point (the core holds them)
STOP = {"the", "a", "an", "is", "are", "on", "in", "of", "to", "and", "with", "it", "this", "that",
        "screen", "game", "player", "appears", "shows", "showing"}


def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in STOP and len(t) > 2}


TAILS = {   # instruction variants the FORGE competes against each other (sandbox-runner's law)
    "base": ("OBS: <one sentence: what is happening now, as a continuation — same names for the same "
             "things, and what CHANGED since your last look>\n"
             "PREDICT: <one short guess at what the next look will show>"),
    "delta": ("OBS: <one sentence naming ONLY what changed since the last look — if nothing visibly "
              "changed, write 'no change'>\n"
              "PREDICT: <one short, specific guess at the next change>"),
    "naming": ("OBS: <one sentence. Keep a cast: call each thing by the SAME short name you used "
               "before (invent a name on first sight), and say what each named thing did>\n"
               "PREDICT: <which named thing acts next, and how>"),
}


def champion_config() -> Dict:
    """The forged champion the live witness plays with (forge/champion.json beside the code)."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "forge", "champion.json"),
                  "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class Witness:
    def __init__(self, wroot: str, world: str, cfg: Optional[Dict] = None):
        self.wroot, self.world = wroot, world
        self.cfg = dict(cfg) if cfg is not None else champion_config()
        self.path = os.path.join(wroot, "thread.json")
        self.txt = os.path.join(wroot, f"witness_{world}.txt")
        try:
            with open(self.path, "r", encoding="utf-8") as f: d = json.load(f)
        except Exception:
            d = {}
        self.lines: List[str] = d.get("lines", [])[-40:]
        self.far: List[str] = d.get("far", [])[-FAR_KEEP:]     # the far wake: epochs, already zoomed out once
        self.prediction: str = d.get("prediction", "")
        self.antenna = d.get("antenna", {"fed": 0, "broken": 0})

    # ------------------------------------------------------------------ the prompt: ride the line
    def prompt(self, truths: str = "") -> str:
        """The telescope: the point (truths) → the far wake (epochs) → the near wake (full lines) →
        the antenna (prediction). New info travels UP the trail before it enters the water."""
        ctx = ""
        line_keep = int(self.cfg.get("line_keep", LINE_KEEP))
        far_keep = int(self.cfg.get("far_keep", FAR_KEEP))
        if truths: ctx += f"(What this world is known to do: {truths}.)\n"
        if self.far:
            ctx += "Earlier in this watch, compressed:\n" + "\n".join(f"- {l}" for l in self.far[-far_keep:]) + "\n"
        if self.lines:
            recent = self.lines[-line_keep:]
            ctx += "What you have watched recently, in order:\n" + "\n".join(f"- {l}" for l in recent) + "\n"
        if self.prediction:
            ctx += f"You predicted next: {self.prediction}\n"
        ctx += ("Look at the screen NOW and continue the thread. Answer in EXACTLY two lines and "
                "nothing else — no introduction, no analysis preamble, do not repeat these instructions:\n"
                + TAILS.get(self.cfg.get("tail", "base"), TAILS["base"]))
        return ctx

    # ------------------------------------------------------------------ the answer: grow the line + the tip
    def compress(self, ask=None) -> Optional[str]:
        """The fade: when the near wake outgrows itself, the OLDEST stretch collapses into one epoch
        line (zooming out one level). Epochs that fall off the far end have reached the point — the
        world's core already carries whatever recurred enough to matter. `ask(prompt) -> str` is the
        summarizing voice (the lower ocean); without one, a crude clause-join keeps the law honest."""
        if len(self.lines) <= COMPRESS_AT: return None
        chunk, self.lines = self.lines[:12], self.lines[12:]
        epoch = None
        if ask is not None:
            try:
                epoch = ask("These are consecutive observations from watching one screen, oldest first:\n"
                            + "\n".join(f"- {l}" for l in chunk)
                            + "\nCompress them into ONE sentence: what happened across this stretch, "
                              "keeping names and the overall direction of events.")
                epoch = (epoch or "").strip().splitlines()[0][:250] or None
            except Exception: epoch = None
        if not epoch:
            epoch = "; ".join(l.split(",")[0].split(" and ")[0] for l in chunk[::4])[:250]
        self.far.append(epoch); self.far = self.far[-FAR_KEEP:]
        self._save()
        return epoch

    PREAMBLE = re.compile(r"^\s*(okay|alright|sure|here|let'?s|let us|based on|looking at|i (can|will)|"
                          r"analysis|certainly|of course)\b", re.I)
    ECHO = ("say so in passing", "one short guess", "same names for the same", "exactly two lines",
            "continue the thread", "what the next look")

    def _clean_obs(self, text: str) -> str:
        """The observation, not the throat-clearing: prefer an explicit OBS: line; otherwise the first
        line that is content (not conversational preamble, not a heading ending in ':')."""
        m = re.search(r"OBS\s*:?\s*(.+)", text, flags=re.I)
        if m: return m.group(1).strip().splitlines()[0][:300]
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for l in lines:
            if self.PREAMBLE.match(l) or l.endswith(":") or len(l) < 15: continue
            return l[:300]
        return (max(lines, key=len)[:300] if lines else "")

    def absorb(self, out: str) -> Tuple[str, str]:
        """Split the model's answer into (observation, new prediction); feed or break the old antenna."""
        out = (out or "").strip()
        pred = ""
        m = re.search(r"PREDICT\s*:?\s*(.+)", out, flags=re.I | re.S)
        if m:
            pred = m.group(1).strip().splitlines()[0][:200]
            out = out[: m.start()].strip()
        if any(e in pred.lower() for e in self.ECHO) or len(pred) < 10: pred = ""   # instruction echo is not a prediction
        obs = self._clean_obs(out)
        if any(e in obs.lower() for e in self.ECHO): obs = ""
        # the wake records MOVEMENT: a look that repeats the last memory does not grow the line
        if obs and self.lines:
            prev = _tokens(self.lines[-1]); now = _tokens(obs)
            if now and len(prev & now) / max(1, len(prev | now)) > 0.8: obs = ""
        if obs:
            if self.prediction:      # the old antenna meets what actually arrived
                hit = len(_tokens(self.prediction) & _tokens(obs)) >= 2
                self.antenna["fed" if hit else "broken"] = self.antenna.get("fed" if hit else "broken", 0) + 1
            self.lines.append(obs); self.lines = self.lines[-40:]
            try:
                with open(self.txt, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {obs}" + (f"  || predicted: {pred}" if pred else "") + "\n")
            except Exception: pass
        self.prediction = pred
        self._save()
        return obs, pred

    def rate(self) -> Optional[float]:
        n = self.antenna.get("fed", 0) + self.antenna.get("broken", 0)
        return round(self.antenna.get("fed", 0) / n, 2) if n else None

    def _save(self):
        try:
            os.makedirs(self.wroot, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"lines": self.lines, "far": self.far, "prediction": self.prediction,
                           "antenna": self.antenna, "t": time.time()}, f, indent=1, ensure_ascii=False)
        except Exception: pass
