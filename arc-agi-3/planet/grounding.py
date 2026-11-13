#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grounding.py — MEANING, ported from Jonathan's language learner
(Shovelcat-AI/lib/agents: closure-test.ts, reproduction-test.ts, concept-registry.ts,
multi-language.ts). Same definitions, same gates, in Python, with the planet's
BASE ATOMS = what the innate species can detect and the hand can do.

  Definition  : a signed bundle of features  {feature: weight in [-1, 1]}
                +1 assert (matter), -1 negate (antimatter), 0/absent don't-care (void).
                A feature is either a BASE ATOM or the id of another concept.
  Closure     : drain(C) = fraction of |weight| that reaches base atoms through
                grounded chains (fixpoint). GROUNDED (drains) / WHIRLPOOL (cycles
                inside the system, never reaches an atom — allowed, never banked) /
                LEAKING (references outside the known system — the disallowed spray).
  Reproduction: independent builders reconstruct the concept from its encoding;
                agreement rate = fraction within threshold; TRIANGULATION needs >= 2
                independent matches before graduation is even considered.
  Registry    : synonym vs new decided in GROUNDING space by the MARGIN — the smallest
                distance between concepts certified distinct — discovered from data.
  Translate   : the same concept's drain against another world's atoms; lostAtoms
                names exactly what does not carry across.

The planet's atoms (see species.py / player.py events):
  mover.moved:<action>, mover.blocked:<action>, counter.down:<colour>, counter.up:<colour>,
  object.vanished, object.appeared, camera.scrolled, surprise.region, death, respawn, ...
An event stream from a life is a sequence of atom-sets; a candidate concept is a
bundle that recurs with the same atoms; it graduates when two independent lives
(builders) reconstruct it within the margin and it drains to atoms.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import math

Definition = Dict[str, float]


# ============================================================================
# CLOSURE — does it drain?
# ============================================================================
@dataclass
class ConceptGraph:
    base_atoms: Set[str]
    concepts: Dict[str, Definition] = field(default_factory=dict)


def drains(graph: ConceptGraph, iters: int = 50) -> Dict[str, float]:
    """Fixpoint: atom drains 1; concept ref drains by that concept's drain; external ref 0.
    Pure cycles converge to 0 (whirlpool); any base exit propagates."""
    d = {cid: 0.0 for cid in graph.concepts}
    for _ in range(iters):
        nd = {}
        for cid, defn in graph.concepts.items():
            tot = sum(abs(w) for w in defn.values())
            if tot == 0: nd[cid] = 0.0; continue
            acc = 0.0
            for f, w in defn.items():
                if f in graph.base_atoms: acc += abs(w)
                elif f in graph.concepts: acc += abs(w) * d[f]
                else: acc += 0.0                      # leaking reference
            nd[cid] = acc / tot
        if all(abs(nd[c] - d[c]) < 1e-9 for c in d): d = nd; break
        d = nd
    return d


def closure(graph: ConceptGraph, cid: str) -> Dict:
    defn = graph.concepts[cid]
    leaks = [f for f in defn if f not in graph.base_atoms and f not in graph.concepts]
    dr = drains(graph).get(cid, 0.0)
    fate = "leaking" if leaks else ("grounded" if dr > 0.5 else ("whirlpool" if dr == 0.0 else "partial"))
    return {"drain": dr, "fate": fate, "leaks": leaks}


def support_atoms(graph: ConceptGraph, cid: str) -> Set[str]:
    out, seen = set(), set()
    def dfs(i):
        if i in seen: return
        seen.add(i)
        for f, w in graph.concepts.get(i, {}).items():
            if w == 0: continue
            if f in graph.base_atoms: out.add(f)
            elif f in graph.concepts: dfs(f)
    dfs(cid); return out


# ============================================================================
# REPRODUCTION — do independent builders converge?
# ============================================================================
def definition_distance(a: Definition, b: Definition) -> float:
    keys = set(a) | set(b)
    if not keys: return 0.0
    return math.sqrt(sum((a.get(k, 0.0) - b.get(k, 0.0)) ** 2 for k in keys) / len(keys))


def consensus(reconstructions: List[Definition]) -> Definition:
    keys = set().union(*[set(r) for r in reconstructions]) if reconstructions else set()
    return {k: sum(r.get(k, 0.0) for r in reconstructions) / len(reconstructions) for k in keys}


def reproduction(source: Definition, reconstructions: List[Definition], vocabulary: Set[str],
                 threshold: float = 0.35) -> Dict:
    """agreement = fraction of builders within threshold of the source; a builder that uses an
    out-of-vocabulary feature has sprayed past the edge (disqualified, drags closure down);
    fiber width = how many ways it gets (mis)read; triangulated = >= 2 independent matches."""
    matches, closed = 0, 0
    for r in reconstructions:
        inside = all(k in vocabulary for k in r)
        closed += inside
        if inside and definition_distance(source, r) <= threshold: matches += 1
    n = max(1, len(reconstructions))
    dists = [definition_distance(reconstructions[i], reconstructions[j])
             for i in range(len(reconstructions)) for j in range(i + 1, len(reconstructions))]
    return {"agreement": matches / n, "closure": closed / n, "matches": matches,
            "fiber_width": (sum(dists) / len(dists)) if dists else 0.0, "triangulated": matches >= 2,
            "score": (matches / n) * (closed / n)}


