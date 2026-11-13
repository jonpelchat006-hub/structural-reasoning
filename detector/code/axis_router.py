#!/usr/bin/env python3
"""
Axis Router — the Fano lateral switch for the detector's pool of axes.
=====================================================================
The detector has a POOL of independent axes (routes). No single axis wins on
every category — the benchmarks showed vision dominates on photos, mixedness/blur
and spectral lead on art. So this router does the framework's **Fano lateral
switch** (SPHERE_GENERATOR C.3): it picks, per detected category, the best
**triple** (3 axes = one quaternion triple = one Fano line) to judge with, and
keeps a shared **anchor axis** (the transfer coordinate) across switches so we
"change chart without losing where we are."

Two more framework moves are built in:
  * Closure failure mints a primitive (SPHERE_GENERATOR C.2/E.2): when the chosen
    triple cannot close on a case (missing/uncertain axes, or the axes disagree),
    that is a certificate → flag "needs a new axis" instead of forcing a verdict.
  * The altered-photo case = a GLOBAL vs LOCAL closure failure: whole-image axes
    say "real photo" while a local axis flags a seam. That cross-axis mismatch is
    the alteration signal AND points at the missing "alteration-localizer" axis.

Pool target = 7 axes = the octonion's 7 imaginary units = 7 Fano triples, one
natural bundle per category. Today 4 are built (vision, context, spectral,
mixedness); 3 are future slots (reconstruction, alteration, texture).

This file is the ROUTING LOGIC only — self-tested with mock axis scores (no API).
Wire it to the real observers: `shovelcat_checker_v6` (vision+context),
`spectral_observer`, `mixedness_observer`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import statistics


# ── the pool of axes (Fano points) ────────────────────────────────────────────
# scale tags drive the global-vs-local (altered-photo) logic.
AXES: Dict[str, dict] = {
    "vision":      {"point": 1, "scale": "global", "built": True,  "desc": "committee of vision models"},
    "spectral":    {"point": 2, "scale": "global", "built": True,  "desc": "frequency fingerprint (free)"},
    "mixedness":   {"point": 3, "scale": "local",  "built": True,  "desc": "boundary blur / C-field (free)"},
    "context":     {"point": 4, "scale": "global", "built": True,  "desc": "medium/type router"},
    "reconstruct": {"point": 5, "scale": "local",  "built": False, "desc": "DIRE re-anneal (future)"},
    "alteration":  {"point": 6, "scale": "local",  "built": False, "desc": "composite/inpaint localizer (future)"},
    "texture":     {"point": 7, "scale": "global", "built": False, "desc": "fine-detail statistics (future)"},
}

# the 7 Fano lines of PG(2,2): any two lines meet in exactly one point.
FANO_LINES = [(1, 2, 3), (1, 4, 5), (1, 6, 7), (2, 4, 6), (2, 5, 7), (3, 4, 7), (3, 5, 6)]

ANCHOR = "vision"   # the transfer coordinate kept across most switches

# ── per-category routing (the triple + weights), read off the benchmarks ──────
# weights reflect measured per-domain strength; "untuned" = no data yet, default.
ROUTING: Dict[str, List[Tuple[str, float]]] = {
    # photos: vision dominates (AUC 0.95); spectral tiebreak; mixedness support
    "photo":            [("vision", 0.60), ("spectral", 0.25), ("mixedness", 0.15)],
    # art/illustration: mixedness/blur (0.86*) + spectral (0.70) lead; vision weaker
    "digital_painting": [("mixedness", 0.40), ("spectral", 0.35), ("vision", 0.25)],
    "illustration":     [("mixedness", 0.40), ("spectral", 0.35), ("vision", 0.25)],
    # render: untuned (no benchmark) — vision-led default, flagged
    "3d_render":        [("vision", 0.50), ("mixedness", 0.30), ("spectral", 0.20)],
    # altered photo: local-heavy; pulls in the alteration axis (future)
    "altered_photo":    [("mixedness", 0.40), ("alteration", 0.40), ("vision", 0.20)],
}
UNTUNED = {"3d_render"}

GLOBAL_REAL = 0.30    # a global axis this positive = "looks like a real photo"
LOCAL_FAKE = -0.30    # a local axis this negative = "this region is manufactured"
LOW_CLOSURE = 0.45    # total present weight*confidence below this = closure failure


@dataclass
class Verdict:
    category: str
    triple: List[str]
    authenticity: float          # [0,1], 1 = authentic
    label: str
    confidence: float
    flags: List[str] = field(default_factory=list)
    detail: str = ""


def route(category: str) -> Tuple[List[str], List[Tuple[str, float]]]:
    """Fano switch: return (triple, weighted axes) for the category."""
    if category not in ROUTING:
        # leak past all categories -> use the whole built pool, flag later
        built = [a for a, m in AXES.items() if m["built"]]
        return built, [(a, 1.0 / len(built)) for a in built]
    weighted = ROUTING[category]
    return [a for a, _ in weighted], weighted


def _label(auth: float) -> str:
    if auth > 0.85: return "AUTHENTIC"
    if auth > 0.65: return "LIKELY_AUTHENTIC"
    if auth > 0.45: return "UNCERTAIN"
    if auth > 0.25: return "LIKELY_AI"
    return "AI_GENERATED"


def judge(category: str, scores: Dict[str, dict]) -> Verdict:
    """
    scores: {axis_id: {"value": -1..1 (1=real), "confidence": 0..1}}.
    Runs the category's triple, combines, and applies the mint/altered rules.
    """
    triple, weighted = route(category)
    flags: List[str] = []

    present = [(a, w) for a, w in weighted if a in scores and AXES.get(a, {}).get("built")]
    wsum = sum(w * scores[a]["confidence"] for a, w in present)

    if not present or wsum < LOW_CLOSURE:
        flags.append("closure_fail:needs_axis")   # certificate — can't close on this
    if category not in ROUTING:
        flags.append("unknown_category:leak")
    if category in UNTUNED:
        flags.append("untuned_category")
    for a, _ in weighted:
        if not AXES.get(a, {}).get("built"):
            flags.append(f"missing_axis:{a}")     # routing wants an axis we haven't built yet

    # weighted combine over present, built axes
    if present and wsum > 0:
        val = sum(w * scores[a]["confidence"] * scores[a]["value"] for a, w in present) / wsum
    else:
        val = 0.0
    auth = (val + 1) / 2

    # cross-axis disagreement (a seam at the axis level)
    vals = [scores[a]["value"] for a, _ in present]
    axis_spread = statistics.pstdev(vals) if len(vals) > 1 else 0.0

    # GLOBAL-vs-LOCAL mismatch = the altered-photo certificate
    globals_ = [scores[a]["value"] for a in scores
                if AXES.get(a, {}).get("scale") == "global" and AXES.get(a, {}).get("built")]
    locals_ = [scores[a]["value"] for a in scores
               if AXES.get(a, {}).get("scale") == "local" and AXES.get(a, {}).get("built")]
    detail = ""
    if globals_ and locals_ and statistics.fmean(globals_) > GLOBAL_REAL and min(locals_) < LOCAL_FAKE:
        flags.append("ALTERED:global_real_local_fake")
        detail = ("global axes read authentic while a local axis flags a manufactured region "
                  "— a real photo with a fake area; route to the alteration localizer.")
        auth = min(auth, 0.40)   # an alteration is not 'authentic'

    conf = round(min(1.0, wsum) * (1.0 - min(1.0, axis_spread)), 3)
    if axis_spread > 0.6:
        flags.append("axis_disagreement")

    return Verdict(category=category, triple=triple, authenticity=round(auth, 3),
                   label=_label(auth), confidence=conf, flags=flags, detail=detail)


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST (mock axis scores; no API)
# ══════════════════════════════════════════════════════════════════════════════

def _fano_shared_point_ok() -> bool:
    for i in range(len(FANO_LINES)):
        for j in range(i + 1, len(FANO_LINES)):
            if len(set(FANO_LINES[i]) & set(FANO_LINES[j])) != 1:
                return False
    return True


def self_test() -> bool:
    ok = True
    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and cond

    print("Fano structure")
    check("any two lines share exactly one point", _fano_shared_point_ok())
    check("anchor 'vision' is in the photo AND art triples",
          "vision" in route("photo")[0] and "vision" in route("digital_painting")[0])
    check("photo and art use DIFFERENT top axis",
          route("photo")[1][0][0] != route("digital_painting")[1][0][0])

    print("Routing + verdicts")
    photo = judge("photo", {"vision": {"value": 0.8, "confidence": 0.9},
                            "spectral": {"value": 0.5, "confidence": 0.7},
                            "mixedness": {"value": 0.4, "confidence": 0.6}})
    print("   ", photo.label, photo.flags)
    check("clean photo -> authentic, no flags", photo.label in ("AUTHENTIC", "LIKELY_AUTHENTIC") and not photo.flags)

    art = judge("digital_painting", {"mixedness": {"value": -0.7, "confidence": 0.8},
                                     "spectral": {"value": -0.6, "confidence": 0.7},
                                     "vision": {"value": -0.3, "confidence": 0.6}})
    print("   ", art.label, art.flags)
    check("AI art -> AI, not altered", art.label in ("LIKELY_AI", "AI_GENERATED") and "ALTERED:global_real_local_fake" not in art.flags)

    altered = judge("photo", {"vision": {"value": 0.7, "confidence": 0.9},      # global: looks real
                              "spectral": {"value": 0.4, "confidence": 0.7},    # global: real
                              "mixedness": {"value": -0.85, "confidence": 0.9}}) # local: fake region
    print("   ", altered.label, altered.flags, "|", altered.detail[:60])
    check("altered photo -> ALTERED flag (global real / local fake)",
          "ALTERED:global_real_local_fake" in altered.flags)

    unknown = judge("x_ray_scan", {"vision": {"value": 0.1, "confidence": 0.3}})
    print("   ", unknown.label, unknown.flags)
    check("unknown category -> leak + needs_axis",
          any("unknown_category" in f for f in unknown.flags) and any("needs_axis" in f for f in unknown.flags))

    altered_route = judge("altered_photo", {"mixedness": {"value": -0.8, "confidence": 0.9},
                                            "vision": {"value": 0.6, "confidence": 0.8}})
    print("   ", altered_route.label, altered_route.flags)
    check("altered_photo routing wants the (unbuilt) alteration axis",
          any("missing_axis:alteration" in f for f in altered_route.flags))

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if self_test() else 1)
