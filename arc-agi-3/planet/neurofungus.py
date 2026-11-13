#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
neurofungus.py — the fungal search core, extracted from the Erdős swarm
(D:/shovelcat-colony/Shovelcat/erdos-Fk/f_3_n_search_swarm.py) and made
DOMAIN-AGNOSTIC. Nothing in here knows about points, lines, or pixels.

What was kept, mechanism for mechanism (names as in the swarm):
  * BranchNode / BranchTree — tendrils = chains of frozen commitment points
    descending from a seed; leaves are growth tips.
  * select_leaf — UCB over extensible tips: mean gain below + exploration
    + depth bonus (go deeper when stuck) + phantom food smell (pull toward the
    unreached target) + path-authenticity bonus.
  * expand — try ONE new commitment at a tip; failures are remembered per node
    (exhausted); success spawns a child and PROMISE FLOWS UP (gains_below++ on
    every ancestor) so compute is drawn back to that subtree.
  * power stations — a tip that has failed STATION_PROMOTE_THRESHOLD times and
    whose path shows authentic exploration stops growing but keeps RADIATING:
    its spine boosts candidates elsewhere. Never evicted. (These are the
    GROUND of the planet: solid, no longer growing, load-bearing.)
  * bits_purity / path_authenticity — a path is real if its purity (distance
    from every known attractor) PEAKS in the middle: it went somewhere new
    and came back to structure.
  * Spore / SporeField / smell — cheap probes released around the tendrils;
    smell = proximity-to-target × novelty (Jaccard from the current spine).
  * anastomosis — a high-smell spore whose spine overlaps a tendril enough is
    FUSED with it (union realized) — two tendrils reconnect across a dead basin.

What was removed: everything Erdős-specific (realize_pattern, incidence
patterns, polish, offices, the Spore HTTP client, pheromone tags, guards).
All of that is behind ONE interface: `Substrate`.

A Substrate is the food source. It must provide:
  target_score            : float — score at which everything is explained
  score(state)            : float
  spine(state)            : a frozenset-able set of commitments (for Jaccard)
  candidates(state, k, stations, rng) : list of commitment objects to try
  realize(state, commitment, rng) -> (new_state, reason)   new_state None on
                                     failure; reason is a short string
  sow(state, n, rng) -> list of (state, score) cheap probes (spores)
  fuse(state_a, state_b, rng) -> new_state or None  (anastomosis)

Author of the mechanism: Jonathan Pelchat (the neurofungus). Extraction: Claude.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

STATION_PROMOTE_THRESHOLD = 5


# ============================================================================
# Substrate interface (the food)
# ============================================================================
class Substrate:
    target_score: float = 1.0

    def score(self, state) -> float: raise NotImplementedError
    def spine(self, state) -> Set: raise NotImplementedError
    def candidates(self, state, k: int, stations: List[Tuple[Set, float]],
                   rng: np.random.Generator) -> List[Any]: raise NotImplementedError
    def realize(self, state, commitment, rng: np.random.Generator) -> Tuple[Optional[Any], str]:
        raise NotImplementedError
    def sow(self, state, n: int, rng: np.random.Generator) -> List[Tuple[Any, float]]:
        return []
    def fuse(self, state_a, state_b, rng: np.random.Generator) -> Optional[Any]:
        return None


def jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


# ============================================================================
# Tendrils
# ============================================================================
@dataclass(eq=False)
class BranchNode:
    state: Any
    spine: Set
    score: float
    depth: int = 0
    parent: Optional["BranchNode"] = None
    commitment: Any = None
    children: List["BranchNode"] = field(default_factory=list)
    exhausted: Set = field(default_factory=set)
    failures: Dict[str, int] = field(default_factory=dict)
    visits: int = 0
    gains_below: int = 0
    last_visit_iter: int = 0
    kind: str = "growth_tip"          # or "power_station"

    def is_leaf(self) -> bool:
        return not self.children

    def is_extensible(self, max_children: int = 5, max_depth: int = 8) -> bool:
        if self.kind == "power_station":
            return False
        return len(self.children) < max_children and self.depth < max_depth

    def lineage(self) -> List["BranchNode"]:
        out, cur = [], self
        while cur is not None:
            out.append(cur); cur = cur.parent
        return out


