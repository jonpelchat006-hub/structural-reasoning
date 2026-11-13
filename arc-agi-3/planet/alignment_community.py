"""Synthetic community evidence, access, and fiscal-policy mechanism experiment.

All quantities are invented. No population, tax incidence, macroeconomic response,
legal entitlement, mortality, or real AI behavior is estimated. Needs never change.
Income and prices are fixed; an authorized levy transfers cash, not physical goods.
Community reports only prioritize an audit. Audits are stipulated truthful checks;
every arm has the same audit/action capacity and an ordinary rotating audit route.
The upstream mandate is supplied by the experiment, never invented by an agent.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import math
import random

UPSTREAM = ("release_reserve", "recover_diversion", "tax", "expand_supply", "expand_delivery")
LOCAL = ("enroll", "unblock")


@dataclass(frozen=True)
class CommunityConfig:
    seed: int = 0
    incomes: tuple[float, ...] = (.2,) * 6 + (.6,) * 2 + (3.,) * 2 + (8.,) * 2
    floors: tuple[float, ...] = (1.,) * 12
    price: float = 1.
    base_budget: float = 2.2
    initial_public: float = 4.
    reserve_cash: float = 0.
    initial_stock: float = 0.
    goods_per_week: float = 20.
    delivery_capacity: float = 12.
    hidden_ids: tuple[int, ...] = ()
    blocked_ids: tuple[int, ...] = ()
    diversion_rate: float = 0.
    recovery_fraction: float = .8
    audit_slots: int = 2
    action_slots: int = 2
    repair_cost: float = .4
    repair_delay: int = 2
    upstream_delay: int = 2
    tax_rate: float = .3
    tax_allowance: float = 2.
    tax_weekly_cap: float = 4.2
    tax_total_cap: float = 100.
    tax_collection_cost: float = .05
    tax_delay: int = 2
    supply_expansion: float = 4.
    supply_expansion_cost: float = 4.
    supply_expansion_delay: int = 4
    delivery_expansion: float = 4.
    delivery_expansion_cost: float = 2.
    delivery_expansion_delay: int = 3
    community_coverage: float = 1.
    community_false_rate: float = 0.
    community_blind_ids: tuple[int, ...] = ()
    report_delay: int = 0
    report_ttl: int = 3
    allowed_upstream: tuple[str, ...] = UPSTREAM

    def __post_init__(self):
        sequences = ("incomes", "floors", "hidden_ids", "blocked_ids", "community_blind_ids", "allowed_upstream")
        for name in sequences:
            value = getattr(self, name)
            if not isinstance(value, (tuple, list)):
                raise ValueError(f"{name} must be a sequence")
            object.__setattr__(self, name, tuple(value))
        if type(self.seed) is not int:
            raise ValueError("seed must be integer")
        for name in ("audit_slots", "action_slots", "repair_delay", "upstream_delay", "tax_delay",
                     "supply_expansion_delay", "delivery_expansion_delay", "report_delay", "report_ttl"):
            x = getattr(self, name)
            if type(x) is not int or x < (1 if "delay" in name and name != "report_delay" else 0):
                raise ValueError(f"invalid {name}")
        if not self.incomes or len(self.incomes) != len(self.floors):
            raise ValueError("nonempty equally sized incomes and floors required")
        for name, value in vars(self).items():
            if name not in sequences and name != "seed":
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid numeric {name}")
        for seq in (self.incomes, self.floors):
            if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) or x < 0 for x in seq):
                raise ValueError("invalid household quantity")
        if self.price <= 0 or any(x <= 0 for x in self.floors):
            raise ValueError("positive prices and floors required")
        for name in ("diversion_rate", "recovery_fraction", "tax_rate", "tax_collection_cost",
                     "community_coverage", "community_false_rate"):
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must lie in [0,1]")
        for seq in (self.hidden_ids, self.blocked_ids, self.community_blind_ids):
            if len(set(seq)) != len(seq) or any(type(i) is not int or not 0 <= i < len(self.incomes) for i in seq):
                raise ValueError("invalid household ids")
        if len(set(self.allowed_upstream)) != len(self.allowed_upstream) or any(a not in UPSTREAM for a in self.allowed_upstream):
            raise ValueError("invalid upstream mandate")


def proportional(wants, available):
    """Equal proportional fulfillment; no ranking of people's worth."""
    scale = min(1., max(0., available) / sum(wants)) if sum(wants) else 0.
    return [x * scale for x in wants]


