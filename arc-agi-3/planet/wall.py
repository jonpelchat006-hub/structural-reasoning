#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wall.py — THE MAP ON THE WALL: an internal map larger than vision, a window you can
drag, a border that sounds when information crosses it, and the work of keeping
vision and wall aligned.

Jonathan: "the screen is infinite and we have a window that can see a portion of it
… build the map of the game on the wall, and recognise where you are that way … the
window border plays sound as info crosses it … the wall is something you can drag
around while your vision stays put, and trying to keep those aligned is part of it."

  Atlas   : a growing 2D canvas in WORLD coordinates. Vision is a (H x W) patch of it.
            The camera species' per-frame shift is the dead-reckoning: the world moved
            (dy, dx) on screen  ⇒  vision moved (-dy, -dx) in the world. Each frame is
            stitched at the dead-reckoned position; a count map is the confidence.
  Align   : dead reckoning drifts. Every few frames the frame is matched (phase
            correlation) against the atlas around the believed position; a strong peak
            that disagrees CORRECTS the position → atom "wall.realigned". At birth the
            frame is matched against the WHOLE atlas → "wall.recognised" (I know where
            I am) or "wall.unknown_place".
  Window  : a rect in world coordinates, same size as vision, that the gaze can DRAG
            ahead of vision (the lead). Misalignment = the lead; the hand is pulled to
            bring vision back under the window. Border events: the body crossing the
            window's edge, and never-seen cells entering the window (new ground) →
            atoms "window.exit:<side>", "window.new_ground", and a sound per side.
  Sound   : winsound.Beep on Windows (optional) — a different pitch per side, a short
            tick for new ground. On the stream you HEAR the map growing.