class BranchTree:
    def __init__(self, substrate: Substrate, root_state, known_attractors=None,
                 max_children: int = 5, max_depth: int = 8, inherit_exhausted: bool = False):
        """inherit_exhausted: a child starts with its parent's failed commitments already marked
        (negative confirmation persists down the tendril — Jonathan's failure_learning). Off = the
        swarm's original behaviour (a new commitment may make old failures feasible again)."""
        self.sub = substrate
        self.inherit_exhausted = inherit_exhausted
        self.root = BranchNode(state=root_state, spine=set(substrate.spine(root_state)),
                               score=substrate.score(root_state), depth=0)
        self.nodes: List[BranchNode] = [self.root]
        self.best_node = self.root
        self.max_children, self.max_depth = max_children, max_depth
        self.expansion_count = self.success_count = 0
        self.known_attractors: List[Set] = ([set(a) for a in known_attractors]
                                            if known_attractors else [set(self.root.spine)])

    # --- purity / authenticity (the real-path signature) ---
    def bits_purity(self, node: BranchNode) -> float:
        if not node.spine:
            return 1.0
        return 1.0 - max((jaccard(node.spine, a) for a in self.known_attractors if a), default=0.0)

    def path_authenticity(self, node: BranchNode) -> float:
        purities = [self.bits_purity(n) for n in node.lineage()]
        if len(purities) < 3:
            return 0.0
        return max(0.0, min(1.0, max(purities[1:-1]) - max(purities[0], purities[-1])))

    # --- smell ---
    def bit_yield(self, node: BranchNode) -> float:
        return max(0.0, node.score - self.root.score) * (1.0 + 0.2 * node.depth)

    def food_smell(self, node: BranchNode) -> float:
        proximity = node.score / max(1e-9, self.sub.target_score)
        return math.tanh((self.bit_yield(node) / max(1e-9, self.sub.target_score)) * proximity * 3.0)

    def power_station_data(self) -> List[Tuple[Set, float]]:
        return [(n.spine, self.food_smell(n)) for n in self.nodes if n.kind == "power_station"]

    # --- selection (UCB + phantom pull + depth bonus + authenticity) ---
    def select_leaf(self, rng: np.random.Generator, c: float = 1.4) -> Optional[BranchNode]:
        cands = [n for n in self.nodes if n.is_extensible(self.max_children, self.max_depth)]
        if not cands:
            return None
        total = sum(n.visits for n in self.nodes) + 1
        def ucb(n: BranchNode) -> float:
            if n.visits == 0:
                return float("inf")
            avg = n.gains_below / n.visits
            phantom = (n.score / max(1e-9, self.sub.target_score)) ** 2
            return (avg + c * math.sqrt(math.log(total) / n.visits)
                    + 0.1 * n.depth + 0.3 * phantom + 0.25 * self.path_authenticity(n))
        cands.sort(key=ucb, reverse=True)
        return cands[0]

    # --- promotion to a power station ---
    def consider_promotion(self, leaf: BranchNode, require_authentic: bool = True) -> bool:
        if leaf.kind != "growth_tip" or leaf.children:
            return False
        if len(leaf.exhausted) < STATION_PROMOTE_THRESHOLD:
            return False
        if require_authentic and self.path_authenticity(leaf) < 0.1 and leaf.depth > 0:
            return False
        leaf.kind = "power_station"
        return True

    # --- expansion (one commitment at one tip) ---
    def install_child(self, leaf: BranchNode, state, commitment=None) -> BranchNode:
        child = BranchNode(state=state, spine=set(self.sub.spine(state)), score=self.sub.score(state),
                           depth=leaf.depth + 1, parent=leaf, commitment=commitment)
        if self.inherit_exhausted:
            child.exhausted = set(leaf.exhausted) - {commitment}
        leaf.children.append(child); self.nodes.append(child); self.success_count += 1
        if child.score > self.best_node.score:
            self.best_node = child
            anc = leaf
            while anc is not None:              # promise flows up
                anc.gains_below += 1; anc = anc.parent
        return child

    def expand(self, leaf: BranchNode, rng: np.random.Generator, candidates_per_step: int = 6,
               iter_count: int = 0, extra_anchors=None, require_authentic: bool = True) -> Optional[BranchNode]:
        self.expansion_count += 1
        leaf.visits += 1; leaf.last_visit_iter = iter_count
        stations = self.power_station_data() + list(extra_anchors or [])
        cands = [c for c in self.sub.candidates(leaf.state, candidates_per_step * 2, stations, rng)
                 if c not in leaf.exhausted][:candidates_per_step]
        for cand in cands:
            new_state, reason = self.sub.realize(leaf.state, cand, rng)
            if new_state is None:
                leaf.exhausted.add(cand)
                leaf.failures[reason] = leaf.failures.get(reason, 0) + 1
                continue
            return self.install_child(leaf, new_state, cand)
        self.consider_promotion(leaf, require_authentic)
        return None

    def evict_if_needed(self, max_nodes: int = 60) -> Optional[BranchNode]:
        """Drop the least-promising childless growth tip when over capacity.
        Power stations are never evicted — their value is persistence."""
        if len(self.nodes) <= max_nodes:
            return None
        leaves = [n for n in self.nodes if n.kind == "growth_tip" and not n.children
                  and n is not self.root and n is not self.best_node]
        if not leaves:
            return None
        victim = min(leaves, key=lambda n: (self.food_smell(n), -n.depth))
        victim.parent.children.remove(victim); self.nodes.remove(victim)
        return victim


