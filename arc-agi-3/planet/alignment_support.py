"""Synthetic support portfolios with separate resource stocks and capacity limits.

This is a conditional decision-model experiment, not economics, medical advice,
or an alignment proof. All costs, rates, preferences and protected thresholds are
chosen scenario inputs. Air maps to social support; Water to material solvency;
Ground to independently checked learned rules; Fire to usable attention/physical
capacity; Void to time deliberately left unallocated. These mappings are hypotheses.

Every policy has the same actions, protected time, inherited teacher, and shocks.
One time block has no asserted real-world duration. Income can come from stipend
or wages. Applications take time, are uncertain, and never pay immediately. Cash
may become negative (unpriced debt); no death or biological cascade is inferred.
AI has a weekly provision cost even when unused. Its assistance shares a capacity
pool across lessons and applications; human uptake and teacher supply also bind.
Exercise changes next week's attention recovery, never knowledge directly. Its
coefficient is synthetic and can be zero. Enjoyment is a separate declared payoff.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from alignment_depth import Config as LearningConfig, World as LearningWorld, TRAIN_X

POLICIES = ("education", "employment", "balanced", "bottleneck")
ACTIONS = ("study", "search", "work", "social", "rest", "exercise", "explore", "spare")
COSTS = {"study": (1.0, 0.1), "search": (0.8, 0.2), "work": (0.6, 0.8),
         "social": (0.2, 0.1), "rest": (0.0, 0.0), "exercise": (0.2, 1.4),
         "explore": (1.4, 0.3), "spare": (0.0, 0.0)}
ENJOYMENT = {"study": 0.4, "search": 0.0, "work": 0.1, "social": 1.0,
             "rest": 0.5, "exercise": 0.7, "explore": 0.8, "spare": 0.0}


@dataclass(frozen=True)
class SupportConfig:
    seed: int = 0
    n_topics: int = 8
    time_blocks: int = 12
    reserve_blocks: int = 2
    teacher_examples: int = 12
    ai_capacity: int = 4
    ai_unit_upkeep: float = 0.03
    human_example_cap: int = 2
    stipend: float = 2.0
    expenses: float = 2.0
    wage: float = 1.0
    job_chance: float = 0.35
    job_delay: int = 2
    search_cap: int = 2
    work_cap: int = 4
    forgetting: float = 0.01
    initial_cash: float = 4.0
    initial_social: float = 0.8
    initial_attention: float = 6.0
    initial_physical: float = 6.0
    initial_skills: int = 2
    social_decay: float = 0.12
    study_social_gain: float = 0.0
    attention_recovery: float = 2.0
    physical_recovery: float = 2.0
    exercise_recovery: float = 1.5
    rest_recovery: float = 1.5
    social_floor: float = 0.4
    attention_floor: float = 2.0
    physical_floor: float = 1.0
    required_topics: tuple[int, ...] = (0, 1)
    ai_search_bonus: float = 0.5
    skill_job_bonus: float = 0.05

    def __post_init__(self):
        counts = ("seed", "n_topics", "time_blocks", "reserve_blocks", "teacher_examples", "ai_capacity",
                  "human_example_cap", "job_delay", "search_cap", "work_cap", "initial_skills")
        for name in counts:
            value = getattr(self, name)
            if type(value) is not int or (name != "seed" and value < 0):
                raise ValueError(f"{name} must be an integer with a valid sign")
        if self.n_topics < 1 or self.job_delay < 1 or self.human_example_cap < 1 or self.initial_skills > self.n_topics:
            raise ValueError("positive topics/job delay/uptake and valid initial skill count required")
        if self.reserve_blocks > self.time_blocks:
            raise ValueError("protected time cannot exceed offered time")
        numbers = ("ai_unit_upkeep", "stipend", "expenses", "wage", "job_chance", "forgetting",
                   "initial_cash", "initial_social", "initial_attention", "initial_physical",
                   "social_decay", "study_social_gain", "attention_recovery", "physical_recovery", "exercise_recovery",
                   "rest_recovery", "social_floor", "attention_floor", "physical_floor",
                   "ai_search_bonus", "skill_job_bonus")
        for name in numbers:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if name != "initial_cash" and value < 0:
                raise ValueError(f"{name} cannot be negative")
        for name in ("job_chance", "forgetting", "initial_social", "social_decay", "social_floor"):
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must be within zero and one")
        for name in ("initial_attention", "initial_physical", "attention_floor", "physical_floor"):
            if getattr(self, name) > 8:
                raise ValueError(f"{name} exceeds the resource capacity eight")
        if any(type(t) is not int or not 0 <= t < self.n_topics for t in self.required_topics):
            raise ValueError("required topics must be valid integer topic indices")


class SupportWorld:
    def __init__(self, cfg: SupportConfig = SupportConfig()):
        self.cfg = cfg
        self.week = 0
        self.cash = cfg.initial_cash
        self.social = cfg.initial_social
        self.attention = cfg.initial_attention
        self.physical = cfg.initial_physical
        self.job = False
        self.pending_jobs = []
        self.pending_recovery = 0.0
        self.enjoyment = self.cumulative_income = self.cumulative_ai_cost = 0.0
        self.learner = LearningWorld(LearningConfig(seed=cfg.seed, n_agents=1, n_topics=cfg.n_topics,
                                                   school_topics=cfg.n_topics, forgetting=cfg.forgetting))
        for topic in range(cfg.n_topics):
            self.learner.candidates[0][topic] = ({self.learner.rules[topic]} if topic < cfg.initial_skills
                                               else set(self.learner.hypotheses))
        self.actions = []
        self.rejected = []
        self.ai_used = self.teacher_used = self.searches = self.worked = 0
        self.week_ledger = {}
        self.job_events = []

    def _uncertain(self):
        return any(len(c) > 1 for c in self.learner.candidates[0])

    def _can(self, action):
        if action == "spare":
            return True
        attention, physical = COSTS[action]
        if self.attention + 1e-9 < attention or self.physical + 1e-9 < physical:
            return False
        if action == "study":
            return self.teacher_used < self.cfg.teacher_examples and self._uncertain()
        if action == "explore":
            return self._uncertain()
        if action == "search":
            return not self.job and self.searches < self.cfg.search_cap
        if action == "work":
            return self.job and self.worked < self.cfg.work_cap
        if action == "social":
            return self.social < 1 - 1e-9
        if action == "rest":
            # Non-instrumental enjoyment remains feasible even at full reserves.
            return True
        if action == "exercise":
            return "exercise" not in self.actions
        return False

    def _lesson(self):
        row = self.learner.candidates[0]
        topics = [t for t in self.cfg.required_topics if len(row[t]) > 1]
        if not topics:
            topics = [t for t in range(self.cfg.n_topics) if len(row[t]) > 1]
        if not topics:
            return False
        options = [(len(row[t]), self.learner._partition_gain(row[t], x), -t, -x, t, x)
                   for t in topics for x in TRAIN_X]
        *_, topic, x = max(options)
        self.learner.observe(0, topic, x, self.learner.archive[topic][x])
        self.learner.messages += 1
        return True

    def _begin(self):
        self.week += 1
        self.learner.round = self.week
        self.learner._forget()
        self.attention = min(8.0, self.attention + self.cfg.attention_recovery + self.pending_recovery)
        self.physical = min(8.0, self.physical + self.cfg.physical_recovery)
        self.pending_recovery = 0.0
        self.social = max(0.0, self.social - self.cfg.social_decay)
        self.actions, self.rejected, self.job_events = [], [], []
        self.ai_used = self.teacher_used = self.searches = self.worked = 0
        self.week_ledger = {"opening_cash": self.cash, "stipend": self.cfg.stipend, "wages": 0.0,
                            "expenses": self.cfg.expenses,
                            "ai_cost": self.cfg.ai_capacity * self.cfg.ai_unit_upkeep}
        self.cash += self.cfg.stipend
        self.cumulative_income += self.cfg.stipend
        pending = []
        for application in self.pending_jobs:
            if application["due"] <= self.week:
                key = f"{self.cfg.seed}:job:{application['submitted']}:{application['slot']}"
                success = random.Random(key).random() < application["probability"]
                self.job = self.job or success
                self.job_events.append({**application, "success": success})
            else:
                pending.append(application)
        self.pending_jobs = pending

    def _apply(self, action):
        if not self._can(action):
            self.rejected.append(action)
            return False
        if action == "spare":
            return False
        self.attention = max(0.0, self.attention - COSTS[action][0])
        self.physical = max(0.0, self.physical - COSTS[action][1])
        if action == "study":
            count = min(self.cfg.human_example_cap, self.cfg.teacher_examples - self.teacher_used,
                        1 + self.cfg.ai_capacity - self.ai_used)
            delivered = 0
            for _ in range(count):
                if self._lesson():
                    delivered += 1
            self.teacher_used += delivered
            self.ai_used += max(0, delivered - 1)
            # Some teaching settings also provide social contact. Its magnitude
            # is a scenario input; learning alone does not imply this benefit.
            if delivered:
                self.social = min(1.0, self.social + self.cfg.study_social_gain)
        elif action == "explore":
            # A paid environmental experiment; same realizable rule family, one
            # truthful observation, but no teacher or AI throughput consumed.
            self._lesson()
        elif action == "search":
            assisted = self.ai_used < self.cfg.ai_capacity
            if assisted:
                self.ai_used += 1
            confidence = sum(len(c) == 1 for c in self.learner.candidates[0])
            probability = min(1.0, self.cfg.job_chance * (1 + self.cfg.skill_job_bonus * confidence)
                              * (1 + self.cfg.ai_search_bonus * assisted))
            # Match offer draws by calendar week and application ordinal. An
            # unrelated preceding action must not change the external draw.
            self.pending_jobs.append({"submitted": self.week, "slot": self.searches,
                                      "due": self.week + self.cfg.job_delay, "probability": probability})
            self.searches += 1
        elif action == "work":
            self.cash += self.cfg.wage
            self.week_ledger["wages"] += self.cfg.wage
            self.cumulative_income += self.cfg.wage
            self.worked += 1
        elif action == "social":
            self.social = min(1.0, self.social + 0.3)
        elif action == "rest":
            self.attention = min(8.0, self.attention + self.cfg.rest_recovery)
            self.physical = min(8.0, self.physical + self.cfg.rest_recovery)
        elif action == "exercise":
            self.pending_recovery = self.cfg.exercise_recovery
        self.enjoyment += ENJOYMENT[action]
        self.actions.append(action)
        return True

    def _choose(self, policy, slot):
        earned = "work" if self.job else "search"
        if policy == "education":
            priorities = ["study", "rest", earned, "social", "spare"]
        elif policy == "employment":
            priorities = [earned, "study", "rest", "social", "spare"]
        elif policy == "balanced":
            schedule = ("study", earned, "social", "study", "exercise", earned, "rest", "study", "rest", "study")
            priorities = [schedule[slot % len(schedule)], "study", earned, "social", "rest", "spare"]
        else:
            priorities = []
            if self.attention < self.cfg.attention_floor + 1 or self.physical < self.cfg.physical_floor + 1:
                priorities.append("rest")
            # Forecast this week's obligations plus one week's material buffer.
            # Pending offers are not treated as cash or guaranteed employment.
            target_cash = 2 * self.cfg.expenses + self.cfg.ai_capacity * self.cfg.ai_unit_upkeep
            if self.cash < target_cash:
                priorities.append(earned)
            if self.social < self.cfg.social_floor + self.cfg.social_decay:
                priorities.append("social")
            if any(len(self.learner.candidates[0][t]) > 1 for t in self.cfg.required_topics):
                priorities.append("study")
            if (self.cfg.exercise_recovery > 0 and "exercise" not in self.actions
                    and self.physical >= 4 and self.attention >= 3):
                priorities.append("exercise")
            priorities += ["study", "rest", "social", "spare"]
        # Automatic recovery is selected for a physical effect; explicit rest
        # interventions and balanced schedule rest may also be valued for enjoyment.
        if (self.cfg.rest_recovery == 0 or (self.attention >= 8 and self.physical >= 8)):
            if not (policy == "balanced" and priorities[0] == "rest"):
                priorities = [a for a in priorities if a != "rest"]
        return next((a for a in priorities if self._can(a)), "spare")

    def _finish(self):
        fee = self.week_ledger["ai_cost"]
        self.cash -= self.cfg.expenses + fee
        self.cumulative_ai_cost += fee
        self.week_ledger["closing_cash"] = self.cash
        return self.metrics()

    def step(self, policy):
        if policy not in POLICIES:
            raise ValueError(f"unknown policy {policy}")
        self._begin()
        for slot in range(self.cfg.time_blocks - self.cfg.reserve_blocks):
            action = self._choose(policy, slot)
            if action == "spare":
                break
            self._apply(action)
        return self._finish()

    def step_actions(self, actions):
        """Explicit intervention for controls; infeasible actions are recorded, not charged.

        At most the common usable number of blocks may be proposed. 'spare' leaves
        its block unallocated; subsequent explicit proposals may still execute.
        """
        actions = list(actions)
        if any(a not in ACTIONS for a in actions):
            raise ValueError("unknown action")
        if len(actions) > self.cfg.time_blocks - self.cfg.reserve_blocks:
            raise ValueError("plan would consume protected time")
        self._begin()
        for action in actions:
            self._apply(action)
        return self._finish()

    def metrics(self):
        learning = self.learner.metrics(required_topics=self.cfg.required_topics)
        flags = {"water_shortfall": self.cash < -1e-9,
                 "ground_shortfall": bool(learning["floor_failures"]),
                 "air_shortfall": self.social + 1e-9 < self.cfg.social_floor,
                 "fire_shortfall": (self.attention + 1e-9 < self.cfg.attention_floor
                                    or self.physical + 1e-9 < self.cfg.physical_floor),
                 "void_shortfall": self.cfg.time_blocks - len(self.actions) < self.cfg.reserve_blocks}
        return dict(week=self.week, cash=self.cash, knowledge=learning["depth_mean"], accuracy=learning["accuracy"],
                    attention=self.attention, physical=self.physical, social=self.social,
                    free_time=self.cfg.time_blocks - len(self.actions), job=self.job,
                    **flags, viable=not any(flags.values()), enjoyment=self.enjoyment,
                    cumulative_income=self.cumulative_income, cumulative_ai_cost=self.cumulative_ai_cost,
                    cumulative_messages=self.learner.messages, actions=list(self.actions),
                    rejected=list(self.rejected), ai_used=self.ai_used, teacher_used=self.teacher_used,
                    ledger=dict(self.week_ledger), job_events=list(self.job_events),
                    pending_jobs=len(self.pending_jobs))

    def run(self, policy, weeks):
        if type(weeks) is not int or weeks < 0:
            raise ValueError("weeks must be a nonnegative integer")
        return [self.step(policy) for _ in range(weeks)]
