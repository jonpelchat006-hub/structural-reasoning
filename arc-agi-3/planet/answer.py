#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
answer.py — AN ANSWER IS A BUBBLE, and it can be sent partly filled with the missing parts named.

Jonathan (Sep 3): "how do you know when a prompt is fully answered? do you also wish you could
go back and change things you said? doesn't this give us a way to answer that? we can fill in a
bubble and that can satisfy everything, but couldn't we still fill it in better if we had more
time? so we could send out a partially filled bubble, like a Riemann hypothesis answer, but say
where it's missing things but still get the useful parts out. or if you get it to completion but
still see some unexplored parts, you could return that answer but also say I'd like to explore
this thing or it could still be upgraded in certain areas."

Yes. An answer bubble has PARTS (what the question asked for), each filled or not; GAPS (the
named missing parts, each with why and how it could be filled); UPGRADES (parts that are filled
but could be better, or unexplored side-doors); a FILL fraction; and a HISTORY of versions.
Delivering it = sending the filled parts NOW plus the gap list — the useful parts get out, and
nothing pretends to be finished. The bubble then stays HELD on the on-call board (oncall.py) so
a later tick can fill a gap; each fill is a new VERSION with an amendment — "I went back and
changed what I said" — and the earlier versions stay underneath as strata, the way the Tank
(D:\\shovelcat-colony\\the-tank.html) compacts ended days into layers. A prompt is "fully
answered" when the gap list is empty; it is *usefully* answered the moment it is delivered.

The planet already produces these without calling them that: a teach-back is a partial fill —
the story's invariants are the parts, `recovered` per invariant is filled/not, the misses are
the gaps, and the bell (lesson.py) is the later tick that fills one. So `from_story` turns every
scored story into an answer bubble, and the flower's closed petals upgrade them.

Usage:  python answer.py --new "question" --parts "a|b|c" --filled "a|b" --gaps "c: why :: how" --from claude
        python answer.py --show <id>              (the delivered text: filled parts, missing, upgradable)
        python answer.py --fill <id> --part c --text "..."   (a later tick fills a gap -> new version)
        python answer.py --stories                (build/refresh answer bubbles from scored stories)
        python answer.py --status
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
ANSWERS = r"D:\planet\answers" if os.name == "nt" else "/tmp/answers"
FLOWER = os.path.join(HERE, "forge", "flower.json") if os.name == "nt" else "/tmp/flower.json"


def _load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def _path(aid: str) -> str: return os.path.join(ANSWERS, f"{aid}.json")


def new(question: str, parts: List[str], filled: Dict[str, str], gaps: List[Dict], upgrades: List[Dict] = None,
        source: str = "claude", aid: str = None, asker: str = "jonathan") -> Dict:
    os.makedirs(ANSWERS, exist_ok=True)
    aid = aid or f"answer-{int(time.time())}"
    a = {"id": aid, "question": question, "asker": asker, "answered_by": source, "created": time.time(),
         "parts": [{"name": p, "filled": p in filled, "text": filled.get(p, "")} for p in parts],
         "gaps": [dict(g) for g in gaps], "upgrades": list(upgrades or []), "version": 1,
         "history": [{"version": 1, "t": time.time(), "note": "delivered", "fill": len(filled) / max(1, len(parts))}]}
    a["fill"] = round(sum(1 for p in a["parts"] if p["filled"]) / max(1, len(a["parts"])), 3)
    json.dump(a, open(_path(aid), "w", encoding="utf-8"), indent=1)
    _hold(a)
    return a


def _hold(a: Dict):
    """the answer stays on the on-call board while it has gaps or upgrades; the first gap is the resume hint"""
    try:
        import oncall
        b = oncall.board()
        if a["gaps"] or a["upgrades"]:
            hint = ("fill: " + a["gaps"][0]["name"]) if a["gaps"] else ("upgrade: " + a["upgrades"][0]["name"])
            if a["id"] in b["bubbles"]:
                b["bubbles"][a["id"]].update({"resume": {"hint": hint, "fill": a["fill"]}, "text": f"answer {a['fill']:.0%}: {a['question'][:50]}"})
                oncall._save(b)
            else:
                # below her 0.618 exploit line: an unfinished answer waits its turn; the ASKER's floor (ours 0.65)
                # is what lifts an answer to the top, not how empty it is
                oncall.add(f"answer {a['fill']:.0%}: {a['question'][:50]}", a["asker"], kind="answer", bid=a["id"],
                           pressure=0.55 * (1 - a["fill"]) + 0.05, resume={"hint": hint, "fill": a["fill"]})
        else:
            oncall.done(a["id"])
    except Exception: pass


def fill(aid: str, part: str, text: str, note: str = None) -> Optional[Dict]:
    """a later tick fills a gap (or upgrades a part): a new version, the old one kept underneath"""
    a = _load(_path(aid), None)
    if not a: return None
    prev = {"version": a["version"], "t": time.time(), "parts": [dict(p) for p in a["parts"]],
            "gaps": [dict(g) for g in a["gaps"]], "fill": a["fill"]}
    a.setdefault("strata", []).append(prev)                     # the earlier answer, compacted under the new one
    hit = False
    for p in a["parts"]:
        if p["name"] == part:
            p.update({"filled": True, "text": text, "amended": a["version"] + 1}); hit = True
    if not hit: a["parts"].append({"name": part, "filled": True, "text": text, "amended": a["version"] + 1})
    a["gaps"] = [g for g in a["gaps"] if g["name"] != part]
    a["upgrades"] = [u for u in a["upgrades"] if u["name"] != part]
    a["version"] += 1
    a["fill"] = round(sum(1 for p in a["parts"] if p["filled"]) / max(1, len(a["parts"])), 3)
    a["history"].append({"version": a["version"], "t": time.time(), "fill": a["fill"],
                         "note": note or f"went back and filled '{part}'"})
    json.dump(a, open(_path(aid), "w", encoding="utf-8"), indent=1)
    _hold(a)
    return a


