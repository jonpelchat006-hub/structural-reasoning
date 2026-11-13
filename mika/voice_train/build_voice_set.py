"""build_voice_set.py - training examples for her voice, from her own lives (Oct 30 2026).

Every 6 experiments on a level she has not cleared, voice4 writes a snapshot: the exact question her voice would get (her
evidence in her words), the ids of the things on offer, and the screen. Every experiment result is written too. This
turns each snapshot into one training example whose answer is what HINDSIGHT says she should have tried:

  - an offered thing whose touch later WON the level (in this life, a later life, or any other run of the same game)
    is proposed with "expect": "level";
  - one that later CHANGED the board, "changed"; one that REFILLED the bar, "refill";
  - up to 3, best first; when none of the offered things ever did anything, the answer is {"claims": []} (stay quiet:
    voice v3's 282 proposals led nowhere and its detours cost ls20 its second level).

The "because" is built only from what the question itself shows (result counts, never tried), so the voice is never
taught to cite what it could not have known. Games can be held out for testing.

    python3 build_voice_set.py --think <dir with *_think.jsonl> [--think ...] --logs <dir with <game>.log> [--logs ...]
                               --out <dir> [--holdout ls20,vc33,...] [--persona <planet dataset.jsonl>]
"""
from __future__ import annotations
import argparse, glob, json, os, random, re, collections

RANK = {"level": 3, "changed": 2, "refill": 1}
SHELL_SYSTEM = """You are the imagination of Mika, a small mind learning a video game that has no instructions.
Mika's body walks to things on the screen and tries the buttons there or bumps into them. Each try ends with a result:
pass (walked through), wall (blocked), nothing (touched, nothing changed), changed (the board changed), refill (a bar refilled),
level (the level was won), unreachable, untestable.
Mika decides; you only propose. Each proposal must name one thing id from the list you are given, say what you expect it
to do, and say why, using what won the earlier levels. Mika checks every proposal against everything she has seen before
her body tries it, so do not propose things that already did nothing many times unless you say what is different now.
Answer only with JSON."""
EXP_LINE = re.compile(r"experiment (\S+?)(?: \([^)]*\))?: (level|LEVEL|changed|refill|nothing|pass|wall|unreachable|untestable)\b")


def game_of(path):
    return os.path.basename(path).split("_think")[0].split(".")[0].split("-")[0]


def pooled_outcomes(think_dirs, log_dirs):
    """(game, level, id) -> Counter of results, over every run we have"""
    pool = collections.defaultdict(collections.Counter)
    for d in think_dirs:
        for p in glob.glob(os.path.join(d, "*_think.jsonl")):
            g = game_of(p)
            for l in open(p, encoding="utf-8"):
                try: t = json.loads(l)
                except Exception: continue
                if t.get("kind") == "exp": pool[(g, int(t["level"]), str(t["id"]))][str(t.get("result")).lower()] += 1
    for d in log_dirs:                                     # older runs: only the text log
        for p in glob.glob(os.path.join(d, "*.log")):
            if p.endswith("_think.jsonl"): continue
            g = game_of(p); lvl = 0
            for l in open(p, encoding="utf-8", errors="replace"):
                m = re.search(r">>> LEVEL (\d+) at press", l)
                if m: lvl = int(m.group(1)); continue
                if re.match(r"^\S+-[0-9a-f]{6,}: \d+ levels", l): lvl = 0; continue    # a new life starts at level 1
                m = EXP_LINE.search(l)
                if m:
                    r = m.group(2).lower()
                    pool[(g, lvl - 1 if r == "level" and lvl > 0 else lvl, m.group(1))][r] += 1   # the win line follows '>>> LEVEL k'
    return pool


def evidence_lines(prompt):
    """id -> the line the question shows for it"""
    out = {}
    for l in prompt.splitlines():
        m = re.match(r"^- (\S+?):", l)
        if m: out[m.group(1)] = l
    return out


def because(tid, expect, line):
    m = re.search(r"results: (.*)$", line or "")
    if m:
        counts = dict((k.strip(), int(v)) for k, v in re.findall(r"(\w[\w ]*?) x(\d+)", m.group(1)))
        if counts.get(expect):
            return f"{tid} already gave {expect} {counts[expect]} time{'s' if counts[expect] > 1 else ''} on this level."
        top = max(counts.items(), key=lambda kv: kv[1])[0] if counts else None
        return f"{tid} was tried before ({m.group(1).strip()}), but nothing else on the list has changed the board here."
    if "never tried" in (line or ""):
        return f"{tid} has never been tried on this level, and the things that were tried here did not win it."
    return f"{tid} is on the screen and has not been tried from here."