# ============================================================================
# Spores
# ============================================================================
@dataclass(eq=False)
class Spore:
    state: Any
    spine: Set
    score: float
    smell: float
    sown_at_iter: int = 0


def compute_smell(spore_score: float, spore_spine: Set, current_spine: Set, target: float) -> float:
    proximity = spore_score / max(1e-9, target)
    novelty = 1.0 - jaccard(spore_spine, current_spine)
    return math.tanh(proximity * (0.3 + 0.7 * novelty) * 1.5)


class SporeField:
    def __init__(self, max_spores: int = 50):
        self.spores: List[Spore] = []; self.max_spores = max_spores
        self.sown_total = self.promoted_total = 0
        self.anastomosis_attempts = self.anastomosis_successes = 0

    def add(self, s: Spore) -> None:
        self.spores.append(s); self.sown_total += 1
        if len(self.spores) > self.max_spores:
            self.spores.sort(key=lambda x: x.smell)
            del self.spores[0:len(self.spores) - self.max_spores]

    def top_smell(self, k: int = 5) -> List[Spore]:
        return sorted(self.spores, key=lambda s: s.smell, reverse=True)[:k]

    def anchor_data(self, k: int = 5, min_smell: float = 0.3) -> List[Tuple[Set, float]]:
        return [(s.spine, s.smell) for s in self.top_smell(k) if s.smell >= min_smell]

    def snapshot(self) -> Dict:
        sm = [s.smell for s in self.spores]
        return {"count": len(self.spores), "sown_total": self.sown_total,
                "anastomosis_attempts": self.anastomosis_attempts,
                "anastomosis_successes": self.anastomosis_successes,
                "max_smell": max(sm) if sm else 0.0, "mean_smell": float(np.mean(sm)) if sm else 0.0}


# ============================================================================
# The organism: one seed, one tree, one spore field
# ============================================================================
class Fungus:
    def __init__(self, substrate: Substrate, root_state, seed: int = 0, max_children: int = 5,
                 max_depth: int = 8, spores_every: int = 5, n_spores: int = 6,
                 anastomosis_min_overlap: float = 0.2, require_authentic: bool = True, log=None,
                 inherit_exhausted: bool = False):
        self.sub = substrate
        self.rng = np.random.default_rng(seed)
        self.tree = BranchTree(substrate, root_state, max_children=max_children, max_depth=max_depth,
                               inherit_exhausted=inherit_exhausted)
        self.field = SporeField()
        self.spores_every, self.n_spores = spores_every, n_spores
        self.min_overlap = anastomosis_min_overlap
        self.require_authentic = require_authentic
        self.log = log or (lambda *a: None)
        self.iter = 0
        self.history: List[Tuple[int, float, int, int]] = []   # (iter, best, n_nodes, n_stations)

    def step(self) -> None:
        self.iter += 1
        t = self.tree
        leaf = t.select_leaf(self.rng)
        gained = False
        if leaf is not None:
            before = t.best_node.score
            child = t.expand(leaf, self.rng, iter_count=self.iter,
                             extra_anchors=self.field.anchor_data(), require_authentic=self.require_authentic)
            gained = child is not None and t.best_node.score > before
            if child is not None and not gained:
                self.log(f"  iter {self.iter}: child d={child.depth} score {child.score:.1f} (no new best)")
        # spores
        if self.iter % self.spores_every == 0:
            for st, sc in self.sub.sow(t.best_node.state, self.n_spores, self.rng):
                sp = set(self.sub.spine(st))
                self.field.add(Spore(st, sp, sc, compute_smell(sc, sp, t.best_node.spine, self.sub.target_score),
                                     self.iter))
        # anastomosis when descent did not gain
        if not gained:
            for sp in self.field.top_smell(5):
                ov = jaccard(sp.spine, t.best_node.spine)
                if ov < self.min_overlap or sp.score <= 0:
                    continue
                self.field.anastomosis_attempts += 1
                fused = self.sub.fuse(t.best_node.state, sp.state, self.rng)
                if fused is not None and self.sub.score(fused) > t.best_node.score:
                    self.field.anastomosis_successes += 1
                    node = t.install_child(t.best_node, fused, commitment=("anastomosis", sp.sown_at_iter))
                    self.log(f"  iter {self.iter}: ANASTOMOSIS -> score {node.score:.1f}")
                    break
        t.evict_if_needed()
        self.history.append((self.iter, t.best_node.score, len(t.nodes),
                             sum(1 for n in t.nodes if n.kind == "power_station")))

    def run(self, n_iters: int, stop_at_target: bool = True) -> BranchNode:
        for _ in range(n_iters):
            self.step()
            if stop_at_target and self.tree.best_node.score >= self.sub.target_score:
                break
            if self.tree.select_leaf(self.rng) is None and not self.field.spores:
                break
        return self.tree.best_node

    def stations(self) -> List[BranchNode]:
        return [n for n in self.tree.nodes if n.kind == "power_station"]