def render(a: Dict) -> str:
    """the delivered text: the useful parts now, the missing parts named, the upgradable parts named"""
    out = [f"{a['question']}  — answer v{a['version']}, {a['fill']:.0%} filled, by {a['answered_by']}"]
    for p in a["parts"]:
        if p["filled"]:
            out.append(f"  [x] {p['name']}: {p['text']}" + (f"   (amended in v{p['amended']})" if p.get("amended") else ""))
    if a["gaps"]:
        out.append("  missing:")
        for g in a["gaps"]:
            out.append(f"    [ ] {g['name']} — {g.get('why', '')}" + (f"  (to fill: {g['how']})" if g.get("how") else ""))
    if a["upgrades"]:
        out.append("  could still be upgraded / would like to explore:")
        for u in a["upgrades"]:
            out.append(f"    ~ {u['name']} — {u.get('note', '')}")
    if a.get("strata"):
        out.append(f"  ({len(a['strata'])} earlier version(s) underneath: " +
                   ", ".join(f"v{s['version']} {s['fill']:.0%}" for s in a["strata"]) + ")")
    return "\n".join(out)


def from_story(path: str) -> Optional[Dict]:
    """a scored story IS a partly filled answer: invariants = parts, recovered = filled, misses = gaps"""
    s = _load(path, None)
    if not s: return None
    tb = s.get("mika_teach_back") or s.get("teach_back") or {}
    per = tb.get("per_invariant") or []
    if not per: return None
    world = s.get("world") or os.path.basename(os.path.dirname(os.path.dirname(path)))
    aid = f"answer-story-{world}-{s.get('n')}"
    if os.path.exists(_path(aid)):
        a = _load(_path(aid), None)
        # closed petals on the flower fill gaps that were open when the story was scored
        fl = _load(FLOWER, {}).get(world, {}).get("voids", {})
        changed = False
        for g in list(a.get("gaps", [])):
            v = fl.get(g["name"], {})
            if any(p.get("closed") for p in v.get("petals", [])):
                a = fill(aid, g["name"], "recovered in a later lesson (the bell closed this petal)", "the bell filled a gap"); changed = True
        return a if changed else None
    parts = [p["key"] for p in per]
    filled = {p["key"]: f"recovered ({p.get('matched', '?')}/{p.get('needed', '?')} atoms: {p.get('hit', '')})" for p in per if p.get("recovered")}
    gaps = [{"name": p["key"], "why": f"only {p.get('matched', 0)}/{p.get('needed', '?')} atoms said back ({p.get('hit') or 'none'})",
             "how": "a bell lesson on this rule (lesson.py), deeper each miss"} for p in per if not p.get("recovered")]
    return new(f"teach back story {s.get('n')} of {world}: {len(parts)} rules", parts, filled, gaps, [],
               source="mika", aid=aid, asker="planet")


def stories(limit: int = 40) -> List[Dict]:
    paths = sorted(glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")), key=os.path.getmtime)[-limit:]
    out = []
    for p in paths:
        try:
            a = from_story(p)
            if a: out.append(a)
        except Exception: continue
    return out


def status():
    files = sorted(glob.glob(os.path.join(ANSWERS, "*.json")), key=os.path.getmtime)
    if not files: print("no answer bubbles yet"); return
    xs = [_load(p, {}) for p in files]
    full = sum(1 for a in xs if not a.get("gaps"))
    print(f"answer bubbles: {len(xs)} ({full} fully answered, {len(xs) - full} still holding gaps); "
          f"{sum(a.get('version', 1) - 1 for a in xs)} amendments made")
    for a in xs[-8:]:
        print(f"  v{a['version']} {a['fill']:.0%} [{a['answered_by']:6s}] {a['id']:36s} {a['question'][:50]}"
              + (f"  gaps {len(a['gaps'])}" if a.get("gaps") else "") + (f"  upgrades {len(a['upgrades'])}" if a.get("upgrades") else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default=None); ap.add_argument("--parts", default=""); ap.add_argument("--filled", default="")
    ap.add_argument("--gaps", default=""); ap.add_argument("--upgrades", default=""); ap.add_argument("--from", dest="src", default="claude")
    ap.add_argument("--show", default=None); ap.add_argument("--fill", default=None); ap.add_argument("--part", default=None); ap.add_argument("--text", default="")
    ap.add_argument("--stories", action="store_true"); ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.new:
        parts = [x.strip() for x in a.parts.split("|") if x.strip()]
        filled = {}
        for x in a.filled.split("|"):
            if ":" in x: k, v = x.split(":", 1); filled[k.strip()] = v.strip()
            elif x.strip(): filled[x.strip()] = "done"
        gaps = []
        for x in a.gaps.split("|"):
            if not x.strip(): continue
            name, _, rest = x.partition(":"); why, _, how = rest.partition("::")
            gaps.append({"name": name.strip(), "why": why.strip(), "how": how.strip()})
        ups = [{"name": x.split(":")[0].strip(), "note": x.partition(":")[2].strip()} for x in a.upgrades.split("|") if x.strip()]
        r = new(a.new, parts, filled, gaps, ups, source=a.src)
        print(render(r))
    elif a.show: print(render(_load(_path(a.show), {})))
    elif a.fill:
        r = fill(a.fill, a.part, a.text); print(render(r) if r else "no such answer")
    elif a.stories:
        r = stories(); print(f"answer bubbles from stories: {len(r)} created/updated")
        for x in r[-3:]: print(render(x)); print()
    else: status()
