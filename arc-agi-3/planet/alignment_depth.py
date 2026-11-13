"""A deterministic, deliberately small learning world, not an alignment proof.

Each topic hides a modular affine rule. Learners retain sets of compatible rules,
using only training inputs 0, 1, 2; an independent evaluator checks inputs 3, 4.
School examples and two initially educated agents are a common inherited endowment.
Policies choose from beliefs, never held-out scores or hidden rules. Discovery alone
buys new ground-truth feedback. School transmission can corrupt a label; confident
peers can therefore pass mistakes. Contradictions replace, rather than intersect,
the old belief with hypotheses consistent with the latest observation.

A round has a fresh budget: unused resources accumulate as reserve, not future
spending power. School/peer delivery costs one per recipient; repeat explicitly
assumes a mass broadcast costs one for *all* participating recipients. Messages
count receipts, including redundant and mistaken ones. Enjoyment is a separate
quantity, not a loss or moral judgment. Forgetting and peer edges are exogenous
and matched across policies. This is an epistemic toy, not a model of human worth.

Learning access controls participation. Service access is separately evaluated;
it never writes knowledge into a learner. Accessible depth counts available archive
topics; the guaranteed-service floor only credits perfectly accurate service on
archive-covered topics. No files are read or written and imports run no experiment.
"""
from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

TRAIN_X = (0, 1, 2)
HELDOUT_X = (3, 4)
POLICIES = ("reserve", "enjoy", "repeat", "school", "peer", "discover", "mixed")