# ============================================================================
# REGISTRY — synonym or new, by the margin
# ============================================================================
@dataclass
class Registry:
    graph: ConceptGraph
    signatures: Dict[str, Definition] = field(default_factory=dict)      # behavioural consensus per concept
    variants: Dict[str, List[Definition]] = field(default_factory=dict)
    band: float = 0.05      # distances quantize at sqrt(k/n); 0.15 swallowed every overlapping bundle

    def margin(self) -> Optional[float]:
        ids = list(self.signatures)
        if len(ids) < 2: return None
        return min(definition_distance(self.signatures[a], self.signatures[b])
                   for i, a in enumerate(ids) for b in ids[i + 1:])

    def nearest(self, sig: Definition) -> Tuple[Optional[str], float]:
        best, bd = None, float("inf")
        for cid, s in self.signatures.items():
            d = definition_distance(sig, s)
            if d < bd: best, bd = cid, d
        return best, bd

    def graduate(self, cid: str, sig: Definition, defn: Definition, repro: Dict) -> Dict:
        """Gate: must drain (closure) AND triangulate (repro); then margin decides new / variant / undecided."""
        self.graph.concepts[cid] = defn
        cl = closure(self.graph, cid)
        if cl["fate"] == "leaking" or not repro.get("triangulated"):
            del self.graph.concepts[cid]
            return {"verdict": "rejected", "why": cl["fate"] if cl["fate"] == "leaking" else "not triangulated", **cl}
        near, d = self.nearest(sig)
        m = self.margin()
        if near is not None and m is not None:
            if d < m * (1 - self.band):
                del self.graph.concepts[cid]
                self.variants.setdefault(near, []).append(defn)
                return {"verdict": "variant", "of": near, "distance": d, "margin": m, **cl}
            if d < m * (1 + self.band):
                del self.graph.concepts[cid]
                return {"verdict": "undecided", "near": near, "distance": d, "margin": m, **cl}
        self.signatures[cid] = sig
        return {"verdict": "new", "nearest": near, "distance": d, "margin": m, **cl}

    def admit(self, cid: str, sig: Definition, defn: Definition) -> None:
        """Recurrence override: the margin said undecided, but the world keeps building this bundle.
        A static geometric band must not hold a permanent veto over recurring structure — evidence
        outvotes geometry (the same E/(E+lambda) law that governs everything else)."""
        self.graph.concepts[cid] = defn
        self.signatures[cid] = sig


# ============================================================================
# TRANSLATABILITY — the same concept against another world's atoms
# ============================================================================
def translatability(graph: ConceptGraph, cid: str, base_from: Set[str], base_to: Set[str]) -> Dict:
    g_from = ConceptGraph(base_from, graph.concepts); g_to = ConceptGraph(base_to, graph.concepts)
    d_from = drains(g_from).get(cid, 0.0); d_to = drains(g_to).get(cid, 0.0)
    ratio = (d_to / d_from) if d_from > 0 else 0.0
    lost = sorted(support_atoms(g_from, cid) - base_to)
    verdict = ("ungrounded" if d_from < 0.5 else "universal" if ratio >= 0.95 else
               "translatable" if ratio >= 0.7 else "lossy" if ratio > 0 else "untranslatable")
    return {"drainFrom": d_from, "drainTo": d_to, "gap": d_from - d_to, "ratio": ratio,
            "lostAtoms": lost, "verdict": verdict}


# ============================================================================
# From a life's event stream to candidate concepts (the planet's builder)
# ============================================================================
def mine_candidates(events: List[Set[str]], min_support: int = 3, max_size: int = 3,
                    max_candidates: int = 40) -> List[Definition]:
    """Recurring atom-sets in one life = candidate bundles (a crude, honest builder: co-occurrence).
    Each candidate is a signed definition over atoms present (+1). Bounded: a life yields at most
    max_candidates bundles, ranked by LIFT (how much more often the atoms co-occur than chance) so
    that atoms which are simply always on (e.g. 'window.lead') do not flood the registry."""
    from collections import Counter
    from itertools import combinations
    n = max(1, len(events))
    single = Counter(a for ev in events for a in ev)
    cnt = Counter()
    for ev in events:
        atoms = sorted(a for a in ev if single[a] < 0.9 * n)   # always-on atoms carry no information
        for k in range(2, min(max_size, len(atoms)) + 1):
            for combo in combinations(atoms, k): cnt[combo] += 1
    scored = []
    for combo, c in cnt.items():
        if c < min_support: continue
        expect = n
        for a in combo: expect *= single[a] / n
        scored.append((c / max(expect, 1e-9), c, combo))
    scored.sort(reverse=True)
    return [{a: 1.0 for a in combo} for _, _, combo in scored[:max_candidates]]


if __name__ == "__main__":
    # self-test in the spirit of the .selftest.ts files
    atoms = {"counter.up:11", "object.vanished", "mover.moved:R", "death", "respawn"}
    g = ConceptGraph(atoms, {
        "refill": {"counter.up:11": 1.0, "object.vanished": 1.0},
        "life": {"death": 1.0, "respawn": 1.0},
        "loop_a": {"loop_b": 1.0}, "loop_b": {"loop_a": 1.0},
        "leaky": {"counter.up:11": 1.0, "magic": 1.0},
    })
    for c in g.concepts: print(c, closure(g, c))
    rep = reproduction(g.concepts["refill"], [g.concepts["refill"], {"counter.up:11": 1.0, "object.vanished": 0.8},
                                              {"counter.up:11": 1.0, "somethingelse": 1.0}], atoms | set(g.concepts))
    print("repro", rep)
    print("translate refill -> world without colour 11:", translatability(g, "refill", atoms, atoms - {"counter.up:11"}))
