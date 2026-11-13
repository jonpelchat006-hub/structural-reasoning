r"""Move what Mika already knows (her sp80 and ls20 journals, Oct 13-16) into her tree, life by life, with each
past life's growth written into the ring of the day it happened. Snapshots only where that life's frames still exist."""
import json, os, shutil, sys
sys.path.insert(0, r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet")
import mika_tree as T

if os.path.isdir(T.ROOT): shutil.rmtree(T.ROOT)                     # a clean build (nothing else writes here yet)
for game in ["sp80", "ls20"]:
    j = json.load(open(rf"D:\planet\mika\{game}.json", encoding="utf-8"))
    lives = j["lives"]
    for k, life in enumerate(lives):
        jk = dict(j, lives=lives[:k + 1], routes={lv: r for lv, r in j.get("routes", {}).items() if int(r.get("life", 0) or 0) <= k + 1})
        rec, frames = None, None
        if k == len(lives) - 1:                                       # only the last life's frames are still on disk
            rp = rf"D:\planet\mika\routes\{game}_life{k + 1}_rec.jsonl"
            if os.path.exists(rp):
                rec = [json.loads(l) for l in open(rp, encoding="utf-8") if l.strip()]; frames = rf"D:\planet\eye\play_{game}.npz"
        T.grow(game, jk, life, k + 1, rec_rows=rec, frames_path=frames, recipe_log=life.get("recipe_log"), log=lambda *a: None, day=life["date"][:10])
# two seed lessons read from her own records (not yet confirmed by her in a second game)
T.seed_lesson("repeat-what-changes", "A thing that changes each time it is touched may need touching more than once before the way opens.",
              "ls20", "her ls20 life 1: the colour-0 thing changed 8 times before the colour-5 thing gave the level (read by Claude, Oct 16)")
T.seed_lesson("arrange-then-act", "Some levels are won by arranging things first and then doing one final action; the final action does nothing until the arrangement is right.",
              "sp80", "her sp80 level-1 route: move the bar, then pour (action 5); pours before that did nothing (read by Claude, Oct 16)")
T.show()