The atlas survives death (it is the map, not the life): the coach keeps it.
"""
from __future__ import annotations
import os, threading
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

UNKNOWN = -1


class Atlas:
    def __init__(self, H: int, W: int, pad: int = 64):
        self.H, self.W, self.pad = H, W, pad
        self.canvas = np.full((H + 2 * pad, W + 2 * pad), UNKNOWN, np.int16)
        self.count = np.zeros_like(self.canvas, np.int32)
        self.origin = (pad, pad)                  # canvas index of world (0,0)
        self.pos = (0, 0)                         # world coords of vision's top-left
        self.seen_cells = 0

    # ---- canvas growth
    def _ensure(self, wy: int, wx: int) -> None:
        oy, ox = self.origin
        cy, cx = wy + oy, wx + ox
        Hc, Wc = self.canvas.shape
        top = max(0, -cy); left = max(0, -cx)
        bottom = max(0, cy + self.H - Hc); right = max(0, cx + self.W - Wc)
        if top or left or bottom or right:
            top, left, bottom, right = [v + (self.pad if v else 0) for v in (top, left, bottom, right)]
            nc = np.full((Hc + top + bottom, Wc + left + right), UNKNOWN, np.int16)
            nn = np.zeros_like(nc, np.int32)
            nc[top:top + Hc, left:left + Wc] = self.canvas; nn[top:top + Hc, left:left + Wc] = self.count
            self.canvas, self.count = nc, nn
            self.origin = (oy + top, ox + left)

    def view(self, wy: int, wx: int, h: Optional[int] = None, w: Optional[int] = None) -> np.ndarray:
        """World-coordinate crop (unknown outside the canvas)."""
        h = h or self.H; w = w or self.W
        out = np.full((h, w), UNKNOWN, np.int16)
        oy, ox = self.origin
        cy, cx = wy + oy, wx + ox
        y0, x0 = max(0, cy), max(0, cx); y1, x1 = min(self.canvas.shape[0], cy + h), min(self.canvas.shape[1], cx + w)
        if y1 > y0 and x1 > x0:
            out[y0 - cy:y1 - cy, x0 - cx:x1 - cx] = self.canvas[y0:y1, x0:x1]
        return out

    # ---- stitching
    def stitch(self, frame: np.ndarray, wy: int, wx: int, body_mask: Optional[np.ndarray] = None) -> int:
        """Paint the frame at world (wy, wx). Cells covered by the driven body are NOT written (the
        body is not the map). Returns the number of never-seen cells now known (new ground)."""
        self._ensure(wy, wx)
        oy, ox = self.origin
        cy, cx = wy + oy, wx + ox
        sl = (slice(cy, cy + self.H), slice(cx, cx + self.W))
        write = np.ones_like(frame, bool) if body_mask is None else ~body_mask
        new = int(((self.count[sl] == 0) & write).sum())
        # majority-ish: overwrite only when the cell is fresh or agrees weakly (keeps the map stable)
        cur = self.canvas[sl]; cnt = self.count[sl]
        agree = cur == frame
        cnt[write & agree] += 1
        fresh = write & (cnt <= 1) & ~agree
        cur[fresh] = frame[fresh]; cnt[fresh] = 1
        disagree = write & (cnt > 1) & ~agree
        cnt[disagree] -= 1
        self.seen_cells += new
        return new

    # ---- alignment
    @staticmethod
    def _match(frame: np.ndarray, patch: np.ndarray) -> Tuple[Tuple[int, int], float]:
        """Best (dy, dx) placing `frame` inside `patch` (patch larger or equal), with a peak score."""
        ph, pw = patch.shape; fh, fw = frame.shape
        known = patch != UNKNOWN
        if known.sum() < 0.5 * frame.size: return (0, 0), 0.0
        a = np.where(known, patch, 0).astype(float); a -= a[known].mean(); a[~known] = 0
        b = np.zeros_like(a); b[:fh, :fw] = frame - frame.mean()
        F = np.fft.fft2(a) * np.conj(np.fft.fft2(b)); F /= (np.abs(F) + 1e-9)
        corr = np.fft.ifft2(F).real
        k = np.unravel_index(int(np.argmax(corr)), corr.shape)
        dy = k[0] if k[0] <= ph - fh // 2 else k[0] - ph; dx = k[1] if k[1] <= pw - fw // 2 else k[1] - pw
        peak = float(corr.max() / (np.abs(corr).mean() * 10 + 1e-9))
        return (int(dy), int(dx)), min(1.0, peak / 10.0)

    def realign(self, frame: np.ndarray, radius: int = 6, min_peak: float = 0.35) -> Optional[Tuple[int, int]]:
        """Match the frame against the atlas around the believed position. Returns the correction
        applied (dy, dx) or None. Only corrects when the peak is strong and the shift is small."""
        wy, wx = self.pos
        patch = self.view(wy - radius, wx - radius, self.H + 2 * radius, self.W + 2 * radius)
        (dy, dx), peak = self._match(frame, patch)
        dy -= radius; dx -= radius
        if peak >= min_peak and (dy or dx) and abs(dy) <= radius and abs(dx) <= radius:
            self.pos = (wy + dy, wx + dx)
            return (dy, dx)
        return None

    def recognise(self, frame: np.ndarray, min_peak: float = 0.4) -> Optional[Tuple[int, int, float]]:
        """Global relocalisation: where in the whole atlas does this frame fit? (birth)"""
        if self.seen_cells < self.H * self.W: return None
        oy, ox = self.origin
        (dy, dx), peak = self._match(frame, self.canvas)
        if peak < min_peak: return None
        return (dy - oy, dx - ox, peak)

    # ---- persistence
    def save(self, path: str) -> None:
        np.savez_compressed(path, canvas=self.canvas, count=self.count, origin=np.array(self.origin),
                            pos=np.array(self.pos), seen=self.seen_cells)

    @classmethod
    def load(cls, path: str, H: int, W: int) -> "Atlas":
        a = cls(H, W)
        d = np.load(path)
        a.canvas, a.count = d["canvas"], d["count"]; a.origin = tuple(int(v) for v in d["origin"])
        a.pos = tuple(int(v) for v in d["pos"]); a.seen_cells = int(d["seen"])
        return a


class Window:
    """The draggable window: vision's rect plus a lead. Sounds at the border."""
    SIDES = {"L": 330, "R": 440, "T": 550, "B": 660}

    def __init__(self, H: int, W: int, sound: bool = False):
        self.H, self.W = H, W
        self.lead = (0, 0)
        self.sound = sound and os.name == "nt"
        self.body_inside = True

    def drag(self, lead: Tuple[int, int]) -> None:
        self.lead = (int(np.clip(lead[0], -self.H // 2, self.H // 2)), int(np.clip(lead[1], -self.W // 2, self.W // 2)))

    def rect(self, vision_pos: Tuple[int, int]) -> Tuple[int, int, int, int]:
        y, x = vision_pos[0] + self.lead[0], vision_pos[1] + self.lead[1]
        return y, x, y + self.H, x + self.W

    def misalignment(self) -> int:
        return abs(self.lead[0]) + abs(self.lead[1])

    def _beep(self, freq: int, ms: int = 40) -> None:
        if not self.sound: return
        try:
            import winsound
            threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()
        except Exception: pass

    def events(self, vision_pos: Tuple[int, int], body_world: Optional[Tuple[float, float]], new_ground: int,
               atlas: Atlas) -> Set[str]:
        ev: Set[str] = set()
        y0, x0, y1, x1 = self.rect(vision_pos)
        if body_world is not None:
            by, bx = body_world
            inside = y0 <= by < y1 and x0 <= bx < x1
            if self.body_inside and not inside:
                side = "T" if by < y0 else "B" if by >= y1 else "L" if bx < x0 else "R"
                ev.add(f"window.exit:{side}"); self._beep(self.SIDES[side], 80)
            elif not self.body_inside and inside:
                ev.add("window.enter"); self._beep(500, 50)
            self.body_inside = inside
        if new_ground > 0:
            ev.add("window.new_ground"); self._beep(880, 20)
        return ev


class Wall:
    """Atlas + Window, driven by the camera species and the mover."""
    def __init__(self, H: int, W: int, sound: bool = False, atlas: Optional[Atlas] = None):
        self.atlas = atlas or Atlas(H, W)
        self.window = Window(H, W, sound)
        self.frames = 0; self.realigns = 0; self.new_ground_total = 0
        self.body_world: Optional[Tuple[float, float]] = None
        self.occluders: List[Tuple[float, float]] = []       # the foreground SHEET: world spots where the body vanished

    def birth(self, frame: np.ndarray) -> Set[str]:
        """Where am I? Match against the surviving map."""
        r = self.atlas.recognise(frame)
        if r is not None:
            self.atlas.pos = (r[0], r[1]); return {"wall.recognised"}
        # unknown place: start a fresh region beside the known map
        if self.atlas.seen_cells > 0:
            self.atlas.pos = (self.atlas.pos[0] + 2 * self.atlas.H, self.atlas.pos[1])
        return {"wall.unknown_place"}

    def update(self, frame: np.ndarray, cam_shift: Tuple[int, int], body_pos: Optional[Tuple[float, float]],
               body_mask: Optional[np.ndarray], progress: Tuple[int, int] = (0, 0)) -> Set[str]:
        ev: Set[str] = set()
        dy, dx = cam_shift
        wy, wx = self.atlas.pos
        self.atlas.pos = (wy - dy, wx - dx)             # world moved (dy,dx) on screen → we moved the other way
        self.frames += 1
        if self.frames % 5 == 0:
            corr = self.atlas.realign(frame)
            if corr is not None:
                self.realigns += 1; ev.add("wall.realigned")
        new = self.atlas.stitch(frame, *self.atlas.pos, body_mask=body_mask)
        self.new_ground_total += new
        if body_pos is not None:
            self.body_world = (self.atlas.pos[0] + body_pos[0], self.atlas.pos[1] + body_pos[1])
        self.window.drag(progress)                       # the gaze drags the window ahead of vision
        ev |= self.window.events(self.atlas.pos, self.body_world, new, self.atlas)
        return ev

    def target_in_window(self, rng) -> Tuple[int, int]:
        """A random SCREEN point inside the window's leading area (the pull that re-aligns vision)."""
        ly, lx = self.window.lead
        H, W = self.atlas.H, self.atlas.W
        y = rng.randrange(H) if ly == 0 else (rng.randrange(0, H // 3) if ly < 0 else rng.randrange(2 * H // 3, H))
        x = rng.randrange(W) if lx == 0 else (rng.randrange(0, W // 3) if lx < 0 else rng.randrange(2 * W // 3, W))
        return y, x

    def summary(self) -> str:
        c = self.atlas.canvas; known = int((c != UNKNOWN).sum())
        return (f"map {known} cells over {c.shape[0]}x{c.shape[1]}, at {self.atlas.pos}, realigned {self.realigns}x, "
                f"new ground {self.new_ground_total}, lead {self.window.lead}")
