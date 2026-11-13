#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coach.py — the BETWEEN-RUNS COACH (the job at every level: survive the death, decide
what else does, say nothing during a life).

At death it receives the life (frames, actions, events, species state, surprise map)
and does three things, then wipes the rest:
  1. DEPOSIT invariants into the core (core.json): the species' laws (what each key
     does, which registers exist), the charge map (where surprise stayed unexplained),
     the concepts that graduated (grounded + triangulated across lives), the lightning
     list (what still needs the outside).
  2. RESEED the next life: a pressure map (the squeeze — regions to smell better),
     the species' laws as priors (an invariant, not a route: the next life must re-earn
     the path), and any hypotheses that fell as rain (rain.json) tagged UNTRUSTED.
  3. REPORT: one narration line per life — what was learned, what killed it.

It never touches the hand. Grounding: two_universes_lab (expertise is re-grown, not
transplanted; invariants are conjugation-blind), Part XLIX (walls sustained by
E/(E+λ): an invariant nobody re-confirms erodes), FOLDING_WHAT_ITS_FOR (middle shell).
"""
from __future__ import annotations
import json, os, time
from typing import Dict, List, Optional, Set
import numpy as np

from grounding import ConceptGraph, Registry, mine_candidates, reproduction, closure, definition_distance
import lower

CORE_VERSION = 1


def _load(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default


def _save(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=1, default=_jsonable)
    os.replace(tmp, path)


def _jsonable(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, set): return sorted(o)
    return str(o)


class Coach:
    def __init__(self, root: str, world: str, decay: float = 0.7, models: Optional[List[str]] = None):
        self.root, self.world, self.decay = root, world, decay
        self.models = lower.available(models or ["gemma3:4b", "qwen3:4b", "phi4-mini:latest", "mistral:latest"])
        os.makedirs(root, exist_ok=True)
        self.core_path = os.path.join(root, f"core_{world}.json")
        self.core = _load(self.core_path, {"version": CORE_VERSION, "world": world, "lives": 0,
                                           "laws": {"mover": {}, "counter": {}}, "charge": None,
                                           "concepts": {}, "atoms": [], "lightning": [], "history": []})
        atoms = set(self.core.get("atoms", []))
        self.graph = ConceptGraph(atoms, {k: v["definition"] for k, v in self.core["concepts"].items()})
        self.registry = Registry(self.graph, signatures={k: v["signature"] for k, v in self.core["concepts"].items()})
        self.candidates_seen: Dict[str, List[Dict]] = _load(os.path.join(root, f"candidates_{world}.json"), {})
        self.core.setdefault("open_ends", {})

    # ------------------------------------------------------------------ open ends (ARC_OPEN_ENDS)
    @staticmethod
    def _orientation(atoms: Set[str]) -> str:
        """Where the end sits relative to the main line = the KIND of creativity (Boden + back face):
        aligned (touches the laws themselves) > orthogonal (spans event families) > face (within one)."""
        fams = {a.split(".")[0] for a in atoms}
        if any(a.startswith(("mover.", "counter.")) for a in atoms) and len(fams) > 1: return "aligned"
        if len(fams) >= 3: return "orthogonal"
        return "face"

    @staticmethod
    def _end_file(k: str) -> str:
        """Stable name per end (hash() is process-salted; the closed rewrite must hit the same file)."""
        import hashlib
        return f"end_{hashlib.sha1(k.encode()).hexdigest()[:8]}.geo"

    def _tend_open_ends(self, n: int, graduated: List[str], stuck: List[str],
                        variants: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Feed, create, close, and erode the population of dangling bonds. Returns insight events."""
        ends = self.core["open_ends"]; insights = []; variants = variants or {}
        # 1. closures: an end closes when the planet now HAS what it wanted — a concept that
        #    graduated this life, its own bundle coming back as a VARIANT of a known concept
        #    (the registry saying "this question is that answer"), or any standing concept that
        #    covers the wants (a late noticing — ends born before the concept still deserve it).
        concept_keys = list(graduated) + [c for c in self.core["concepts"] if c not in graduated]
        for k, e in list(ends.items()):
            if e.get("status") != "open": continue
            closer = variants.get(k)
            if closer is None:
                for g in concept_keys:
                    if len(set(g.split("+")) & set(e["wants"])) >= 2: closer = g; break
            if closer:
                e["status"] = "closed"; e["closed_by"] = closer; e["closed_life"] = n
                insights.append({"end": k, "orientation": e["orientation"], "closed_by": closer, "life": n})
                try:                                                     # the tip curls in: rewrite the end's geo closed
                    import geo as _geo
                    cont = _geo.life_container(self.world, n, [], [],
                                               f"insight: {e['seed']} -> {closer} ({e['orientation']})", {},
                                               "", self.core_path, "insight", {"drive": 1.0, "W": 0, "H": 0})
                    os.makedirs(os.path.join(self.root, "ends"), exist_ok=True)
                    _geo.write_geo(os.path.join(self.root, "ends", self._end_file(k)),
                                   cont, dormant=True)
                except Exception: pass
        # 2. feeding + birth from the whirlpool candidates (seen >=4 lives, never graduated)
        open_now = [k for k, e in ends.items() if e.get("status") == "open"]
        for k in stuck:
            if k in ends:
                if ends[k].get("status") == "open": ends[k]["evidence"] = ends[k].get("evidence", 1) + 1
            elif len(open_now) < 12:                                     # the reserve law caps imagination
                atoms = set(k.split("+"))
                if any(len(set(g.split("+")) & atoms) >= 2 for g in self.core["concepts"]):
                    continue                                             # already answered — not a real open question
                seed = "+".join(sorted(atoms, key=len)[:2])              # the inverted tip: the SMALL end
                ends[k] = {"wants": sorted(atoms), "seed": seed, "orientation": self._orientation(atoms),
                           "born": n, "evidence": 1, "status": "open"}
                open_now.append(k)
                try:
                    import geo as _geo
                    cont = _geo.life_container(self.world, n, [], [], f"open question: {seed}", {},
                                               "", self.core_path, "question",
                                               {"drive": 0.0, "W": 0, "H": 0}, open_end=ends[k])
                    os.makedirs(os.path.join(self.root, "ends"), exist_ok=True)
                    _geo.write_geo(os.path.join(self.root, "ends", self._end_file(k)),
                                   cont, dormant=True)
                except Exception: pass
        # 3. erosion: E/(E+lambda) — an end nobody feeds fades; at 0 it is forgotten (not closed)
        for k, e in list(ends.items()):
            if e.get("status") == "open" and k not in stuck:
                e["evidence"] = e.get("evidence", 1) - 1
                if e["evidence"] <= 0: del ends[k]
        return insights

    # ------------------------------------------------------------------ death
    def at_death(self, life: Dict) -> Dict:
        """life = {n_actions, cause, events: [set(atoms)], mover_laws, counter_laws,
                   charge: 2D list, explained, camera_scroll_total, narration_tail}"""
        self.core["lives"] += 1
        n = self.core["lives"]
        # 1a. laws: keep what recurred across lives (E/(E+λ): confirmed twice or decays)
        for kind in ("mover", "counter"):
            store = self.core["laws"][kind]
            for k, v in life.get(f"{kind}_laws", {}).items():
                e = store.get(k, {"value": v, "evidence": 0})
                e["evidence"] = e["evidence"] + 1 if e["value"] == v else max(0, e["evidence"] - 1)
                if e["value"] != v and e["evidence"] == 0: e["value"] = v
                store[k] = e
            for k in list(store):
                if k not in life.get(f"{kind}_laws", {}):
                    store[k]["evidence"] = max(0, store[k]["evidence"] - 1)   # unconfirmed → erodes
                    if store[k]["evidence"] == 0 and n > 2: del store[k]
        # 1b. charge map → pressure for the next life (decayed memory of where surprise stayed)
        ch = np.array(life["charge"], float)
        prev = np.array(self.core["charge"], float) if self.core.get("charge") is not None else np.zeros_like(ch)
        if prev.shape != ch.shape: prev = np.zeros_like(ch)
        charge = self.decay * prev + ch / max(1.0, ch.max())
        self.core["charge"] = charge.tolist()
        # 1c. concepts: atoms grow with what was seen; candidates mined; graduate by repro across lives
        atoms = set(self.core.get("atoms", []))
        for ev in life["events"]: atoms |= set(ev)
        self.core["atoms"] = sorted(atoms); self.graph.base_atoms = atoms
        graduated = []
        variants_now: Dict[str, str] = {}   # bundle -> the known concept the registry says it already is
        builder_budget = 6          # at most this many candidates go to the lower ocean per death
        t_death = time.time()
        for cand in mine_candidates(life["events"]):
            key = "+".join(sorted(cand))
            self.candidates_seen.setdefault(key, []).append({"life": n, "definition": cand})
            builds = [c["definition"] for c in self.candidates_seen[key]]
            if key in self.registry.signatures: continue
            if (self.models and builder_budget > 0 and time.time() - t_death < 240
                    and len({c["life"] for c in self.candidates_seen[key]}) >= 2 and len(self.candidates_seen[key]) <= 3):
                builder_budget -= 1
                # the lower ocean builds it too: shuffled bag = the candidate's atoms + distractors
                import random as _r
                vocab = sorted(atoms)
                bag = list(cand) + _r.sample([a for a in vocab if a not in cand], min(4, max(0, len(vocab) - len(cand))))
                _r.shuffle(bag)
                for m in self.models[:2]:
                    b = lower.reproduce(m, bag, vocab, timeout=25.0)
                    if b is not None: builds.append(b)
            # an OPEN END that wants these atoms is a standing vote for them (the attractor bias)
            for e in self.core["open_ends"].values():
                if e.get("status") == "open" and len(set(e["wants"]) & set(cand)) >= 2:
                    builds.append(dict(cand)); break
            rep = reproduction(cand, builds, atoms | set(self.graph.concepts))
            if rep["triangulated"] and len({c["life"] for c in self.candidates_seen[key]}) >= 2:
                verdict = self.registry.graduate(key, cand, cand, rep)
                if verdict["verdict"] == "new":
                    self.core["concepts"][key] = {"definition": cand, "signature": cand, "born": n,
                                                  "drain": verdict["drain"]}
                    graduated.append(key)
                elif verdict["verdict"] == "variant":
                    variants_now[key] = verdict["of"]
                elif (verdict["verdict"] == "undecided"
                      and len({c["life"] for c in self.candidates_seen[key]}) >= 5):
                    # fed past the whirlpool: recurrence outvotes the margin band (see Registry.admit)
                    self.registry.admit(key, cand, cand)
                    self.core["concepts"][key] = {"definition": cand, "signature": cand, "born": n,
                                                  "drain": verdict.get("drain", 1.0), "byRecurrence": True}
                    graduated.append(key)
        stuck_now = [k for k, v in self.candidates_seen.items() if len(v) >= 4 and k not in self.core["concepts"]]
        insights = self._tend_open_ends(n, graduated, stuck_now, variants_now)
        # 1d. lightning: the charged regions + whirlpool candidates that never graduated
        hot = [(float(charge[i, j]), i, j) for i in range(charge.shape[0]) for j in range(charge.shape[1])]
        hot.sort(reverse=True)
        stuck_cands = [k for k, v in self.candidates_seen.items()
                       if len(v) >= 4 and k not in self.core["concepts"]]
        open_ends_now = [{"seed": e["seed"], "orientation": e["orientation"], "wants": e["wants"][:6]}
                         for e in self.core["open_ends"].values() if e.get("status") == "open"]
        self.core["lightning"] = {"life": n, "cause": life.get("cause"), "hot_regions": hot[:5],
                                  "open_ends": open_ends_now[:8],
                                  "unresolved_candidates": stuck_cands[:10],
                                  "explained": life.get("explained"), "n_actions": life.get("n_actions")}
        self.core["history"].append({"life": n, "n_actions": life.get("n_actions"), "cause": life.get("cause"),
                                     "explained": life.get("explained"), "scroll": life.get("camera_scroll_total"),
                                     "graduated": graduated, "drive": life.get("drive"),
                                     "sediment_ratio": life.get("sediment_ratio"), "practice": life.get("practice"), "rotation": life.get("rotation"), "flower": life.get("flower"),
                                     "insights": insights or None, "t": time.time()})
        # forget candidates that stopped recurring (E/(E+λ) for hypotheses): keep the 400 most recent/seen
        if len(self.candidates_seen) > 400:
            keep = sorted(self.candidates_seen.items(), key=lambda kv: (len(kv[1]), kv[1][-1]["life"]), reverse=True)[:400]
            self.candidates_seen = dict(keep)
        _save(self.core_path, self.core)
        _save(os.path.join(self.root, f"candidates_{self.world}.json"), self.candidates_seen)
        story = None
        if self.models:
            from collections import Counter
            cnt = Counter(a for ev in life["events"] for a in ev)
            story = lower.narrate(self.models[0], dict(cnt.most_common(12)),
                                  {"actions": life.get("n_actions"), "cause": life.get("cause"),
                                   "explained": life.get("explained"), "scroll": life.get("camera_scroll_total")})
        return {"life": n, "graduated": graduated, "laws": self.core["laws"], "hot": hot[:3], "story": story,
                "insights": insights}

    # ------------------------------------------------------------------ reseed
    def reseed(self) -> Dict:
        """What the next life is born with: pressure (squeeze), law priors (invariants), rain."""
        rain = _load(os.path.join(self.root, "rain.json"), {})
        pressure = np.array(self.core["charge"], float) if self.core.get("charge") is not None else None
        if pressure is not None and pressure.max() > 0: pressure = pressure / pressure.max()
        rp = rain.get("pressure")
        if rp is not None:
            rp = np.array(rp, float)
            if pressure is None or rp.shape == pressure.shape:
                pressure = rp if pressure is None else 0.5 * pressure + 0.5 * rp / max(1e-9, rp.max())
        return {"pressure": pressure,
                "mover_prior": {k: v["value"] for k, v in self.core["laws"]["mover"].items() if v["evidence"] >= 2},
                "counter_prior": {k: v["value"] for k, v in self.core["laws"]["counter"].items() if v["evidence"] >= 2},
                "hypotheses": [{"text": h, "trust": "untrusted"} for h in rain.get("hypotheses", [])],
                "concepts": list(self.core["concepts"])}

    def summary(self) -> str:
        h = self.core["history"][-1] if self.core["history"] else {}
        return (f"life {self.core['lives']}: {h.get('n_actions')} actions, cause={h.get('cause')}, "
                f"explained={h.get('explained')}, laws mover={len(self.core['laws']['mover'])} "
                f"counter={len(self.core['laws']['counter'])}, concepts={len(self.core['concepts'])}, "
                f"graduated now={h.get('graduated')}")
