"""Oct 16 night, by hand from D:\\planet\\mika\\logs\\ls20_20261013_083813.log: where ls20 life 1's level-2 resets fell in
its experiment list. Level 2 = experiments 44-54: pokes at 180, 182, 184 (MATCH) -> RESET #7 at 184 (door 18 away, budget 2);
poke 201 -> RESET #8 at 203; poke 220 -> RESET #9 at 222; poke 239, ring 11@51,40 at 242, pokes 245 and 247, ring 11@16,15
at 262, door 5@39,13 -> LEVEL 2 at 267. So the resets fall before experiments 47, 48 and 49 (level index 1)."""
import json
J = r"D:\planet\mika\ls20.json"
j = json.load(open(J, encoding="utf-8"))
life = j["lives"][0]
ex = life["experiments"]
assert [e["id"] for e in ex[44:55]] == ["0@46,51"] * 6 + ["11@51,40", "0@46,51", "0@46,51", "11@16,15", "5@39,13"], [e["id"] for e in ex[44:55]]
assert ex[54]["result"] == "level"
life["resets_at"] = [[1, 47], [1, 48], [1, 49]]
life["resets_at_note"] = "level-2 resets backfilled by hand from the Oct 13 play log (Oct 16 night)"
json.dump(j, open(J, "w", encoding="utf-8"), indent=1)
import sys; sys.path.insert(0, r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet")
import mika_mind as mm
m = mm.MikaMind(mm.load_journal("ls20"), log=lambda *a: None)
print("level-2 recipe now:", m.recipes.get(1))
