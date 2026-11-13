"""qtube_fit.py - the Q-tube's matching rule for her relations (Nov 1-2 2026). On only with MIKA_QTUBE=1.

Jonathan (Nov 1): "to actually mirror something she would just kind of pick up the thing as a picture and move it ...
the other should be the same thing just moved." In her space a picture is a flat object; spinning it in its plane and
turning it over are the 8 moves of a flat plate (all ordinary turns Q p Q^-1). Laying the moved picture on a target, the
FIT is how many cells don't line up: 0 = it plugs in (a socket, the zero at the bridge). Her relations already find every
target that fits exactly; this adds the NEAREST one when none fits exactly (a shape that is the key moved with a cell
or two different, or drawn at another scale), so the body has somewhere to aim, and tells the voice what the fit is.
Tests: qtube/qlift.py (round 4: the flat-object model recognised mirrors it was never shown, 97%).
"""
from __future__ import annotations
import os, threading
import numpy as np

def on():
    """read at every use: the flag reaches her game process after the modules are imported"""
    return os.environ.get("MIKA_QTUBE", "0") == "1"
MOVES = ["as it is", "spun a quarter", "spun a half", "spun three quarters",
         "turned over", "turned over and spun a quarter", "turned over and spun a half", "turned over and spun three quarters"]
NEAR = 0.25                         # at most one cell in four off
_local = threading.local()          # one game per thread on Kaggle: her notes stay with her game


def move(a, t):
    g = np.rot90(a, t % 4)
    return np.fliplr(g) if t >= 4 else g


def _rescale(g, shape):
    """nearest-cell resize when the two are the same picture at another whole-number scale"""
    (h, w), (H, W) = g.shape, shape
    for k in (2, 3):
        if (H, W) == (h * k, w * k): return np.kron(g, np.ones((k, k), int))
        if (h, w) == (H * k, W * k): return g.reshape(H, k, W, k).max(axis=(1, 3))
    return None


def _off(g, b):
    """cells that don't line up: the same size laid straight on, another whole-number scale resized, otherwise the
    best small shift of the one laid over the other on a common canvas"""
    if g.shape == b.shape: return int((g != b).sum())
    r = _rescale(g, b.shape)
    if r is not None: return int((r != b).sum())
    H, W = max(g.shape[0], b.shape[0]) + 2, max(g.shape[1], b.shape[1]) + 2
    cb = np.zeros((H, W), int); cb[1:1 + b.shape[0], 1:1 + b.shape[1]] = b
    best = None
    for dy in range(H - g.shape[0] + 1):
        for dx in range(W - g.shape[1] + 1):
            cg = np.zeros((H, W), int); cg[dy:dy + g.shape[0], dx:dx + g.shape[1]] = g
            o = int((cg != cb).sum())
            if best is None or o < best: best = o
    return best


def fit(a, b):
    """(move index, cells off, fraction off) of the best move of a laid on b; None when either is missing"""
    if a is None or b is None: return None
    a = (np.asarray(a) > 0).astype(int); b = (np.asarray(b) > 0).astype(int)
    if a.size > 400 or b.size > 400: return None
    best = None
    for t in range(8):
        o = _off(move(a, t), b)
        if o is not None and (best is None or o < best[1]): best = (t, o)
    if best is None: return None
    n = max(int(a.sum()), int(b.sum()), 1)
    return best[0], best[1], best[1] / n


def off_as_is(a, b):
    """cells off with no move at all (the region must actually read this way for the target to take it)"""
    if a is None or b is None: return None
    a = (np.asarray(a) > 0).astype(int); b = (np.asarray(b) > 0).astype(int)
    if a.size > 400 or b.size > 400: return None
    return _off(a, b)


def note(text):
    try:
        n = getattr(_local, "notes", [])
        if text not in n: _local.notes = (n + [text])[-3:]
    except Exception:
        pass


def notes():
    return list(getattr(_local, "notes", []))


def take():
    """the notes, once: the voice hears each fit one time"""
    n = notes(); _local.notes = []
    return n


def clear():
    _local.notes = []


def words(t, off):
    return f"{MOVES[t]}" + (" and it fits exactly" if off == 0 else f", with {off} cell{'s' if off != 1 else ''} off")
