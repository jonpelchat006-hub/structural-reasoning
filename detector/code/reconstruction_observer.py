"""
reconstruction_observer.py — Axis 5 of the Shovelcat AI checker.

The re-anneal / reconstruction observer. Model-free, $0, no API, no GPU.
Drop-in sibling of `spectral_observer.py` and `mixedness_observer.py`.

--------------------------------------------------------------------------------
POLARITY WARNING — READ BEFORE WIRING THIS INTO THE COMMITTEE
--------------------------------------------------------------------------------
On Axis 1 (vision committee) convergence means AUTHENTIC: independent observers
reading the image agree, so the content is coherent (FOLDING_OBSERVERS,
SPARSE_VESICA 18.19, distinct-route-count = 1).

On THIS axis convergence means GENERATED. We are not asking whether independent
readers agree; we are asking whether the image is a fixed point of a generative
re-annealing process. On-manifold content settles back; off-manifold content does
not (FOLDING_OUTER_SLOT Part V, DIRE).

Same theta = 1 test, different reference manifold. The signs are OPPOSITE.
This module therefore emits RAW, UNSIGNED sub-measures. The combiner must map
them to p_fake with weights fit on a calibration set. Do not hand-assign a sign.
--------------------------------------------------------------------------------

Sub-measures
  A  seed_convergence      Do a blind grid seed and a content-committed outline
                           seed relax onto the SAME void lines? Over-determined
                           boundary structure => the two seeds agree.
  B  scale ladder          Run the void lines coarse->fine and fine->coarse.
                           Real edges are edges at every scale. A diffusion
                           schedule commits coarse structure at high noise and
                           detail at low noise; the handoff can leave boundaries
                           that live in only one band of the ladder.
  C  stiffness / vibration Shake the image, re-relax from the REST position,
                           measure how far the lines move and how much returns.
                           This is the "vibrate the void lines" measurement done
                           as displacement-from-equilibrium, not from scratch.
  D  round-trip            Redraw the image from its own void lines + fills, then
                           re-read the redraw. Is the image already a fixed point
                           of our own draw engine?

Grounding (see project docs)
  - dissolve quiet borders            FOLDING_PIXEL_TRANSMISSION (tested, 8/8)
  - stop at the ~1/5 void reserve,    FOLDING_SATURATION_BUDGET / FOLDING_CHANNELS
    never relax to zero mixing
  - relax until mixing stops          FOLDING_VOID_LINE_DRAW Part IV
  - successive cuts near-orthogonal   FOLDING_FLOORS 1 (mean 64.3deg, 0/8 parallel)
    -> used here only as a VALIDITY check on a degenerate relaxation
  - do NOT read pixel deformation     FOLDING_PIXEL_STRAIN (refuted)

Usage
  python reconstruction_observer.py img1.png img2.jpg --json out.json
  python reconstruction_observer.py --dir ./real --dir ./ai --json bench.json
  python reconstruction_observer.py img.png --jpeg 75      # confound control
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field, asdict

import numpy as np
from scipy import ndimage as ndi
from skimage import color, filters, graph, io, measure, segmentation, transform

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

WORK_SIDE = 512      # every image is resized to this max side. resolution is a
                     # known confound on the mixedness axis; fix it here.
VOID_RESERVE = 0.20  # the 1/5 saturation reserve. never relax past it.
COMPACTNESS = 12.0   # m in the SLIC metric; how much the line resists bending
N_RELAX_ITER = 10
BOUNDARY_TOL = 2     # px tolerance when matching two void-line sets
LADDER_K = (24, 96, 384, 1536)   # the coarse->fine level ladder
# Vibration is measured as a THERMAL LADDER, not at one amplitude. A single
# sigma produced return_spread ~= 0.002 on real Midjourney output -- no dynamic
# range at all, and no distribution to take a half-life from. Heat the image at
# several amplitudes instead and read how fast the lines let go: that decay rate
# is the half-life number SPARSE_VESICA 18.19 actually asks for.
SHAKE_SIGMAS = (0.02, 0.06, 0.14)
SHAKES_PER_SIGMA = 2
# The nudge must be a real displacement relative to the line spacing, not an
# absolute 2 px -- at 2 px restoring_fraction saturated at 0.973 +/- 0.009.
NUDGE_FRAC = 0.35    # fraction of the void-line spacing s


# --------------------------------------------------------------------------
# void-line relaxation core
# --------------------------------------------------------------------------

def _seed_grid(lab, k):
    """Blind seed: a uniform grid of thin void lines. Knows nothing about the
    image. This is the content-agnostic route."""
    h, w = lab.shape[:2]
    s = max(2.0, math.sqrt(h * w / float(k)))
    ys = np.arange(s / 2, h, s)
    xs = np.arange(s / 2, w, s)
    gy, gx = np.meshgrid(ys, xs, indexing="ij")
    gy, gx = gy.ravel(), gx.ravel()
    iy, ix = gy.astype(int), gx.astype(int)
    centers = np.zeros((len(gy), 5), float)
    centers[:, :3] = lab[iy, ix]
    centers[:, 3] = gy
    centers[:, 4] = gx
    return centers, s


def _seed_outline(lab, k):
    """Content-committed seed: put the centers in the flat interiors that the
    image's own edge structure carves out, i.e. seed FROM the outlines. Same
    count and same spacing as the grid seed, so the only difference is where
    the lines start."""
    h, w = lab.shape[:2]
    s = max(2.0, math.sqrt(h * w / float(k)))
    gray = lab[..., 0] / 100.0
    grad = filters.sobel(filters.gaussian(gray, 1.0))
    # watershed of the gradient => basins bounded by the real outlines
    markers = ndi.label(grad < np.percentile(grad, 15))[0]
    ws = segmentation.watershed(grad, markers)
    props = measure.regionprops(ws)
    cy = np.array([p.centroid[0] for p in props], float)
    cx = np.array([p.centroid[1] for p in props], float)
    area = np.array([p.area for p in props], float)
    if len(cy) == 0:
        return _seed_grid(lab, k)
    # keep the k largest basins; if there are too few, top up on a jittered grid
    order = np.argsort(-area)[:k]
    cy, cx = cy[order], cx[order]
    if len(cy) < k:
        extra, _ = _seed_grid(lab, k - len(cy))
        cy = np.concatenate([cy, extra[:, 3]])
        cx = np.concatenate([cx, extra[:, 4]])
    iy = np.clip(cy.astype(int), 0, h - 1)
    ix = np.clip(cx.astype(int), 0, w - 1)
    centers = np.zeros((len(cy), 5), float)
    centers[:, :3] = lab[iy, ix]
    centers[:, 3] = cy
    centers[:, 4] = cx
    return centers, s


def _relax(lab, centers, s, m=COMPACTNESS, n_iter=N_RELAX_ITER):
    """Slide the void lines until the mixing stops.

    Lloyd iteration in (L,a,b,y,x). Pixels that keep their colour and their
    neighbours pull their border toward nothing; pixels that mix pull it toward
    them. This is FOLDING_VOID_LINE_DRAW Part IV as an actual loop.
    """
    h, w = lab.shape[:2]
    centers = centers.copy()
    k = len(centers)
    yy = np.broadcast_to(np.arange(h)[:, None], (h, w))
    xx = np.broadcast_to(np.arange(w)[None, :], (h, w))
    labels = np.full((h, w), -1, np.int32)
    win = int(math.ceil(s))

    for _ in range(n_iter):
        dist = np.full((h, w), np.inf)
        labels[:] = -1
        for j in range(k):
            cy, cx = centers[j, 3], centers[j, 4]
            y0, y1 = max(0, int(cy - win)), min(h, int(cy + win) + 1)
            x0, x1 = max(0, int(cx - win)), min(w, int(cx + win) + 1)
            if y0 >= y1 or x0 >= x1:
                continue
            patch = lab[y0:y1, x0:x1]
            dc2 = ((patch - centers[j, :3]) ** 2).sum(-1)
            dy = np.arange(y0, y1)[:, None] - cy
            dx = np.arange(x0, x1)[None, :] - cx
            d = dc2 + (m * m / (s * s)) * (dy * dy + dx * dx)
            sub = dist[y0:y1, x0:x1]
            upd = d < sub
            sub[upd] = d[upd]
            labels[y0:y1, x0:x1][upd] = j

        miss = labels < 0
        if miss.any():
            _, idx = ndi.distance_transform_edt(miss, return_indices=True)
            labels = labels[tuple(idx)]

        flat = labels.ravel()
        cnt = np.bincount(flat, minlength=k).astype(float)
        nz = cnt > 0
        cnt_safe = np.where(nz, cnt, 1.0)
        for c in range(3):
            centers[:, c] = np.bincount(
                flat, weights=lab[..., c].ravel(), minlength=k) / cnt_safe
        centers[:, 3] = np.bincount(flat, weights=yy.ravel(), minlength=k) / cnt_safe
        centers[:, 4] = np.bincount(flat, weights=xx.ravel(), minlength=k) / cnt_safe

    # make every region simply connected so the borders are real borders
    labels = measure.label(labels, connectivity=1)
    return labels, centers


# --------------------------------------------------------------------------
# mixing energy and the void reserve
# --------------------------------------------------------------------------

def _mixing_energy(lab, labels):
    """Mean residual inside the regions: how much the pixels still mix once the
    void lines are where they are. Never goes to zero -- the wall is leaky
    (~0.83 transmissive), which is why we stop at a reserve."""
    flat = labels.ravel()
    k = flat.max() + 1
    cnt = np.bincount(flat, minlength=k).astype(float)
    cnt[cnt == 0] = 1.0
    means = np.stack([
        np.bincount(flat, weights=lab[..., c].ravel(), minlength=k) / cnt
        for c in range(3)], axis=1)
    resid = lab.reshape(-1, 3) - means[flat]
    return float(np.sqrt((resid ** 2).sum(1)).mean())


def _energy_floor(lab):
    """E0: the energy of the trivial one-region partition (no void lines at all)."""
    g = lab.reshape(-1, 3).mean(0)
    return float(np.sqrt(((lab.reshape(-1, 3) - g) ** 2).sum(1)).mean())


def _dissolve_to_reserve(rgb, lab, labels, reserve=VOID_RESERVE):
    """Dissolve quiet borders -- borders between similar pixels carry no
    information (FOLDING_PIXEL_TRANSMISSION, tested 8/8) -- and spend down to
    the reserve, never past it (FOLDING_SATURATION_BUDGET).

    The threshold is not hand-tuned: we bisect for the largest dissolve that
    keeps the residual mixing at or under reserve * E0.
    """
    e0 = _energy_floor(lab)
    target = reserve * e0
    g = graph.rag_mean_color(rgb, labels)
    lo, hi, best = 0.0, 120.0, labels
    for _ in range(9):
        mid = 0.5 * (lo + hi)
        try:
            cand = graph.cut_threshold(labels, g, mid, in_place=False)
        except Exception:
            hi = mid
            continue
        cand = measure.label(cand, connectivity=1)
        if _mixing_energy(lab, cand) <= target:
            best, lo = cand, mid          # room to dissolve more
        else:
            hi = mid                       # past the reserve, back off
    return best, e0, _mixing_energy(lab, best)


# --------------------------------------------------------------------------
# comparing two void-line sets
# --------------------------------------------------------------------------

def _boundaries(labels):
    return segmentation.find_boundaries(labels, mode="thick")


def _boundary_f(a, b, tol=BOUNDARY_TOL):
    """Symmetric F-score between two void-line sets, tol px slack.
    1.0 = the two routes landed on the same lines."""
    if a.sum() == 0 or b.sum() == 0:
        return 0.0
    da = ndi.distance_transform_edt(~a)
    db = ndi.distance_transform_edt(~b)
    prec = float((da[b] <= tol).mean())
    rec = float((db[a] <= tol).mean())
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)


def _orientation_concentration(labels):
    """Validity check, not a fake signal. Successive real cuts cross near
    orthogonally (FOLDING_FLOORS: mean 64.3deg, 0/8 parallel). If the settled
    lines are nearly all one orientation the relaxation stayed grid-locked and
    the run should not be scored."""
    b = _boundaries(labels).astype(float)
    gy = ndi.sobel(b, 0)
    gx = ndi.sobel(b, 1)
    mag = np.hypot(gy, gx)
    sel = mag > np.percentile(mag[mag > 0], 50) if (mag > 0).any() else mag > 0
    if sel.sum() < 16:
        return 1.0
    ang = (np.arctan2(gy[sel], gx[sel]) % np.pi)
    hist, _ = np.histogram(ang, bins=12, range=(0, np.pi))
    return float(hist.max() / max(1, hist.sum()))


# --------------------------------------------------------------------------
# redraw (the backward direction: void lines + fill -> image)
# --------------------------------------------------------------------------

def _redraw(rgb, labels, soften=1.0):
    """Run the membrane backward. Fill each region from its own matter (mean
    colour), then let it bleed slightly across the leaky wall. This is the
    diffusion-curves engine in its cheapest piecewise-constant form."""
    flat = labels.ravel()
    k = flat.max() + 1
    cnt = np.bincount(flat, minlength=k).astype(float)
    cnt[cnt == 0] = 1.0
    out = np.zeros_like(rgb)
    for c in range(3):
        means = np.bincount(flat, weights=rgb[..., c].ravel(), minlength=k) / cnt
        out[..., c] = means[labels]
    if soften > 0:
        out = filters.gaussian(out, soften, channel_axis=-1)
    return out


def _band_residual(a, b, sigma=1.5):
    """Structure-band residual only. The top frequency octave is where sensor
    noise, JPEG and resampling live -- exactly the confound that made the 0.86
    mixedness number untrustworthy. Blur both sides before differencing so this
    measures structure, not noise floor."""
    aa = filters.gaussian(a, sigma, channel_axis=-1)
    bb = filters.gaussian(b, sigma, channel_axis=-1)
    denom = float(aa.std()) + 1e-6
    return float(np.abs(aa - bb).mean() / denom)


# --------------------------------------------------------------------------
# the four sub-measures
# --------------------------------------------------------------------------

@dataclass
class Result:
    path: str = ""
    ok: bool = True
    note: str = ""
    seconds: float = 0.0
    # validity
    orientation_concentration: float = 0.0
    energy_floor: float = 0.0
    rest_energy_ratio: float = 0.0
    # A -- seed convergence
    seed_convergence: float = 0.0
    seed_region_ratio: float = 0.0
    # B -- scale ladder
    ladder_fb_agreement: float = 0.0
    nonmonotone_fraction: float = 0.0
    ladder_profile: list = field(default_factory=list)
    # C -- stiffness / vibration (thermal ladder)
    return_rate: float = 0.0        # mean over the whole ladder
    return_at_low: float = 0.0      # coldest shake
    return_at_high: float = 0.0     # hottest shake
    thermal_slope: float = 0.0      # d(agreement)/d(sigma) -- the decay rate
    return_spread: float = 0.0
    mean_displacement: float = 0.0
    restoring_fraction: float = 0.0
    thermal_profile: list = field(default_factory=list)
    # D -- round trip
    roundtrip_fixed_point: float = 0.0
    struct_residual: float = 0.0


def _load(path, jpeg_q=None):
    img = io.imread(path)
    if img.ndim == 2:
        img = np.stack([img] * 3, -1)
    img = img[..., :3].astype(np.float64) / 255.0
    h, w = img.shape[:2]
    scale = WORK_SIDE / float(max(h, w))
    if scale < 1.0:
        img = transform.resize(img, (int(round(h * scale)), int(round(w * scale))),
                               anti_aliasing=True)
    if jpeg_q is not None:
        import io as _io
        from PIL import Image
        buf = _io.BytesIO()
        Image.fromarray((img * 255).astype(np.uint8)).save(buf, "JPEG", quality=jpeg_q)
        buf.seek(0)
        img = np.asarray(Image.open(buf), dtype=np.float64) / 255.0
    return img


def analyse(path, jpeg_q=None, seed=0):
    t0 = time.time()
    rng = np.random.default_rng(seed)
    res = Result(path=path)
    try:
        rgb = _load(path, jpeg_q)
    except Exception as exc:                      # noqa: BLE001
        res.ok, res.note = False, f"load failed: {exc}"
        return res
    lab = color.rgb2lab(rgb)

    # ---- Stage 0: the rest position -------------------------------------
    # You cannot measure vibration without an equilibrium to vibrate about.
    # Relax first, dissolve to the reserve, and call THAT the starting position.
    k_rest = LADDER_K[2]
    c_grid, s = _seed_grid(lab, k_rest)
    lab_g, cen_g = _relax(lab, c_grid, s)
    rest, e0, e_rest = _dissolve_to_reserve(rgb, lab, lab_g)
    B_rest = _boundaries(rest)
    res.energy_floor = e0
    res.rest_energy_ratio = e_rest / (e0 + 1e-9)
    res.orientation_concentration = _orientation_concentration(rest)

    # ---- A: seed convergence (blind grid vs content-committed outline) ---
    c_out, s2 = _seed_outline(lab, k_rest)
    lab_o, _ = _relax(lab, c_out, s2)
    out_d, _, _ = _dissolve_to_reserve(rgb, lab, lab_o)
    B_out = _boundaries(out_d)
    res.seed_convergence = _boundary_f(B_rest, B_out)
    n1, n2 = rest.max() + 1, out_d.max() + 1
    res.seed_region_ratio = float(min(n1, n2) / max(n1, n2))

    # ---- B: the scale ladder, forward and backward ----------------------
    fwd = []
    for k in LADDER_K:
        c, ss = _seed_grid(lab, k)
        lb, _ = _relax(lab, c, ss, n_iter=max(5, N_RELAX_ITER // 2))
        fwd.append(_boundaries(lb))
    # backward: one fine relaxation, then dissolve upward to matching counts
    c_fine, s_fine = _seed_grid(lab, LADDER_K[-1])
    fine, _ = _relax(lab, c_fine, s_fine, n_iter=max(5, N_RELAX_ITER // 2))
    g_fine = graph.rag_mean_color(rgb, fine)
    bwd = []
    for k in LADDER_K:
        lo, hi, best = 0.0, 120.0, fine
        for _ in range(8):
            mid = 0.5 * (lo + hi)
            try:
                cand = measure.label(
                    graph.cut_threshold(fine, g_fine, mid, in_place=False),
                    connectivity=1)
            except Exception:
                hi = mid
                continue
            if cand.max() + 1 > k:
                best, lo = cand, mid
            else:
                hi = mid
        bwd.append(_boundaries(best))
    agree = [_boundary_f(f, b) for f, b in zip(fwd, bwd)]
    res.ladder_fb_agreement = float(np.mean(agree))
    res.ladder_profile = [round(a, 4) for a in agree]

    # a real edge, once born, survives to every finer level. a boundary that
    # appears mid-ladder and vanishes again is a scale orphan.
    union = np.zeros_like(fwd[0])
    for f in fwd:
        union |= f
    pres = np.stack([
        ndi.distance_transform_edt(~f)[union] <= BOUNDARY_TOL for f in fwd], 1)
    if pres.size:
        # monotone = a run of zeros then a run of ones, coarse -> fine
        mono = np.all(pres[:, 1:] >= pres[:, :-1], axis=1)
        res.nonmonotone_fraction = float(1.0 - mono.mean())

    # ---- C: stiffness / vibration about the rest position ---------------
    # heat the plate at several amplitudes and watch the sand let go
    per_sigma, disp, all_f = [], [], []
    for sigma in SHAKE_SIGMAS:
        fs = []
        for _ in range(SHAKES_PER_SIGMA):
            noisy = np.clip(rgb + rng.normal(0, sigma, rgb.shape), 0, 1)
            lab_n = color.rgb2lab(noisy)
            lb, cen = _relax(lab_n, cen_g.copy(), s, n_iter=max(4, N_RELAX_ITER // 2))
            dd, _, _ = _dissolve_to_reserve(noisy, lab_n, lb)
            fs.append(_boundary_f(B_rest, _boundaries(dd)))
            disp.append(float(np.hypot(cen[:, 3] - cen_g[:, 3],
                                       cen[:, 4] - cen_g[:, 4]).mean()))
        per_sigma.append(float(np.mean(fs)))
        all_f.extend(fs)
    res.thermal_profile = [round(v, 4) for v in per_sigma]
    res.return_rate = float(np.mean(per_sigma))
    res.return_at_low = per_sigma[0]
    res.return_at_high = per_sigma[-1]
    # slope of agreement vs noise amplitude: how fast the void lines let go as
    # the plate heats. Steeper = shallower wells = less deeply anchored lines.
    res.thermal_slope = float(np.polyfit(np.array(SHAKE_SIGMAS), per_sigma, 1)[0])
    res.return_spread = float(np.std(all_f))
    res.mean_displacement = float(np.mean(disp))

    # deterministic restoring-force probe: nudge every line off equilibrium by a
    # real fraction of the line spacing and see how much of it walks back.
    nudged = cen_g.copy()
    theta = rng.uniform(0, 2 * np.pi)
    nudge = NUDGE_FRAC * s
    nudged[:, 3] += nudge * math.sin(theta)
    nudged[:, 4] += nudge * math.cos(theta)
    lb_n, _ = _relax(lab, nudged, s, n_iter=max(4, N_RELAX_ITER // 2))
    dd_n, _, _ = _dissolve_to_reserve(rgb, lab, lb_n)
    res.restoring_fraction = _boundary_f(B_rest, _boundaries(dd_n))

    # ---- D: round trip, read -> draw -> read ----------------------------
    drawn = _redraw(rgb, rest)
    lab_d = color.rgb2lab(np.clip(drawn, 0, 1))
    c_rt, s_rt = _seed_grid(lab_d, k_rest)
    lb_rt, _ = _relax(lab_d, c_rt, s_rt)
    rt, _, _ = _dissolve_to_reserve(np.clip(drawn, 0, 1), lab_d, lb_rt)
    res.roundtrip_fixed_point = _boundary_f(B_rest, _boundaries(rt))
    res.struct_residual = _band_residual(rgb, np.clip(drawn, 0, 1))

    if res.orientation_concentration > 0.60:
        res.note = ("relaxation stayed grid-locked (orientation concentration "
                    f"{res.orientation_concentration:.2f} > 0.60); "
                    "treat this run as invalid, do not score it")
    res.seconds = time.time() - t0
    return res


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def _gather(paths, dirs):
    out = [(p, None) for p in paths]
    for d in dirs or []:
        label = os.path.basename(os.path.normpath(d))
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(EXTS):
                out.append((os.path.join(d, f), label))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("images", nargs="*")
    ap.add_argument("--dir", action="append", default=[],
                    help="directory of images; its name becomes the class label")
    ap.add_argument("--json", default=None)
    ap.add_argument("--jpeg", type=int, default=None,
                    help="recompress at this quality first (confound control)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)

    items = _gather(a.images, a.dir)
    if not items:
        ap.error("no images given")

    rows = []
    for path, label in items:
        r = analyse(path, jpeg_q=a.jpeg, seed=a.seed)
        d = asdict(r)
        d["label"] = label
        rows.append(d)
        flag = "" if r.ok and not r.note else "  [!] " + (r.note or "failed")
        print(f"{os.path.basename(path):<38} "
              f"seedconv={r.seed_convergence:.3f} "
              f"ladder={r.ladder_fb_agreement:.3f} "
              f"orphan={r.nonmonotone_fraction:.3f} "
              f"return={r.return_rate:.3f} "
              f"tslope={r.thermal_slope:+.2f} "
              f"roundtrip={r.roundtrip_fixed_point:.3f} "
              f"resid={r.struct_residual:.3f}"
              f"{flag}", flush=True)

    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"config": {"work_side": WORK_SIDE,
                                  "void_reserve": VOID_RESERVE,
                                  "ladder_k": list(LADDER_K),
                                  "shakes": SHAKES,
                                  "jpeg_q": a.jpeg},
                       "rows": rows}, fh, indent=2)
        print(f"\nwrote {a.json}")

    labels = {r["label"] for r in rows if r["label"]}
    if len(labels) == 2:
        _report_auc(rows, sorted(labels))
    return 0


def _auc(pos, neg):
    """Mann-Whitney AUC. Returns the raw, unsigned value -- 0.5 means no signal,
    and BOTH 0.9 and 0.1 mean a strong signal (0.1 just means the sign is the
    other way). The combiner picks the sign; this reports the truth."""
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    rp = r[:len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def _report_auc(rows, labels):
    a, b = labels
    feats = ["seed_convergence", "ladder_fb_agreement", "nonmonotone_fraction",
             "return_rate", "return_at_low", "return_at_high", "thermal_slope",
             "return_spread", "mean_displacement", "restoring_fraction",
             "roundtrip_fixed_point", "struct_residual", "rest_energy_ratio"]
    print(f"\nAUC ({a} vs {b}), raw and unsigned:")
    print(f"{'sub-measure':<26}{'AUC':>8}{'|AUC-.5|':>10}  direction")
    for f in feats:
        pa = np.array([r[f] for r in rows if r["label"] == a and r["ok"]])
        pb = np.array([r[f] for r in rows if r["label"] == b and r["ok"]])
        if len(pa) < 2 or len(pb) < 2:
            continue
        v = _auc(pa, pb)
        d = f"higher in {a}" if v > 0.5 else f"higher in {b}"
        print(f"{f:<26}{v:>8.3f}{abs(v - 0.5):>10.3f}  {d}")
    print("\nSign is an empirical question -- fit it on this table, "
          "do not inherit it from the committee axis.")


if __name__ == "__main__":
    sys.exit(main())
