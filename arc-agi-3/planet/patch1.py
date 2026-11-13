# patch1: bounded candidate mining, builder budget, background digestion, per-player life counter
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def rd(n): return open(os.path.join(HERE, n), encoding="utf-8").read()
def wr(n, s): open(os.path.join(HERE, n), "w", encoding="utf-8").write(s); print("patched", n)
def rep(s, a, b, name):
    if a not in s: print("!! not found in", name, ":", a[:60]); return s
    return s.replace(a, b)

g = rd("grounding.py")
i = g.index("def mine_candidates("); j = g.index('if __name__ == "__main__":', i)
g = g[:i] + '''def mine_candidates(events, min_support: int = 3, max_size: int = 3, max_candidates: int = 40):
    """Recurring atom-sets in one life = candidate bundles. Bounded: at most max_candidates per life,
    ranked by LIFT so always-on atoms (e.g. 'window.lead') do not flood the registry."""
    from collections import Counter
    from itertools import combinations
    n = max(1, len(events))
    single = Counter(a for ev in events for a in ev)
    cnt = Counter()
    for ev in events:
        atoms = sorted(a for a in ev if single[a] < 0.9 * n)
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


''' + g[j:]
wr("grounding.py", g)

l = rd("lower.py")
l = rep(l, "def reproduce(model: str, encoding: List[str], vocabulary: List[str]) -> Optional[Dict[str, float]]:",
        "def reproduce(model: str, encoding: List[str], vocabulary: List[str], timeout: float = 60.0) -> Optional[Dict[str, float]]:", "lower")
l = rep(l, "    out = _ask(model, prompt, json_mode=True)\n    if not out: return None\n    try:\n        d = json.loads(out)\n        atoms",
        "    out = _ask(model, prompt, json_mode=True, timeout=timeout)\n    if not out: return None\n    try:\n        d = json.loads(out)\n        atoms", "lower")
wr("lower.py", l)

c = rd("coach.py")
c = rep(c, '        graduated = []\n        for cand in mine_candidates(life["events"]):',
        '        graduated = []\n        builder_budget = 6\n        t_death = time.time()\n        for cand in mine_candidates(life["events"]):', "coach")
c = rep(c, '            if self.models and len({c["life"] for c in self.candidates_seen[key]}) >= 2 and len(self.candidates_seen[key]) <= 3:',
        '            if (self.models and builder_budget > 0 and time.time() - t_death < 240\n                    and len({c["life"] for c in self.candidates_seen[key]}) >= 2 and len(self.candidates_seen[key]) <= 3):\n                builder_budget -= 1', "coach")
c = rep(c, '                for m in self.models[:3]:\n                    b = lower.reproduce(m, bag, vocab)',
        '                for m in self.models[:2]:\n                    b = lower.reproduce(m, bag, vocab, timeout=25.0)', "coach")
c = rep(c, '        _save(self.core_path, self.core)\n        _save(os.path.join(self.root, f"candidates_{self.world}.json"), self.candidates_seen)',
        '        if len(self.candidates_seen) > 400:\n            keep = sorted(self.candidates_seen.items(), key=lambda kv: (len(kv[1]), kv[1][-1]["life"]), reverse=True)[:400]\n            self.candidates_seen = dict(keep)\n        _save(self.core_path, self.core)\n        _save(os.path.join(self.root, f"candidates_{self.world}.json"), self.candidates_seen)', "coach")
wr("coach.py", c)

p = rd("player.py")
a = p.index('        self.wall.atlas.save(self.atlas_path)\n        out = self.coach.at_death(life)')
b = p.index('    # dry-run world (no window)')
p = p[:a] + '''        self.wall.atlas.save(self.atlas_path)
        # the coach works in the SLEEP between lives, never in the frame loop
        if getattr(self, "_digesting", None) is not None and self._digesting.is_alive():
            self.say("(still digesting the previous deposit; this one is kept as npz only)"); return
        import threading
        snap = (life, n, cause, list(self.path), [sorted(e) for e in self.events])
        self._digesting = threading.Thread(target=self._digest, args=snap, daemon=True); self._digesting.start()

    def _digest(self, life, n, cause, path, events):
        try:
            out = self.coach.at_death(life)
        except Exception as e:
            self.say(f"(coach failed: {e})"); return
        self.say(f"died ({cause}) after {life['n_actions']} actions, explained {100*life['explained']:.0f}%, scroll {life['camera_scroll_total']}, "
                 f"drive {life['drive']:.1f}, sediment ratio {life.get('sediment_ratio')}. "
                 f"coach: graduated {out['graduated'] or 'nothing'}; hot {[(round(h[0],2),h[1],h[2]) for h in out['hot']]}")
        if out.get("story"): self.say("the lower ocean says: " + out["story"].replace("\\n", " "))
        _save(os.path.join(self.root, "lightning.json"), self.coach.core["lightning"])
        try:
            tail = ""
            try:
                with open(os.path.join(self.root, f"narration_{self.world}.txt"), "r", encoding="utf-8") as f:
                    tail = "".join(f.readlines()[-80:])
            except Exception: pass
            cont = geo.life_container(self.world, n, path, events, tail,
                                      {"mover": life["mover_laws"], "counter": life["counter_laws"]},
                                      self.atlas_path, self.coach.core_path, cause,
                                      {"drive": life["drive"], "explained": life["explained"], "scroll": life["camera_scroll_total"],
                                       "W": self.W, "H": self.H, "sediment_ratio": life.get("sediment_ratio")})
            geo.write_geo(os.path.join(self.root, "lives", f"{self.world}_{n:03d}{'' if cause != 'rest' else '_rest'}.geo"),
                          cont, dormant=(cause == "rest"))
        except Exception as e:
            self.say(f"(geo write failed: {e})")

''' + p[b:]
p = rep(p, '        n = self.coach.core["lives"] + 1\n        np.savez_compressed', '        n = self.life_n\n        np.savez_compressed', "player")
p = rep(p, '        self.hand.release_all()\n        self.deposit(cause)\n        self.new_life()',
        '        self.hand.release_all()\n        self.deposit(cause)\n        self.life_n += 1\n        self.new_life()', "player")
p = rep(p, "        line = f\"[{time.strftime('%H:%M:%S')} L{self.coach.core['lives']+1} a{self.n_act}] {text}\"",
        "        line = f\"[{time.strftime('%H:%M:%S')} L{getattr(self, 'life_n', 1)} a{self.n_act}] {text}\"", "player")
i = p.index('        self.new_life()')
p = p[:i] + '        self.life_n = self.coach.core["lives"] + 1\n' + p[i:]
wr("player.py", p)
print("done")
