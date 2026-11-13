"""Observed contact laws: learned quaternion poses plus exact evidence support.

Spatial D4 structure is supplied. Which contact causes which effect is acquired
from before/after masks. Symmetry may leave several laws observationally valid.
The frozen 7x7 encoder is a prior, not a learned game perception system.
"""
from __future__ import annotations

from collections import deque
import numpy as np
import torch
import torch.nn.functional as F

import qtest as Q
from qbridge import quat_R
from qmoments import QuaternionMoments


def embed(mask):
    mask = np.asarray(mask, dtype=np.float64)
    if mask.ndim != 2 or max(mask.shape) > 7 or any((7 - n) % 2 for n in mask.shape):
        raise ValueError("Pose encoder supports odd mask dimensions up to 7; abstain otherwise.")
    result = np.zeros((7, 7), dtype=np.float64)
    y, x = ((7 - n) // 2 for n in mask.shape)
    result[y:y + mask.shape[0], x:x + mask.shape[1]] = mask
    return result


def same_mask(a, b):
    return a.shape == b.shape and np.array_equal(a, b)


def matching_turns(before, after):
    return {i for i, turn in enumerate(Q.TURNS) if same_mask(turn(before), after)}


def unique_orbit(mask):
    masks, labels, seen = [], [], set()
    for i, turn in enumerate(Q.TURNS):
        value = turn(mask).copy()
        key = (value.shape, value.tobytes())
        if key not in seen:
            masks.append(value)
            labels.append(i)
            seen.add(key)
    return masks, labels


def mask_json(mask):
    return np.asarray(mask, dtype=int).tolist()


class ContactPoseRule:
    def __init__(self, encoder: QuaternionMoments, name, seed=0):
        self.encoder, self.name = encoder, name
        self.generator = torch.Generator().manual_seed(seed)
        self.quaternion = torch.nn.Parameter(torch.randn(4, generator=self.generator, dtype=torch.float64))
        self.optimizer = torch.optim.Adam([self.quaternion], lr=0.06)
        self.support = set(range(8))
        self.examples = []
        self.events = []
        self.contradictions = 0
        self.known_nonpose = []
        self.cache = {}
        self.fit_ok = False
        self.fit_loss = None

    def code(self, mask):
        key = (mask.shape, mask.tobytes())
        if key not in self.cache:
            with torch.no_grad():
                self.cache[key] = self.encoder.encode(torch.from_numpy(embed(mask).reshape(49)))
        return self.cache[key]

    def predict(self, mask):
        if not self.examples or not self.support:
            return None
        masks, labels = unique_orbit(mask)
        R = quat_R(self.quaternion)
        moved = self.encoder.transform(self.code(mask), R)
        with torch.no_grad():
            distances = [float(self.encoder.distance(moved, self.code(m))) for m in masks]
        chosen = int(np.argmin(distances))
        possible = []
        for turn in sorted(self.support):
            value = Q.TURNS[turn](mask).copy()
            if not any(same_mask(value, p) for p in possible):
                possible.append(value)
        consensus = len(possible) == 1
        agrees = consensus and same_mask(masks[chosen], possible[0])
        return {"mask": masks[chosen], "rotation_index": labels[chosen],
                "distances": distances, "possible_masks": possible,
                "support": sorted(self.support), "consensus": consensus,
                "verified": bool(len(self.examples) >= 2 and self.fit_ok and agrees),
                "quaternion": F.normalize(self.quaternion.detach(), dim=-1).tolist()}

    def observe(self, before, after, steps=200, provenance=None):
        candidates = matching_turns(before, after)
        event = {"name": self.name, "before": mask_json(before), "after": mask_json(after),
                 "compatible_turns": sorted(candidates), "provenance": provenance}
        if not candidates:
            self.known_nonpose.append(event)
            self.contradictions += 1
            self.support.clear()
            self.fit_ok = False
            event.update(status="non_pose_change", support_after=[])
            self.events.append(event)
            return event
        narrowed = self.support & candidates
        if not narrowed:
            self.contradictions += 1
            event.update(status="contradiction", support_after=[])
            self.support.clear()
            self.fit_ok = False
            self.events.append(event)
            return event
        self.support = narrowed
        self.examples.append((before.copy(), after.copy()))
        # Predict the observed next geometry; do not stop merely when top-1 is correct.
        def training_loss():
            R = quat_R(self.quaternion)
            return torch.stack([self.encoder.distance(
                self.encoder.transform(self.code(a), R), self.code(b))
                for a, b in self.examples]).mean()

        # A symmetric first observation can fit a reflection exactly. When a
        # later observation rules it out, that point can be a stationary saddle
        # for the new pose loss. Refit from independent starts using training
        # evidence only, before inspecting any held-out interaction.
        starts = [self.quaternion.detach().clone()] + [
            torch.randn(4, generator=self.generator, dtype=torch.float64) for _ in range(3)]
        best_loss, best_quaternion, selected_start = float("inf"), None, None
        for start_index, initial in enumerate(starts):
            with torch.no_grad():
                self.quaternion.copy_(F.normalize(initial, dim=-1))
            self.optimizer = torch.optim.Adam([self.quaternion], lr=0.06)
            for _ in range(steps):
                loss = training_loss()
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                with torch.no_grad():
                    self.quaternion.copy_(F.normalize(self.quaternion, dim=-1))
            with torch.no_grad():
                final_loss = float(training_loss())
            if final_loss < best_loss:
                best_loss = final_loss
                best_quaternion = self.quaternion.detach().clone()
                selected_start = start_index
        with torch.no_grad():
            self.quaternion.copy_(best_quaternion)
        self.fit_loss = best_loss
        self.fit_ok = bool(np.isfinite(best_loss) and best_loss <= 1e-6)
        event.update(status="learned", support_after=sorted(self.support),
                     loss=best_loss, fit_ok=self.fit_ok,
                     multistart_count=len(starts), selected_start=selected_start,
                     quaternion=F.normalize(self.quaternion.detach(), dim=-1).tolist(),
                     observations=len(self.examples))
        self.events.append(event)
        return event

    def summary(self):
        return {"name": self.name, "observations": len(self.examples),
                "fit_ok": self.fit_ok, "fit_loss": self.fit_loss,
                "support": sorted(self.support), "contradictions": self.contradictions,
                "nonpose_observations": len(self.known_nonpose),
                "quaternion": F.normalize(self.quaternion.detach(), dim=-1).tolist(),
                "events": self.events}


def plan_contacts(start, target, rules, max_depth=8):
    """BFS uses learned pose predictions only while all evidence-compatible laws agree."""
    key = lambda m: (m.shape, m.tobytes())
    queue, seen = deque([(start, [])]), {key(start)}
    while queue:
        state, path = queue.popleft()
        if same_mask(state, target):
            return path
        if len(path) >= max_depth:
            continue
        for name, rule in rules.items():
            prediction = rule.predict(state)
            if prediction is None or not prediction["verified"]:
                continue
            nxt = prediction["mask"]
            if key(nxt) not in seen:
                seen.add(key(nxt))
                queue.append((nxt, path + [name]))
    return None
