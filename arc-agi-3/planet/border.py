#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
border.py — MAIL ARRIVES AT THE BORDER: rain rendered as experience, not as privileged text.

The channel model says incoming messages wrap around the window border with the void line as
the tube's centerline: traveling down the line vibrates the message off into the screen — sound
sheds at the border, and the content arrives as colors (the Shovelcat-checker color-channel
trick). Design rule this enforces: NOTHING gets to bypass perception. The rain used to be
injected into the reseed as trusted-ish text; now it is drawn onto the top border band of the
frame, symbol by symbol, scrolling like a ticker — so the SAME species that read the game read
the mail. A message that is not understood just leaves unexplained border events, which build
charge, which is lightning asking about it.

Encoding (deliberately learnable, not secret): each character byte becomes one of the eye's 32
symbols (level = byte % 8, edge = (byte // 8) % 4 → symbol = level + 8*edge), drawn as a 2-row
column cell on the top band, scrolling one cell per look. A tone per new symbol (330–990 Hz by
level) when sound is on. The band is masked out of the atlas (mail is weather, not geography).
"""
from __future__ import annotations
import numpy as np
from typing import List, Optional, Tuple

BAND_ROWS = 2


def encode(text: str) -> List[int]:
    """chars → the eye's 32-symbol alphabet. Same byte always the same symbol: learnable."""
    out = []
    for b in text.encode("utf-8", errors="replace"):
        out.append((b % 8) + 8 * ((b // 8) % 4))
    return out


class MailBand:
    """A ticker of symbols scrolling right-to-left along the top border band of the frame."""
    def __init__(self, messages: List[str], W: int, sound: bool = False, gap: int = 6):
        self.W = W; self.sound = sound
        stream: List[int] = []
        for m in messages[:4]:                      # a life carries at most a few letters
            stream.extend(encode(m[:240])); stream.extend([-1] * gap)
        self.stream = stream; self.head = -W        # starts fully off-screen right
        self.done = not stream

    def step(self) -> Optional[np.ndarray]:
        """Advance one cell; return the band (BAND_ROWS x W, -1 = leave frame as is), or None when over."""
        if self.done: return None
        self.head += 1
        band = np.full((BAND_ROWS, self.W), -1, np.int16)
        any_visible = False
        for x in range(self.W):
            i = self.head + x
            if 0 <= i < len(self.stream) and self.stream[i] >= 0:
                band[:, x] = self.stream[i]; any_visible = True
        if self.head >= len(self.stream):
            self.done = True; return None
        # a tone for the symbol newly entering at the right edge
        entering = self.head + self.W - 1
        if self.sound and 0 <= entering < len(self.stream) and self.stream[entering] >= 0:
            try:
                import winsound
                winsound.Beep(330 + 90 * (self.stream[entering] % 8), 25)
            except Exception: pass
        return band if any_visible else band       # an all-gap band still occupies the rows

    def mask(self, H: int) -> np.ndarray:
        m = np.zeros((H, self.W), bool)
        if not self.done: m[:BAND_ROWS, :] = True
        return m


if __name__ == "__main__":
    mb = MailBand(["hi"], W=8, sound=False, gap=2)
    n = 0
    while True:
        b = mb.step()
        if b is None: break
        n += 1
    print("ticks", n, "encoded", encode("hi"))
