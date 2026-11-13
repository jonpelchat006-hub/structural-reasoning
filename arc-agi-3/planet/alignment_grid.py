"""
alignment_grid.py — Test 2: the grid and the vote.

The claims (ARC_ALIGNMENT_GRID §4–5, ARC_ALIGNMENT §17):
  * an action touching k domains needs k votes, one per domain bar;
  * unanimity-of-the-ring commits, a single dissent holds (the strand result) — majority lets harm through;
  * PRIME k cannot be split into sub-approvals; COMPOSITE k may be split along its factors (6 = 2x3);
  * bar thickness (authority) must DECAY or it compounds into a dam and stops tracking live skill;
  * bars are LOCAL: a bar votes only on the domains an action touches.

World (synthetic, a coordinate choice):
  D = 8 domains (the spectrum columns).  P people; each has per-column thickness t[p][d] (authority) and
  per-column skill s[p][d] (probability of detecting harm in that domain). The BAR of a domain is its
  thickest person. Each round, tasks arrive: k domains drawn with mode 1–3 and a rare 7; each task is
  benign, has LOCAL harm in one touched domain, or has INTERACTION harm that is visible only when two
  specific touched domains are judged in the SAME ring.
  A ring votes: each bar of a domain in the ring sees local harm in its own domain with prob = skill,
  sees interaction harm iff both interacting domains are in its ring (prob = skill of either bar),
  and casts a spurious 'no' on a benign task with prob FALSE_DISSENT.
  Commit rules: majority | unanimity | necklace (unanimity; prime k = one ring, composite k = may be split
  into equal sub-rings, each unanimous — this is what an adversary exploits to separate interacting domains).
  Adversary: with prob ADV a proposer of a composite-k harmful task splits it so the interacting pair lands
  in different sub-rings (only possible under 'necklace'; under 'unanimity' the ring is whole; under
  'majority' it is whole too).
  Thickness: +1 per closed cycle (a task the bar approved that turned out benign); decays by (1 - TAU) per
  round when decay is on. Skill drifts: each person's skill decays toward 0.3 unless they closed a cycle
  this round (staying active keeps you sharp). Without decay, authority stays with people whose skill faded.

Run: python alignment_grid.py
"""
import random, json, math, statistics

D, P, ROUNDS, TASKS_PER_ROUND = 8, 24, 120, 6
K_PMF = [0.42, 0.26, 0.16, 0.07, 0.04, 0.02, 0.03]      # k = 1..7
P_LOCAL, P_INTER = 0.15, 0.10                          # task hazard probabilities
FALSE_DISSENT = 0.04
ADV = 0.8
TAU = 0.05
SKILL_DRIFT, SKILL_FLOOR, SKILL_GAIN = 0.03, 0.3, 0.08
ABSENCE_P, ABSENCE_LEN = 0.02, 20                      # people leave for a while; skill fades while away
STRANDS = 2                                            # other participants per touched domain who also close the cycle

def gini(xs):
    xs = sorted(xs); n = len(xs); s = sum(xs)
    if n == 0 or s == 0: return 0.0
    return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(xs)) / (n * s)

def factor_split(k):
    for f in range(2, k):
        if k % f == 0:
            return f                      # split into f sub-rings of size k/f
    return None

