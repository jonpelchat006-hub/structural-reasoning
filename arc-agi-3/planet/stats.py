#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stats.py — the STATS ORGAN: the planet learns that marks on the screen carry numbers.

During a watched session the player drops raw screenshots into <world>/stats/session_*/
(one every ~20 s, plus the last frames — end screens carry the score). In the SLEEP the
lower ocean's seeing model (gemma3 is multimodal) reads a sample of them: what numbers are
on the HUD, kills/deaths/assists if shown, health, resources, and whether a victory/defeat
screen is up. Everything it reads lands in <world>/stats/ledger.jsonl — one row per shot —
and a per-session summary in <world>/stats/sessions.json. The chatbot reads the ledger, so
"what was my KDA lately" is answered from what was actually watched.

Honest bounds: the reader sees only what was on screen when the shot was taken. Scoreboards
that need Tab held are only read if you held Tab while it watched; a session with no visible
numbers yields an empty row, not an invented one. Every value carries the shot it came from.

Usage:
  python stats.py --root D:\\planet\\ocean\\dota_2          # digest this world's new sessions
  python stats.py --root D:\\planet\\ocean --all            # every world with a stats folder
  python stats.py --root D:\\planet\\ocean\\dota_2 --summary  # print what the ledger holds
"""
from __future__ import annotations
import argparse, base64, glob, json, os, re, sys, time
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import lower

MODEL = "gemma3:4b"
PER_SESSION = 14          # shots read per session (evenly spaced + the last two)

PROMPT = (
    "This is a screenshot from a video game. Read ONLY what is actually visible; never guess and never "
    "derive one number from another. Most games show FEW of these fields — omitting keys is the normal, "
    "correct answer. "
    "Return JSON with these keys (omit a key entirely when it is not visible):\n"
    '{"kills": int, "deaths": int, "assists": int, "kda_text": "the exact text if a K/D/A display is visible", '
    '"health": int, "resource": int, "gold": int, "level": int, "score_text": "any score text", '
    '"clock": "the game clock if visible", "screen": "playing" | "menu" | "scoreboard" | "victory" | "defeat" | "loading", '
    '"other_numbers": {"label": value}}\n'
    "In other_numbers, list EVERY distinct number display you can see, each under a short stable lowercase "
    "label naming what the display is labeled or looks like (e.g. \"stress\", \"torch\", \"ammo\", \"xp\", "
    "\"souls\"). Use the same label for the same display every time. JSON only.")


def read_shot(model: str, path: str) -> Optional[Dict]:
    try:
        with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode()
    except Exception:
        return None
    out = lower._ask_image(model, PROMPT, b64, timeout=120.0, json_mode=True, num_predict=300)
    if not out: return None
    try:
        d = json.loads(out)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def pick(files: List[str], k: int) -> List[str]:
    if len(files) <= k: return files
    idx = sorted({int(i * (len(files) - 1) / (k - 3)) for i in range(k - 2)} | {len(files) - 2, len(files) - 1})
    return [files[i] for i in idx]


def digest_world(root: str, model: str) -> None:
    sdir = os.path.join(root, "stats")
    if not os.path.isdir(sdir): print("no stats folder in", root); return
    world = os.path.basename(root.rstrip("\\/"))
    ledger_path = os.path.join(sdir, "ledger.jsonl")
    done: set = set()
    rows: List[Dict] = []
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for l in f:
                r = json.loads(l); rows.append(r); done.add(r["shot"])
    except Exception: pass
    models = lower.available([model])
    if not models: print("vision model not available in Ollama:", model); return
    new = 0
    for sess in sorted(glob.glob(os.path.join(sdir, "session_*"))):
        shots = sorted(glob.glob(os.path.join(sess, "*.jpg")) + glob.glob(os.path.join(sess, "*.png")))
        todo = [s for s in pick(shots, PER_SESSION) if os.path.relpath(s, sdir) not in done]
        for s in todo:
            d = read_shot(models[0], s)
            rel = os.path.relpath(s, sdir)
            row = {"world": world, "session": os.path.basename(sess), "shot": rel,
                   "t": os.path.getmtime(s), "read": d or {}}
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row); done.add(rel); new += 1
            vis = {k: v for k, v in (d or {}).items() if k != "other_numbers" and v not in (None, "", {})}
            print(f"  {rel}: {json.dumps(vis, ensure_ascii=False)[:140]}")
    # per-session summaries — SKEPTICAL: a 4b vision model fabricates (it read "KDA 64/64/64" in a
    # game with no KDA). A stat is kept only when it RECURS: the field appears in >=2 shots of the
    # session, and a K/D/A must come from kda_text matching a real k/d/a pattern with kills
    # non-decreasing across shots. Omission is the normal answer.
    KDA_RE = re.compile(r"^\s*(\d{1,3})\s*/\s*(\d{1,3})(?:\s*/\s*(\d{1,3}))?\s*$")
    sessions: Dict[str, Dict] = {}
    by_sess: Dict[str, List[Dict]] = {}
    for r in sorted(rows, key=lambda r: r["t"]):
        by_sess.setdefault(r["session"], []).append(r)
    for name, rs in by_sess.items():
        s = {"world": world, "shots": len(rs), "start": rs[0]["t"], "end": rs[-1]["t"]}
        kdas = []
        for r in rs:
            m = KDA_RE.match(str(r["read"].get("kda_text", "")))
            if not m: continue
            k = tuple(int(g) if g else None for g in m.groups())
            d = r["read"]
            # fabrication signatures: all three equal, or the same value smeared across unrelated fields
            vals = [v for v in (d.get("kills"), d.get("deaths"), d.get("assists"), d.get("gold"), d.get("level"))
                    if isinstance(v, (int, float))]
            smear = len(vals) >= 3 and max(set(vals), key=vals.count) and vals.count(max(set(vals), key=vals.count)) >= 3
            if len({v for v in k if v is not None}) == 1 or (smear and k[0] in vals and vals.count(k[0]) >= 3):
                continue
            if k[1] > 40 or k[0] > 99: continue            # sanity: nobody dies 66 times; that's another number
            kdas.append(k)
        if kdas:
            from collections import Counter as _C
            best, cnt = _C(kdas).most_common(1)[0]
            if cnt >= 2:                       # a K/D/A is only believed when the SAME reading recurred
                chain = [k for k in kdas if k == best or (k[0] >= best[0] and k[1] >= best[1])]
                k = max(chain, key=lambda t: (t[0], t[1]))
                s["kills"], s["deaths"] = k[0], k[1]
                s["kda"] = f"{k[0]}/{k[1]}" + (f"/{k[2]}" if k[2] is not None else "")
                if k[2] is not None: s["assists"] = k[2]
        for field in ("gold", "level"):
            vals = [r["read"][field] for r in rs if isinstance(r["read"].get(field), (int, float))]
            if len(vals) >= 2: s[field] = vals[-1]
        clocks = [r["read"]["clock"] for r in rs if re.match(r"^\d{1,3}:\d{2}$", str(r["read"].get("clock", "")))]
        if clocks: s["clock"] = clocks[-1]
        ends = [r["read"]["screen"] for r in rs if r["read"].get("screen") in ("victory", "defeat")]
        if ends: s["result"] = ends[-1]
        sessions[name] = s
    with open(os.path.join(sdir, "sessions.json"), "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=1, ensure_ascii=False)
    regs = harvest_registers(rows, sessions)
    with open(os.path.join(sdir, "registers.json"), "w", encoding="utf-8") as f:
        json.dump(regs, f, indent=1, ensure_ascii=False)
    learned = [f"{k} ({v['kind']}{', outcome-linked' if v.get('outcome_link') else ''})"
               for k, v in sorted(regs.items(), key=lambda kv: -kv[1]["importance"])[:6] if v["kind"] != "constant"]
    print(f"{world}: read {new} new shots; {len(sessions)} sessions; registers: {', '.join(learned) or 'none yet'}")


def _norm_label(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", "", str(s).lower()).strip()
    return re.sub(r"\s+", "_", s)[:24]


def harvest_registers(rows: List[Dict], sessions: Dict) -> Dict:
    """WHAT MATTERS in this game is not declared, it is discovered — Jonathan's budget rule:
    watch which numbers are spent and gained. Every number display the reader ever saw becomes a
    REGISTER with a per-session series. Classification by movement: a number that goes both up and
    down is a BUDGET (health, gold, stress — the stuff of decisions); monotonic within sessions is
    an ACCUMULATOR (kills, xp); never moving is CONSTANT (Warframe's junk resources end up here or
    'rare' — nobody has to care about every little thing). Importance = how alive it is (activity),
    plus co-movement with other registers (gold jumps when kills tick = the layers coupling), plus,
    once enough sessions carry a victory/defeat, correlation with the outcome (deaths ↔ losses is
    how KDA EARNS its importance — it is never assumed)."""
    series: Dict[str, Dict[str, List]] = {}
    for r in sorted(rows, key=lambda r: r["t"]):
        d = r["read"]; sess = r["session"]
        flat = {}
        for k in ("kills", "deaths", "assists", "health", "resource", "gold", "level"):
            if isinstance(d.get(k), (int, float)): flat[k] = float(d[k])
        JUNK = {"label", "value", "number", "int", "n", "count", "unknown", ""}
        for k, v in (d.get("other_numbers") or {}).items():
            lab = _norm_label(k)
            if lab in JUNK: continue
            try: flat[lab] = float(v)
            except Exception: pass
        for k, v in flat.items():
            series.setdefault(k, {}).setdefault(sess, []).append(v)
    out: Dict[str, Dict] = {}
    for label, by_sess in series.items():
        n = sum(len(v) for v in by_sess.values())
        ups = downs = 0
        finals = {}
        for sess, vals in by_sess.items():
            for a, b in zip(vals, vals[1:]):
                if b > a: ups += 1
                elif b < a: downs += 1
            finals[sess] = vals[-1]
        distinct = len({v for vals in by_sess.values() for v in vals})
        moves = ups + downs
        if n < 3 or distinct <= 1 or moves == 0:
            kind = "rare" if n < 3 else "constant"
        elif min(ups, downs) / moves < 0.2:            # a few contrary moves are misreads, not spending
            kind = "accumulator"
        else: kind = "budget"
        activity = (ups + downs) / max(1, n - len(by_sess))
        # outcome link: does the session-final value separate victories from defeats? (needs >=2 of each... be honest: >=3 resulted sessions)
        resulted = [(finals[s], sessions[s]["result"]) for s in finals if s in sessions and sessions[s].get("result")]
        outcome_link = None
        if len(resulted) >= 3 and len({r for _, r in resulted}) == 2:
            wins = [v for v, r in resulted if r == "victory"]; losses = [v for v, r in resulted if r == "defeat"]
            if wins and losses and (max(wins) < min(losses) or max(losses) < min(wins)):
                outcome_link = "higher-in-" + ("victory" if min(wins) > max(losses) else "defeat")
        out[label] = {"kind": kind, "n": n, "sessions": len(by_sess), "ups": ups, "downs": downs,
                      "activity": round(activity, 3), "last": finals[max(finals)],
                      "importance": round(activity * (2.0 if kind == "budget" else 1.0)
                                          * (2.0 if outcome_link else 1.0) * min(1.0, len(by_sess) / 3), 3),
                      "outcome_link": outcome_link}
    # co-movement: aligned per-shot deltas between the top labels (the layers coupling)
    tops = [k for k, v in sorted(out.items(), key=lambda kv: -kv[1]["importance"])[:8] if v["kind"] in ("budget", "accumulator")]
    for a in tops:
        best, bs = None, 0
        for b in tops:
            if a == b: continue
            agree = tot = 0
            for sess in series[a]:
                va, vb = series[a].get(sess, []), series[b].get(sess, [])
                for i in range(1, min(len(va), len(vb))):
                    da, db = va[i] - va[i-1], vb[i] - vb[i-1]
                    if da and db: tot += 1; agree += (da > 0) == (db > 0)
            if tot >= 4 and agree / tot > 0.75 and agree / tot > bs:
                best, bs = b, agree / tot
        if best: out[a]["moves_with"] = best
    return out


def summary(root: str) -> str:
    sdir = os.path.join(root, "stats")
    try:
        with open(os.path.join(sdir, "sessions.json"), "r", encoding="utf-8") as f: sessions = json.load(f)
    except Exception:
        return ""
    world = os.path.basename(root.rstrip("\\/"))
    lines = []
    try:
        with open(os.path.join(sdir, "registers.json"), "r", encoding="utf-8") as f: regs = json.load(f)
        learned = [f"{k} ({v['kind']}" + (f", moves with {v['moves_with']}" if v.get("moves_with") else "")
                   + (f", {v['outcome_link']}" if v.get("outcome_link") else "") + ")"
                   for k, v in sorted(regs.items(), key=lambda kv: -kv[1]["importance"])[:6]
                   if v["kind"] in ("budget", "accumulator")]
        if learned: lines.append(f"{world} — what matters so far: " + "; ".join(learned))
    except Exception: pass
    for name, s in sorted(sessions.items()):
        day = time.strftime("%b %d %H:%M", time.localtime(s.get("start", 0)))
        bits = [f"{world} {day}"]
        if s.get("kda"): bits.append(f"KDA {s['kda']}")
        elif s.get("kda_text"): bits.append(f"KDA text '{s['kda_text']}'")
        for k in ("gold", "level", "clock", "result"):
            if s.get(k) not in (None, ""): bits.append(f"{k} {s[k]}")
        bits.append(f"({s['shots']} shots read)")
        lines.append(", ".join(bits))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--all", action="store_true", help="root is the ocean; digest every world with a stats folder")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    roots = [os.path.dirname(p) for p in glob.glob(os.path.join(a.root, "*", "stats"))] if a.all else [a.root]
    for r in roots:
        if a.summary: print(summary(r) or f"(no ledger in {r})")
        else: digest_world(r, a.model)


if __name__ == "__main__":
    main()