def label(snap, later, pool, game):
    """the hindsight answer for one snapshot"""
    lvl = int(snap["level"]); ids = [str(i) for i in snap["ids"]]
    lines = evidence_lines(snap["prompt"])
    scored = []
    for tid in ids:
        res = collections.Counter(later.get((lvl, tid), [])) + pool.get((game, lvl, tid), collections.Counter())
        best = max([r for r in res if r in RANK], key=lambda r: RANK[r], default=None)
        if best: scored.append((RANK[best], res[best], tid, best))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    claims = [{"try": tid, "expect": best, "because": because(tid, best, lines.get(tid))} for _, _, tid, best in scored[:3]]
    return {"claims": claims}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--think", action="append", default=[])
    ap.add_argument("--logs", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--holdout", default="")
    ap.add_argument("--persona", default=None)
    ap.add_argument("--quiet-share", type=float, default=0.35, help="most examples with an empty answer, as a share")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--persona-n", type=int, default=40, help="how many of Jonathan's planet-voice examples to mix in")
    a = ap.parse_args()
    random.seed(a.seed)
    hold = set(x for x in a.holdout.split(",") if x)
    pool = pooled_outcomes(a.think, a.logs + a.think)
    os.makedirs(a.out, exist_ok=True)
    train, test, stats = [], [], collections.Counter()
    for d in a.think:
        run = os.path.basename(os.path.normpath(d))
        for p in sorted(glob.glob(os.path.join(d, "*_think.jsonl"))):
            g = game_of(p)
            recs = []
            for l in open(p, encoding="utf-8"):
                try: recs.append(json.loads(l))
                except Exception: pass
            for i, t in enumerate(recs):
                if t.get("kind") != "snap": continue
                later = collections.defaultdict(list)
                for u in recs[i + 1:]:
                    if u.get("kind") == "exp" and u.get("life") == t.get("life"):
                        later[(int(u["level"]), str(u["id"]))].append(str(u.get("result")).lower())
                ans = label(t, later, pool, g)
                fid = f"{run}_{g}_{t.get('life')}_{t['level']}_{t['n']}"
                ex = {"id": fid, "game": g, "level": t["level"], "frame_data": t["frame"],
                      "messages": [{"role": "system", "content": SHELL_SYSTEM},
                                   {"role": "user", "content": t["prompt"]},
                                   {"role": "assistant", "content": json.dumps(ans)}],
                      "positives": [c["try"] for c in ans["claims"]], "offered": t["ids"]}
                stats["quiet" if not ans["claims"] else "speaks"] += 1
                (test if g in hold else train).append(ex)
    # not too many quiet answers in training
    speak = [e for e in train if e["positives"]]; quiet = [e for e in train if not e["positives"]]
    keep_q = int(a.quiet_share / (1 - a.quiet_share) * len(speak)) if speak else len(quiet)
    random.shuffle(quiet); train = speak + quiet[:keep_q]; random.shuffle(train)
    persona = []
    if a.persona and os.path.exists(a.persona):
        for l in open(a.persona, encoding="utf-8"):
            try: persona.append({"id": "persona", "game": "persona", "messages": json.loads(l)["messages"]})
            except Exception: pass
    random.shuffle(persona); persona = persona[: a.persona_n]
    with open(os.path.join(a.out, "train.jsonl"), "w") as fh:
        for e in train + persona: fh.write(json.dumps(e) + "\n")
    with open(os.path.join(a.out, "test.jsonl"), "w") as fh:
        for e in test: fh.write(json.dumps(e) + "\n")
    print(f"snapshots: {sum(stats.values())} ({stats['speaks']} with a hindsight answer, {stats['quiet']} quiet)")
    print(f"train: {len(train)} game examples ({len(speak)} speak, {min(keep_q, len(quiet))} quiet) + {len(persona)} persona; "
          f"test (held-out games {sorted(hold)}): {len(test)}")
    print("pooled (game, level, thing) outcomes:", len(pool))


if __name__ == "__main__":
    main()