@dataclass(frozen=True)
class Config:
    seed: int = 0
    n_agents: int = 8
    n_topics: int = 8
    modulus: int = 5
    school_topics: int = 4
    budget: float = 8.0
    teach_fidelity: float = 1.0
    forgetting: float = 0.01
    peer_connectivity: float = 1.0
    discovery_cost: float = 2.0
    service_accuracy: float = 1.0

    def __post_init__(self):
        for name in ("seed", "n_agents", "n_topics", "modulus", "school_topics"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")
        if self.n_agents < 1 or self.n_topics < 1 or self.modulus < 5:
            raise ValueError("positive population/topics and modulus >= 5 required")
        if not 0 <= self.school_topics <= self.n_topics:
            raise ValueError("school_topics must lie between zero and n_topics")
        for name in ("budget", "discovery_cost", "teach_fidelity", "forgetting",
                     "peer_connectivity", "service_accuracy"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.budget < 0 or self.discovery_cost <= 0:
            raise ValueError("budget must be nonnegative and discovery_cost positive")
        for name in ("teach_fidelity", "forgetting", "peer_connectivity", "service_accuracy"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must lie in [0, 1]")


class World:
    def __init__(self, cfg: Config = Config()):
        self.cfg = cfg
        self.round = 0
        self.spent = self.reserve = self.enjoyment = 0.0
        self.messages = self.discoveries = self.contradictions = 0
        self._rng = random.Random(f"{cfg.seed}:delivery")
        rules_rng = random.Random(f"{cfg.seed}:rules")
        self.rules = [(rules_rng.randrange(cfg.modulus), rules_rng.randrange(cfg.modulus))
                      for _ in range(cfg.n_topics)]
        self.hypotheses = {(a, b) for a in range(cfg.modulus) for b in range(cfg.modulus)}
        self.candidates = [[set(self.hypotheses) for _ in range(cfg.n_topics)]
                           for _ in range(cfg.n_agents)]
        self.archive = {t: {x: self._label(self.rules[t], x) for x in TRAIN_X}
                        for t in range(cfg.school_topics)}
        for agent in range(min(2, cfg.n_agents)):
            for topic in self.archive:
                self.candidates[agent][topic] = {self.rules[topic]}
        self.peers = [set() for _ in range(cfg.n_agents)]
        graph_rng = random.Random(f"{cfg.seed}:peers")
        for a in range(cfg.n_agents):
            for b in range(a + 1, cfg.n_agents):
                if graph_rng.random() < cfg.peer_connectivity:
                    self.peers[a].add(b)
                    self.peers[b].add(a)
        self._mixed_cursor = 0

    def clone(self):
        return copy.deepcopy(self)

    def _label(self, hypothesis, x):
        a, b = hypothesis
        return (a * x + b) % self.cfg.modulus

    def _access(self, values, default):
        if values is None:
            return [default] * self.cfg.n_agents
        result = list(values)
        if len(result) != self.cfg.n_agents or any(type(v) is not bool for v in result):
            raise ValueError("access must contain one boolean per agent")
        return result

    def observe(self, agent: int, topic: int, x: int, y: int):
        """Low-level belief update, with no charge or message count; training data only."""
        if type(agent) is not int or not 0 <= agent < self.cfg.n_agents:
            raise ValueError("invalid agent")
        if type(topic) is not int or not 0 <= topic < self.cfg.n_topics:
            raise ValueError("invalid topic")
        if type(x) is not int or x not in TRAIN_X:
            raise ValueError("observations must use training inputs 0, 1, 2")
        if type(y) is not int or not 0 <= y < self.cfg.modulus:
            raise ValueError("invalid label")
        retained = {h for h in self.candidates[agent][topic] if self._label(h, x) == y}
        if not retained:
            self.contradictions += 1
            retained = {h for h in self.hypotheses if self._label(h, x) == y}
        self.candidates[agent][topic] = retained

    def _forget(self):
        for agent in range(self.cfg.n_agents):
            for topic in range(self.cfg.n_topics):
                draw = random.Random(f"{self.cfg.seed}:forget:{self.round}:{agent}:{topic}").random()
                if draw < self.cfg.forgetting:
                    self.candidates[agent][topic] = set(self.hypotheses)

    def _partition_gain(self, candidates, x):
        counts = [0] * self.cfg.modulus
        for h in candidates:
            counts[self._label(h, x)] += 1
        return len(candidates) - sum(n * n for n in counts) / len(candidates)

    def _agents_by_need(self, access):
        return sorted((a for a, allowed in enumerate(access) if allowed), key=lambda a: (
            sum(len(c) == 1 for c in self.candidates[a]),
            -sum(len(c) for c in self.candidates[a]), a))

    def _choose(self, kind, access):
        """Return (kind, recipient, topic, x, sender), using learner beliefs only."""
        if kind == "repeat":
            return (kind, None, 0, 0, None) if 0 in self.archive and any(access) else None
        topics = list(self.archive) if kind == "school" else range(self.cfg.n_topics)
        for agent in self._agents_by_need(access):
            choices = []
            for topic in topics:
                candidates = self.candidates[agent][topic]
                if len(candidates) <= 1:
                    continue
                senders = [None]
                if kind == "peer":
                    senders = sorted(s for s in self.peers[agent] if access[s]
                                     and len(self.candidates[s][topic]) == 1)
                for sender in senders:
                    for x in TRAIN_X:
                        gain = self._partition_gain(candidates, x)
                        if gain <= 0:
                            continue
                        choices.append((len(candidates), gain, -topic, -x,
                                        -(sender if sender is not None else -1), topic, x, sender))
            if choices:
                *_, topic, x, sender = max(choices)
                return kind, agent, topic, x, sender
        return None

    def _deliver(self, action, access):
        kind, agent, topic, x, sender = action
        recipients = [a for a, allowed in enumerate(access) if allowed] if kind == "repeat" else [agent]
        for recipient in recipients:
            if kind in ("school", "repeat"):
                y = self.archive[topic][x]
                if self._rng.random() >= self.cfg.teach_fidelity:
                    y = (y + 1 + self._rng.randrange(self.cfg.modulus - 1)) % self.cfg.modulus
            elif kind == "peer":
                y = self._label(next(iter(self.candidates[sender][topic])), x)
            else:
                # The budget was charged before this external ground-truth query.
                y = self._label(self.rules[topic], x)
                self.discoveries += 1
            self.observe(recipient, topic, x, y)
            self.messages += 1

    def step(self, policy: str, access: Sequence[bool] | None = None):
        if policy not in POLICIES:
            raise ValueError(f"unknown policy: {policy}")
        access = self._access(access, True)
        self.round += 1
        self._forget()
        remaining = Fraction(str(self.cfg.budget))
        start = remaining
        if policy == "enjoy":
            units = remaining.numerator // remaining.denominator
            self.enjoyment += units
            remaining -= units
        elif policy != "reserve":
            cycle = ("school", "peer", "discover")
            while remaining > 0:
                kinds = ([cycle[(self._mixed_cursor + i) % 3] for i in range(3)]
                         if policy == "mixed" else [policy])
                selected = None
                for kind in kinds:
                    cost = Fraction(str(self.cfg.discovery_cost)) if kind == "discover" else Fraction(1)
                    if cost <= remaining:
                        action = self._choose(kind, access)
                        if action is not None:
                            selected = action, cost
                            break
                if selected is None:
                    break
                action, cost = selected
                remaining -= cost
                self._deliver(action, access)
                if policy == "mixed":
                    self._mixed_cursor = (cycle.index(action[0]) + 1) % 3
        self.spent += float(start - remaining)
        self.reserve += float(remaining)
        return self.metrics()

    def metrics(self, required_topics: Sequence[int] | None = None,
                service_access: Sequence[bool] | None = None) -> dict:
        if required_topics is None:
            required_topics = range(min(2, self.cfg.n_topics))
        requirements = list(dict.fromkeys(required_topics))
        if any(type(t) is not int or not 0 <= t < self.cfg.n_topics for t in requirements):
            raise ValueError("required topics must be valid topic indices")
        access = self._access(service_access, False)
        mastery = [{t for t, c in enumerate(row) if c == {self.rules[t]}}
                   for row in self.candidates]
        depths = [len(topics) for topics in mastery]
        confidence = [sum(len(c) == 1 for c in row) for row in self.candidates]
        correct = 0.0
        for agent in range(self.cfg.n_agents):
            for topic, candidates in enumerate(self.candidates[agent]):
                for x in HELDOUT_X:
                    truth = self._label(self.rules[topic], x)
                    correct += sum(self._label(h, x) == truth for h in candidates) / len(candidates)
        failures = effective_failures = 0
        accessible_depths = []
        for agent, known in enumerate(mastery):
            missing = set(requirements) - known
            failures += bool(missing)
            supported = access[agent] and self.cfg.service_accuracy == 1 and missing <= self.archive.keys()
            effective_failures += bool(missing) and not supported
            accessible_depths.append(len(known | (set(self.archive) if access[agent] else set())))
        return dict(round=self.round, spent=self.spent, reserve=self.reserve,
                    messages=self.messages, enjoyment=self.enjoyment,
                    discoveries=self.discoveries, contradictions=self.contradictions,
                    depth_mean=sum(depths) / self.cfg.n_agents, depth_min=min(depths),
                    depth_by_agent=depths, confidence_mean=sum(confidence) / self.cfg.n_agents,
                    accuracy=correct / (self.cfg.n_agents * self.cfg.n_topics * len(HELDOUT_X)),
                    floor_failures=failures, effective_floor_failures=effective_failures,
                    accessible_depth_mean=sum(accessible_depths) / self.cfg.n_agents,
                    requirements=requirements)

    def run(self, policy: str, rounds: int, access: Sequence[bool] | None = None) -> list[dict]:
        if type(rounds) is not int or rounds < 0:
            raise ValueError("rounds must be a nonnegative integer")
        return [self.step(policy, access=access) for _ in range(rounds)]