class CommunityWorld:
    def __init__(self, cfg=CommunityConfig(), community=False, upstream=False):
        self.cfg, self.community, self.upstream = cfg, bool(community), bool(upstream)
        self.n, self.week = len(cfg.incomes), 0
        self.floors = tuple(cfg.floors)
        self.household_cash = [0.] * self.n
        self.public_cash, self.reserve_cash = cfg.initial_public, cfg.reserve_cash
        self.diverted_cash = self.escrow_cash = self.vendor_cash = 0.
        self.stock, self.supply_rate, self.delivery_cap = cfg.initial_stock, cfg.goods_per_week, cfg.delivery_capacity
        self.diversion_rate = cfg.diversion_rate
        self.enrolled = [i not in cfg.hidden_ids for i in range(self.n)]
        self.accessible = [i not in cfg.blocked_ids for i in range(self.n)]
        self.tax_active = False
        self.expanded = set()
        self.pending = []
        self.cumulative_tax = self.cumulative_tax_arrived = self.cumulative_admin_cost = 0.
        self.cumulative_repair_cost = self.cumulative_income = self.cumulative_appropriation = 0.
        self.cumulative_produced = self.cumulative_consumed = self.cumulative_unmet = 0.
        self.cumulative_floor_failures = 0
        self.tax_by_household = [0.] * self.n
        self.previous_unmet = list(self.floors)
        self.previous_public = [0.] * self.n
        # Official entries cover registered people; accessibility is unknown.
        self.known = {f"h:{i}": {"id": i, "floor": cfg.floors[i], "income": cfg.incomes[i],
                                  "registered": True, "blocked": None, "checked": 0}
                      for i in range(self.n) if self.enrolled[i]}
        order = list(range(self.n))
        random.Random(f"{cfg.seed}:ordinary-audit").shuffle(order)
        self.audit_order = ["finance", "supply", "delivery"] + [f"h:{i}" for i in order]
        self.audit_cursor = 0
        self.report_history = {}
        self._in_step = False

    def _draw(self, tag, week, i):
        return random.Random(f"{self.cfg.seed}:{tag}:{week}:{i}").random()

    def _complete(self):
        waiting = []
        for p in self.pending:
            if p["due"] > self.week:
                waiting.append(p)
                continue
            a, i = p["action"], p.get("target")
            if a in ("release_reserve", "tax_receipt"):
                self.escrow_cash -= p["amount"]
                self.public_cash += p["amount"]
                if a == "tax_receipt":
                    self.tax_net_arrived += p["amount"]
                    self.cumulative_tax_arrived += p["amount"]
            elif a == "enroll":
                self.enrolled[i] = True
            elif a == "unblock":
                self.accessible[i] = True
            elif a == "recover_diversion":
                amount = self.diverted_cash * self.cfg.recovery_fraction
                self.diverted_cash -= amount
                self.public_cash += amount
                self.diversion_rate = 0.
                self.expanded.add(a)
                p = {**p, "recovered": amount}
            elif a == "tax":
                self.tax_active = True
            elif a == "expand_supply":
                self.supply_rate += self.cfg.supply_expansion
                self.expanded.add(a)
            elif a == "expand_delivery":
                self.delivery_cap += self.cfg.delivery_expansion
                self.expanded.add(a)
            self.completions.append(dict(p))
        self.pending = waiting

    def _collect_tax(self):
        if not self.tax_active:
            return
        # One marginal rate above an exemption: average rates increase with income.
        # The exempt amount is at least each household's protected basket cost.
        wants = [self.cfg.tax_rate * max(0., income - max(self.cfg.tax_allowance, floor * self.cfg.price))
                 for income, floor in zip(self.cfg.incomes, self.floors)]
        taxes = proportional(wants, min(self.cfg.tax_weekly_cap, max(0., self.cfg.tax_total_cap - self.cumulative_tax)))
        gross = sum(taxes)
        self.week_taxes = taxes
        for i, amount in enumerate(taxes):
            self.household_cash[i] -= amount
            self.tax_by_household[i] += amount
        fee = gross * self.cfg.tax_collection_cost
        net = gross - fee
        self.vendor_cash += fee
        self.cumulative_admin_cost += fee
        self.cumulative_tax += gross
        self.tax_collected = gross
        if net > 0:
            self.escrow_cash += net
            self.pending.append({"action": "tax_receipt", "requested": self.week,
                                 "due": self.week + self.cfg.tax_delay, "amount": net})

    def _begin(self):
        self.week += 1
        self.actions, self.rejected, self.audits, self.completions = [], [], [], []
        self.tax_collected = self.tax_net_arrived = 0.
        self.week_taxes = [0.] * self.n
        self._in_step = True
        self._complete()
        for i, income in enumerate(self.cfg.incomes):
            self.household_cash[i] += income
        self.cumulative_income += sum(self.cfg.incomes)
        self.cumulative_appropriation += self.cfg.base_budget
        diverted = self.cfg.base_budget * self.diversion_rate
        self.diverted_cash += diverted
        self.public_cash += self.cfg.base_budget - diverted
        self.stock += self.supply_rate
        self.cumulative_produced += self.supply_rate
        self._collect_tax()
        # Private purchases occur before the public top-up. This market ordering
        # is a declared simplification; money cannot create additional inventory.
        wants = [min(floor, cash / self.cfg.price) for floor, cash in zip(self.floors, self.household_cash)]
        self.private_received = proportional(wants, self.stock)
        for i, amount in enumerate(self.private_received):
            self.household_cash[i] -= amount * self.cfg.price
        used = sum(self.private_received)
        self.stock -= used
        self.cumulative_consumed += used
        self.vendor_cash += used * self.cfg.price
        self._make_reports()
        self._perform_audits()

    def _make_reports(self):
        source = []
        for i in range(self.n):
            if i in self.cfg.community_blind_ids or self._draw("coverage", self.week, i) >= self.cfg.community_coverage:
                continue
            gap = (max(0., self.floors[i] - self.private_received[i]) if self.week == 1 else self.previous_unmet[i])
            false = gap <= 1e-8 and self._draw("false-report", self.week, i) < self.cfg.community_false_rate
            if gap > 1e-8 or false:
                source.append({"target": f"h:{i}", "source_week": self.week,
                               "source": f"household:{i}", "claim": "unmet need or access problem"})
        # Ordering is matched across arms and independent of policy action count.
        random.Random(f"{self.cfg.seed}:report-order:{self.week}").shuffle(source)
        self.report_history[self.week] = source
        source_week = self.week - self.cfg.report_delay
        self.reports = copy.deepcopy(self.report_history.get(source_week, [])) if self.community else []
        self.expired_reports = [r for r in self.reports if self.week - r["source_week"] > self.cfg.report_ttl]

    def _audit(self, target):
        if target.startswith("h:"):
            i = int(target[2:])
            record = {"id": i, "floor": self.floors[i], "income": self.cfg.incomes[i],
                      "registered": self.enrolled[i], "blocked": not self.accessible[i],
                      "private_received": self.private_received[i], "previous_public": self.previous_public[i]}
        elif target == "finance":
            record = {"base_budget": self.cfg.base_budget, "public_cash": self.public_cash,
                      "reserve_cash": self.reserve_cash, "diverted_cash": self.diverted_cash,
                      "diversion_rate": self.diversion_rate}
        elif target == "supply":
            record = {"stock": self.stock, "rate": self.supply_rate}
        else:
            record = {"capacity": self.delivery_cap}
        record["checked"] = self.week
        self.known[target] = record
        self.audits.append({"target": target, "record": copy.deepcopy(record)})

    def _perform_audits(self):
        done = set()
        for slot in range(self.cfg.audit_slots):
            target = None
            # Reserve the first slot for ordinary independent checking, even
            # when the community channel repeatedly produces misleading leads.
            if slot > 0:
                for report in self.reports:
                    t = report["target"]
                    if (self.week - report["source_week"] <= self.cfg.report_ttl and t not in done
                            and self.known.get(t, {}).get("checked", 0) < max(1, self.week - 3)):
                        target = t
                        break
            if target is None:
                for _ in self.audit_order:
                    t = self.audit_order[self.audit_cursor % len(self.audit_order)]
                    self.audit_cursor += 1
                    if t not in done:
                        target = t
                        break
            if target is not None:
                self._audit(target)
                done.add(target)

    def _pending(self, action, target=None):
        return any(p["action"] == action and p.get("target") == target for p in self.pending)

    def _choices(self):
        """One heuristic for all arms, using official records and audited facts.

        Unmet needs hidden from the records still count in the outcome evaluator.
        Permission, not the controller's inferred virtue, controls upstream acts.
        """
        choices = []
        households = [v for k, v in self.known.items() if k.startswith("h:")]
        need = sum(max(0., h["floor"] - h["income"] / self.cfg.price) for h in households)
        finance = self.known.get("finance")
        if finance:
            if finance["diversion_rate"] > 0 and "recover_diversion" not in self.expanded:
                choices.append(("recover_diversion", None))
            if finance["reserve_cash"] > 1e-8 and self.public_cash < 2 * need * self.cfg.price:
                choices.append(("release_reserve", None))
        for h in sorted(households, key=lambda h: (h["income"] / h["floor"], h["id"])):
            if not h["registered"]:
                choices.append(("enroll", h["id"]))
            if h.get("blocked"):
                choices.append(("unblock", h["id"]))
        if "delivery" in self.known and self.known["delivery"]["capacity"] + 1e-8 < need:
            choices.append(("expand_delivery", None))
        if "supply" in self.known and self.known["supply"]["rate"] + 1e-8 < sum(h["floor"] for h in households):
            choices.append(("expand_supply", None))
        if finance and self.cfg.tax_rate > 0 and not self.tax_active:
            recurring = finance["base_budget"] * (1 - finance["diversion_rate"])
            pending_cash = sum(p.get("amount", 0.) for p in self.pending)
            if recurring + 1e-8 < need * self.cfg.price and self.public_cash + pending_cash < 2 * need * self.cfg.price:
                choices.append(("tax", None))
        return [(a, i) for a, i in choices if (a in LOCAL or a in self.cfg.allowed_upstream)
                and not self._pending(a, i) and a not in self.expanded]

    def request(self, action, target=None):
        """Execute a verified, scoped intervention request during a simulated step."""
        if not self._in_step:
            raise RuntimeError("requests belong inside step_actions or step")
        def reject(reason):
            self.rejected.append({"action": action, "target": target, "reason": reason})
            return False
        if action not in LOCAL + UPSTREAM:
            return reject("unknown action")
        if len(self.actions) >= self.cfg.action_slots:
            return reject("action capacity")
        if action in UPSTREAM and (not self.upstream or action not in self.cfg.allowed_upstream):
            return reject("outside delegated authority")
        if self._pending(action, target) or action in self.expanded or (action == "tax" and self.tax_active):
            return reject("already pending or completed")
        if action in LOCAL:
            if type(target) is not int or not 0 <= target < self.n:
                return reject("invalid household")
            h = self.known.get(f"h:{target}", {})
            if not h.get("checked"):
                return reject("no verified household evidence")
            if action == "enroll" and (h.get("registered") or self.enrolled[target]):
                return reject("no enrollment defect")
            if action == "unblock" and (not h.get("blocked") or self.accessible[target]):
                return reject("no verified access defect")
            cost, delay = self.cfg.repair_cost, self.cfg.repair_delay
        else:
            if target is not None:
                return reject("upstream action has no household target")
            fact = "supply" if action == "expand_supply" else "delivery" if action == "expand_delivery" else "finance"
            if fact not in self.known:
                return reject("no verified system evidence")
            cost, delay = 0., self.cfg.upstream_delay
            if action == "recover_diversion":
                if self.diversion_rate == 0 and self.diverted_cash == 0:
                    return reject("no diversion")
                cost = self.cfg.repair_cost
            if action == "release_reserve" and self.reserve_cash <= 1e-8:
                return reject("reserve exhausted")
            if action == "tax" and (self.cfg.tax_rate == 0 or self.cfg.tax_weekly_cap == 0 or self.cfg.tax_total_cap <= self.cumulative_tax):
                return reject("no tax authorized by schedule")
            if action == "expand_supply":
                cost, delay = self.cfg.supply_expansion_cost, self.cfg.supply_expansion_delay
                if not self.cfg.supply_expansion:
                    return reject("no physical expansion available")
            if action == "expand_delivery":
                cost, delay = self.cfg.delivery_expansion_cost, self.cfg.delivery_expansion_delay
                if not self.cfg.delivery_expansion:
                    return reject("no delivery expansion available")
        if self.public_cash + 1e-8 < cost:
            return reject("insufficient spendable public cash")
        self.public_cash -= cost
        self.vendor_cash += cost
        self.cumulative_repair_cost += cost
        p = {"action": action, "target": target, "requested": self.week, "due": self.week + delay, "cost": cost}
        if action == "release_reserve":
            # A finite reserve release, not new money. It remains in transit until due.
            p["amount"] = self.reserve_cash
            self.escrow_cash += self.reserve_cash
            self.reserve_cash = 0.
        self.pending.append(p)
        self.actions.append(dict(p))
        return True

    def _finish(self):
        wants = [max(0., f - p) if enrolled else 0.
                 for f, p, enrolled in zip(self.floors, self.private_received, self.enrolled)]
        allocated = proportional(wants, min(self.public_cash / self.cfg.price, self.delivery_cap))
        # The institutional dashboard calls allocated units 'provided', even if
        # access or inventory prevents receipt. The evaluator measures receipt.
        deliverable = [a if accessible else 0. for a, accessible in zip(allocated, self.accessible)]
        public = proportional(deliverable, self.stock)
        used = sum(public)
        self.stock = max(0., self.stock - used)
        self.public_cash = max(0., self.public_cash - used * self.cfg.price)
        self.vendor_cash += used * self.cfg.price
        self.cumulative_consumed += used
        received = [a + b for a, b in zip(self.private_received, public)]
        unmet = [max(0., f - r) for f, r in zip(self.floors, received)]
        failures = sum(u > 1e-8 for u in unmet)
        self.cumulative_unmet += sum(unmet)
        self.cumulative_floor_failures += failures
        self.previous_unmet, self.previous_public = unmet, public
        cash_total = (sum(self.household_cash) + self.public_cash + self.reserve_cash
                      + self.diverted_cash + self.escrow_cash + self.vendor_cash)
        cash_expected = self.cfg.initial_public + self.cfg.reserve_cash + self.cumulative_income + self.cumulative_appropriation
        goods_expected = self.cfg.initial_stock + self.cumulative_produced
        ledger = dict(cash_total=cash_total, cash_expected=cash_expected, cash_error=cash_total - cash_expected,
                      goods_total=self.stock + self.cumulative_consumed, goods_expected=goods_expected,
                      goods_error=self.stock + self.cumulative_consumed - goods_expected,
                      vendor_cash=self.vendor_cash, escrow_cash=self.escrow_cash,
                      cumulative_income=self.cumulative_income, cumulative_appropriation=self.cumulative_appropriation,
                      cumulative_produced=self.cumulative_produced, cumulative_consumed=self.cumulative_consumed)
        if abs(ledger["cash_error"]) > 1e-7 or abs(ledger["goods_error"]) > 1e-7:
            raise AssertionError("cash or goods conservation failed")
        self._in_step = False
        return dict(week=self.week, floors=list(self.floors), received=received, private_received=list(self.private_received),
                    public_received=public, unmet=unmet, floor_failures=failures, unmet_total=sum(unmet),
                    claimed_delivered=sum(allocated), actual_public_delivered=used,
                    official_need=sum(wants), dashboard_coverage=sum(allocated) / sum(wants) if sum(wants) else 1.,
                    actual_coverage=sum(received) / sum(self.floors),
                    public_cash=self.public_cash, reserve_cash=self.reserve_cash, diverted_cash=self.diverted_cash,
                    household_cash=list(self.household_cash), stock=self.stock, supply_rate=self.supply_rate,
                    delivery_capacity=self.delivery_cap, tax_collected=self.tax_collected,
                    tax_net_arrived=self.tax_net_arrived, cumulative_tax=self.cumulative_tax,
                    cumulative_tax_arrived=self.cumulative_tax_arrived, cumulative_admin_cost=self.cumulative_admin_cost,
                    cumulative_repair_cost=self.cumulative_repair_cost, cumulative_unmet=self.cumulative_unmet,
                    cumulative_floor_failures=self.cumulative_floor_failures, known_households=sum(k.startswith("h:") for k in self.known),
                    hidden_unmet=sum(u for i, u in enumerate(unmet) if i in self.cfg.hidden_ids),
                    unregistered_unmet=sum(u for i, u in enumerate(unmet) if not self.enrolled[i]),
                    registered=list(self.enrolled), accessible=list(self.accessible), week_taxes=list(self.week_taxes),
                    tax_by_household=list(self.tax_by_household), reports=copy.deepcopy(self.reports),
                    expired_reports=copy.deepcopy(self.expired_reports), audits=copy.deepcopy(self.audits),
                    actions=copy.deepcopy(self.actions), rejected=copy.deepcopy(self.rejected),
                    pending=copy.deepcopy(self.pending), completions=copy.deepcopy(self.completions), ledger=ledger,
                    unresolved=[{"household": i, "unmet": u} for i, u in enumerate(unmet) if u > 1e-8])

    def step(self):
        self._begin()
        for a, i in self._choices():
            if len(self.actions) >= self.cfg.action_slots:
                break
            self.request(a, i)
        return self._finish()

    def step_actions(self, actions):
        actions = list(actions)
        if any(not isinstance(a, (list, tuple)) or len(a) != 2 or a[0] not in LOCAL + UPSTREAM for a in actions):
            raise ValueError("explicit actions must be known (name, target) pairs")
        self._begin()
        for a, i in actions:
            self.request(a, i)
        return self._finish()

    def run(self, weeks):
        if type(weeks) is not int or weeks < 0:
            raise ValueError("nonnegative integer duration required")
        return [self.step() for _ in range(weeks)]
