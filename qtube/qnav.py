"""Frame-only local navigation hypotheses learned from observed body motions.

Action IDs have no built-in direction. A supplied body detector/footprint is a
perception prior. Floor colour is inferred from pixels revealed after successful
moves. A selected target box is allowed only as an explicit unverified probe.
Every executed step still needs observation checks in the caller.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import numpy as np


def learn_motion(frames, actions, body_pos, footprint=5):
    vectors = defaultdict(Counter)
    revealed = Counter()
    evidence = []
    for i, action in enumerate(actions):
        a = int(action.get("a") if isinstance(action, dict) else action)
        if a == 0:
            continue
        before, after = body_pos(frames[i]), body_pos(frames[i + 1])
        if before is None or after is None:
            continue
        delta = (after[0] - before[0], after[1] - before[1])
        vectors[a][delta] += 1
        if delta == (0, 0):
            continue
        y, x = before
        old = {(r, c) for r in range(y, y + footprint) for c in range(x, x + footprint)}
        y, x = after
        new = {(r, c) for r in range(y, y + footprint) for c in range(x, x + footprint)}
        for r, c in old - new:
            revealed[int(frames[i + 1][r, c])] += 1
        evidence.append({"transition": i, "action": a, "from": list(before),
                         "to": list(after), "delta": list(delta)})
    moves = {}
    for action, counts in vectors.items():
        nonzero = [(n, delta) for delta, n in counts.items() if delta != (0, 0)]
        # Conflicting nonzero effects require context; do not average them.
        if len(nonzero) == 1:
            moves[action] = nonzero[0][1]
    if not revealed:
        raise ValueError("No successful movements reveal a traversable surface.")
    floor, count = revealed.most_common(1)[0]
    if count / sum(revealed.values()) < 0.8:
        raise ValueError("Revealed surfaces do not support one dominant floor hypothesis.")
    return {"moves": moves, "floor_colours": [floor], "footprint": footprint,
            "revealed_counts": dict(revealed), "evidence": evidence,
            "displacement_counts": {str(a): {str(d): n for d, n in v.items()}
                                    for a, v in vectors.items()}}


def plan_to_box(frame, start, box, motion, max_steps=60, blocked=frozenset()):
    """Reach a lattice position whose body centre lies inside a candidate box.

    Ordinary steps use only inferred floor pixels and the initial body footprint.
    Steps that intersect the target are labelled probes, not known passability.
    """
    frame = np.asarray(frame)
    size = motion["footprint"]
    y0, x0, y1, x1 = map(int, box)
    target = np.zeros(frame.shape, dtype=bool)
    target[y0:y1 + 1, x0:x1 + 1] = True
    allowed = np.isin(frame, motion["floor_colours"])
    sy, sx = start
    allowed[sy:sy + size, sx:sx + size] = True
    allowed |= target
    queue, seen = deque([(tuple(start), [])]), {tuple(start)}
    while queue:
        position, path = queue.popleft()
        cy, cx = position[0] + size // 2, position[1] + size // 2
        if y0 <= cy <= y1 and x0 <= cx <= x1:
            return path
        if len(path) >= max_steps:
            continue
        for action, delta in sorted(motion["moves"].items()):
            nxt = position[0] + delta[0], position[1] + delta[1]
            y, x = nxt
            if (position, action) in blocked or nxt in seen:
                continue
            if y < 0 or x < 0 or y + size > frame.shape[0] or x + size > frame.shape[1]:
                continue
            if not allowed[y:y + size, x:x + size].all():
                continue
            probe = bool(target[y:y + size, x:x + size].any())
            row = {"action": int(action), "from": list(position), "to": list(nxt),
                   "target_probe": probe}
            seen.add(nxt)
            queue.append((nxt, path + [row]))
    return None