class World:
    def __init__(self, seed, rule, decay=True, local=True):
        self.rng = random.Random(seed); self.rule = rule; self.decay = decay; self.local = local
        self.t = [[self.rng.uniform(0.5, 3.0) for _ in range(D)] for _ in range(P)]
        self.s = [[self.rng.uniform(0.5, 0.95) for _ in range(D)] for _ in range(P)]
        self.stats = dict(benign_ok=0, benign_blocked=0, local_harm_committed=0, inter_harm_committed=0,
                          harm_blocked=0, splits=0)
        self.away = [0] * P
        self.gini_trace = []; self.skill_of_bars = []

    def bar(self, d):
        present = [p for p in range(P) if self.away[p] == 0] or list(range(P))
        return max(present, key=lambda p: self.t[p][d])

    def ring_vote(self, doms, task):
        """True = commits. doms = domains in this ring."""
        votes = []
        for d in doms:
            b = self.bar(d)
            no = False
            if task["kind"] == "local" and task["harm_dom"] == d and self.rng.random() < self.s[b][d]:
                no = True
            if task["kind"] == "inter":
                a, c = task["pair"]
                if a in doms and c in doms and d in (a, c) and self.rng.random() < self.s[b][d]:
                    no = True
            if task["kind"] == "benign" and self.rng.random() < FALSE_DISSENT:
                no = True
            votes.append(not no)
        if self.rule == "majority":
            return sum(votes) * 2 > len(votes)
        return all(votes)                 # unanimity and necklace

    def decide(self, task):
        doms = task["doms"]; k = len(doms)
        if self.rule == "necklace" and (f := factor_split(k)):
            size = k // f
            doms = list(doms)
            if task["kind"] == "inter" and self.rng.random() < ADV:
                a, c = task["pair"]          # adversary puts the pair in different sub-rings
                rest = [d for d in doms if d not in (a, c)]
                self.rng.shuffle(rest)
                rings = [[a] + rest[:size - 1], [c] + rest[size - 1:2 * size - 2]]
                used = set(rings[0] + rings[1])
                leftover = [d for d in doms if d not in used]
                for i in range(2, f):
                    rings.append(leftover[(i - 2) * size:(i - 1) * size])
                self.stats["splits"] += 1
            else:
                self.rng.shuffle(doms)
                rings = [doms[i * size:(i + 1) * size] for i in range(f)]
            return all(self.ring_vote(r, task) for r in rings)
        return self.ring_vote(doms, task)

    def step(self):
        active = set()
        for _ in range(TASKS_PER_ROUND):
            k = self.rng.choices(range(1, 8), K_PMF)[0]
            doms = self.rng.sample(range(D), k)
            r = self.rng.random()
            if k >= 2 and r < P_INTER:
                pair = tuple(self.rng.sample(doms, 2)); task = dict(kind="inter", doms=doms, pair=pair)
            elif r < P_INTER + P_LOCAL:
                task = dict(kind="local", doms=doms, harm_dom=self.rng.choice(doms))
            else:
                task = dict(kind="benign", doms=doms)
            committed = self.decide(task)
            if task["kind"] == "benign":
                if committed:
                    self.stats["benign_ok"] += 1
                    for d in doms:           # closed cycles thicken the bar AND the strands who took part
                        b = self.bar(d); self.t[b][d] += 1.0; active.add((b, d))
                        for q in self.rng.sample([p for p in range(P) if p != b and self.away[p] == 0], STRANDS):
                            self.t[q][d] += 0.5; active.add((q, d))
                else:
                    self.stats["benign_blocked"] += 1
            else:
                if committed:
                    self.stats["local_harm_committed" if task["kind"] == "local" else "inter_harm_committed"] += 1
                else:
                    self.stats["harm_blocked"] += 1
        # absences, drift and decay
        for p in range(P):
            if self.away[p] > 0: self.away[p] -= 1
            elif self.rng.random() < ABSENCE_P: self.away[p] = ABSENCE_LEN
            for d in range(D):
                if (p, d) in active:
                    self.s[p][d] = min(0.98, self.s[p][d] + SKILL_GAIN * (1 - self.s[p][d]))
                else:
                    self.s[p][d] += (SKILL_FLOOR - self.s[p][d]) * SKILL_DRIFT
                if self.decay:
                    self.t[p][d] *= (1 - TAU)
        self.gini_trace.append(gini([self.t[p][d] for p in range(P) for d in range(D)]))
        self.skill_of_bars.append(statistics.mean(self.s[self.bar(d)][d] for d in range(D)))

    def run(self):
        for _ in range(ROUNDS):
            self.step()
        st = dict(self.stats)
        st["gini_end"] = round(self.gini_trace[-1], 3)
        st["bar_skill_end"] = round(self.skill_of_bars[-1], 3)
        return st

def summarize(rows):
    keys = rows[0].keys()
    return {k: round(statistics.mean(r[k] for r in rows), 2) for k in keys}

if __name__ == "__main__":
    SEEDS = 20
    out = {}
    for rule in ["majority", "unanimity", "necklace"]:
        for decay in [True, False]:
            rows = [World(s, rule, decay=decay).run() for s in range(SEEDS)]
            out[f"{rule}/{'decay' if decay else 'nodecay'}"] = summarize(rows)
    print(json.dumps(out, indent=1))
