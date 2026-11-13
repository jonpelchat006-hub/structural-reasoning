#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music.py — the tunnel PLAYED ALOUD: render a forge bout's sound to an actual .wav.

Jonathan (Aug 31): "maybe we can think about the self-improvement tunnel as where music comes
from? if things don't hit the walls in the tunnel there would be no vibration. it would be like
a drum beat when it hits that midpoint. if it's fully extended, something going through would
bounce a lot and play like a guitar chord. or if it's extended but doesn't hit the walls it's
like a flute."

And that is honest acoustics, not metaphor: a struck membrane IS percussion, many reflections
between two fixed ends IS a string (Karplus-Strong synthesis literally simulates a pluck as a
delay line full of bounces), and air passing down a tube without touching the walls IS a flute
(the resonating column, edge-tone breath). So the three instruments are synthesized here by the
same physics the tunnel enacts:

  DRUM   — one decaying noise burst per wall hit, low and round: the midpoint struck.
  CHORD  — one Karplus-Strong pluck per reference job (a bounce-filled delay line — the actual
           tunnel simulation), pitch from that job's antenna rate on a pentatonic scale:
           cleaner passage = higher string. Strummed like a guitar.
  FLUTE  — one breathy sustained note per job, legato, vibrato: through without touching.
  SILENCE— two seconds of room tone with a single soft tick: the sealed tunnel, confirmed.

Usage:  python music.py             (render the newest forge bout -> forge/bout.wav)
        python music.py --play      (render then play it, Windows)
        python music.py --demo      (render all four instruments to /tmp or forge/, no ledger)
"""
from __future__ import annotations
import argparse, json, math, os, struct, sys, wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

SR = 22050
FDIR = os.path.join(HERE, "forge")
PENTA = [220.0 * 2 ** (k / 12) for k in (0, 3, 5, 7, 10, 12)]   # A minor pentatonic — no wrong notes


def _drum_hit(dur=0.5) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (70 * np.exp(-t * 3)) * t) * np.exp(-t * 9)      # pitch-dropping thump
    snap = np.random.randn(n) * np.exp(-t * 60) * 0.4                           # the stick's click
    return body + snap


def _pluck(freq: float, dur=1.6) -> np.ndarray:
    """Karplus-Strong: a delay line of length SR/freq full of noise, averaged as it bounces —
    a literal simulation of a wave reflecting down a tunnel between two fixed ends."""
    n = int(SR * dur)
    d = max(2, int(SR / freq))
    buf = np.random.randn(d)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % d]
        buf[i % d] = 0.996 * 0.5 * (buf[i % d] + buf[(i + 1) % d])
    return out * np.linspace(1, 0.85, n)


def _bow(freq: float, dur=2.2, gain=1.0) -> np.ndarray:
    """A BOWED string — the coupling instrument. A violin string is not struck or plucked: the
    bow grips and releases it in stick-slip friction, a FLAT tunnel (point contact, drum physics
    at kilohertz) continuously driving an EXTENDED tunnel (the string). Synthesized as the
    sawtooth that stick-slip motion actually produces, with a slow bow-attack envelope."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.6)     # vibrato arrives late
    ph = np.cumsum(freq * vib) / SR
    saw = 2 * (ph % 1.0) - 1.0                                                 # stick-slip waveform
    body = saw - 0.55 * np.roll(saw, int(SR / freq / 2))                       # crude body resonance
    env = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.3)             # the bow leans in
    return body * env * 0.5 * gain


