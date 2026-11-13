"""Oct 16 evening: (1) give her existing routes the cells-changed count of every press (from the saved press records),
for trimming and the surprise watch; (2) fill each cleared branch's leaderboard from the journal's past lives."""
import glob, json, os, re, sys
sys.path.insert(0, r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet")
import mika_mind as M, mika_tree as T
for game in ["sp80", "ls20"]:
    j = M.load_journal(game)
    files = sorted(glob.glob(rf"D:\planet\mika\routes\{game}_life*_rec.jsonl"), key=lambda p: -int(re.search(r"life(\d+)", p).group(1)))
    for lv, rt in j.get("routes", {}).items():
        want = [list(p[:3]) for p in rt["presses"]]
        for fp in files:
            rows = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()]
            seg = M.routes_from_rec(rows).get(int(lv))
            if seg and [p[:3] for p in seg] == want:
                rt["presses"] = seg; print(game, "L" + str(int(lv) + 1), "route changes from", os.path.basename(fp), [p[3] for p in seg]); break
        else:
            print(game, "L" + str(int(lv) + 1), "no matching press record; the route stays without change counts")
    M.save_journal(j)
    for k, life in enumerate(j["lives"]):
        lp = life.get("level_presses") or []
        for lvl in range(int(life.get("levels", 0))):
            if lvl >= len(lp): continue
            b = T.branch(game, lvl); took = int(lp[lvl]) - (int(lp[lvl - 1]) if lvl > 0 else 0)
            recs = b["data"].setdefault("records", [])
            if not any(r["life"] == k + 1 for r in recs):
                recs.append({"life": k + 1, "date": life["date"][:10], "presses": took, "mode": life.get("mode", "push")})
            b["data"]["best"] = min(r["presses"] for r in recs)
            T._save(T._p(game, f"L{lvl + 1}.json"), b)
    for lvl in range(2):
        b = T._load(T._p(game, f"L{lvl + 1}.json"), {})
        if b.get("data", {}).get("records"): print(game, f"L{lvl + 1} leaderboard: best {b['data']['best']}, presses by life", [r["presses"] for r in b["data"]["records"]])
    mm = M.MikaMind(M.load_journal(game), log=lambda *a: None)
    print(game, "trimmed routes to try:", {lv + 1: f"{len(t)} of {len(mm.routes[lv])}" for lv, t in mm.trims.items()})
