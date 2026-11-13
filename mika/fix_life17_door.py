"""ls20 life 17 (Oct 16 night): the winning press into the door 5@39,13 was filed 'refill' (the new level's bar read as a refill,
a bug fixed in play.py the same night). Put it back to 'level' so the door is not taken for a ring."""
import json
J = r"D:\planet\mika\ls20.json"
j = json.load(open(J, encoding="utf-8"))
life = j["lives"][16]
assert life["levels"] == 2 and life["level_presses"] == [25, 129], (life["levels"], life["level_presses"])
fixed = 0
for e in life["experiments"]:
    if e.get("id") == "5@39,13" and int(e.get("level", -1)) == 1 and e.get("result") == "refill":
        e["result"] = "level"; e["fixed_note"] = "was filed 'refill' on the winning press (Oct 16 night bug)"; fixed += 1
for r in life.get("recipe_log", []):
    if r.get("id") == "5@39,13" and r.get("result") == "refill": r["result"] = "level"
print("fixed", fixed)
print("resets_at", life.get("resets_at"))
print("relations kept", len(j.get("relations", [])), [(r["learned_on"], r["src_colour"], r["target_colours"], r["colour"], len(r["states"])) for r in j.get("relations", [])])
print("routes", {k: v.get("len") for k, v in j.get("routes", {}).items()})
json.dump(j, open(J, "w", encoding="utf-8"), indent=1)
import sys; sys.path.insert(0, r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet")
import mika_mind as mm
m = mm.MikaMind(mm.load_journal("ls20"), log=lambda *a: None)
print("L2 recipe:", m.recipes.get(1), "| refills:", sorted(m.refill_ids))