def _bell(freq: float = 220.0, depth: int = 1, dur: float = None) -> np.ndarray:
    """A BELL — the bent tunnel. Bending a tube and flaring its ends is the brass/bell family,
    and a struck bell rings INHARMONIC partials (hum, prime, the minor-third tierce, quint,
    nominal — the classic church-bell recipe). Depth is the lesson: depth 1 HITS HARD (loud
    strike, short ring); depth 3 TEACHES A LOT (gentler strike, long long ring)."""
    dur = dur if dur is not None else 0.8 + 1.1 * depth
    n = int(SR * dur)
    t = np.arange(n) / SR
    partials = [(0.5, 1.0), (1.0, 0.8), (1.2, 0.6), (1.5, 0.4), (2.0, 0.35), (2.67, 0.15)]
    decay = 1.2 / max(0.6, depth)                              # deep lesson = slow decay
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * decay * (1 + r))
            for r, a in partials)
    strike = np.random.randn(n) * np.exp(-t * 90) * (0.5 if depth <= 1 else 0.2)
    return (x * (1.3 if depth <= 1 else 0.9) + strike)


def _flute(freq: float, dur=1.2) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t)                               # vibrato
    tone = (np.sin(2 * np.pi * freq * vib * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
            + 0.12 * np.sin(2 * np.pi * 3 * freq * t))
    breath = np.random.randn(n) * 0.02                                          # air over the edge
    env = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.15)             # soft in, soft out
    return (tone + breath) * env


def _mix(events) -> np.ndarray:
    """events: list of (start_seconds, samples).  Overlap-add into one track."""
    total = int(SR * (max(s + len(x) / SR for s, x in events) + 0.3)) if events else SR
    out = np.zeros(total)
    for s, x in events:
        i = int(s * SR)
        out[i:i + len(x)] += x
    peak = np.abs(out).max() or 1.0
    return out * min(1.0, 0.85 / peak)          # only ever normalize DOWN — a soft tick stays soft


def render(sound: dict, path: str) -> str:
    inst, hits = sound.get("instrument", "silence"), sound.get("hits", 0)
    notes = sound.get("notes", []) or [0.5]
    ev = []
    if inst == "drum":
        for k in range(max(1, min(hits, 8))):
            ev.append((k * 0.42, _drum_hit()))
    elif inst == "chord":
        for j, r in enumerate(notes):                                          # each job a string
            f = PENTA[min(len(PENTA) - 1, int(r * len(PENTA)))]
            ev.append((j * 0.07, _pluck(f)))                                   # strummed
        for k in range(min(hits, 6)):                                          # the bounces heard faintly
            ev.append((0.9 + k * 0.13, _drum_hit(0.18) * 0.15))
    elif inst == "flute":
        for j, r in enumerate(notes):
            f = PENTA[min(len(PENTA) - 1, int(r * len(PENTA)))]
            ev.append((j * 1.0, _flute(f)))
    else:                                                                       # silence: the sealed seam
        ev.append((1.0, _drum_hit(0.12) * 0.06))
    x = _mix(ev)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return path


def newest_bout() -> dict:
    p = os.path.join(FDIR, "ledger.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8").read().splitlines() if l.strip()]
    return rows[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--play", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        out = FDIR if os.path.isdir(FDIR) else "/tmp"
        for inst, s in (("drum", {"instrument": "drum", "hits": 3}),
                        ("chord", {"instrument": "chord", "hits": 9, "notes": [0.2, 0.5, 0.8, 0.95]}),
                        ("flute", {"instrument": "flute", "hits": 0, "notes": [0.4, 0.7, 0.9]}),
                        ("silence", {"instrument": "silence", "hits": 0})):
            print("rendered", render(s, os.path.join(out, f"demo_{inst}.wav")))
        return
    row = newest_bout()
    sound = row.get("sound")
    if not sound:
        import forge
        sound = forge.sound_of(row.get("rotation", "normal"), row.get("challenger_runs", []))
    p = render(sound, os.path.join(FDIR, "bout.wav"))
    print(f"the tunnel played {sound['instrument']} for {row.get('world')} "
          f"({sound.get('hits', 0)} wall hits) -> {p}")
    if a.play and os.name == "nt":
        import winsound
        winsound.PlaySound(p, winsound.SND_FILENAME)


if __name__ == "__main__":
    main()
