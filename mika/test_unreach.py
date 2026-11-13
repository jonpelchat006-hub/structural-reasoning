"""simulation check of the Oct 16 night fix: an unreachable recipe step waits 10 presses and is asked again"""
import sys
sys.path.insert(0, r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet")
import mika_mind as mm

j = mm.load_journal("ls20")
m = mm.MikaMind(j, log=print)
lv = 1
print("recipe:", m.recipes.get(lv))
key = {"id": "0@46,51"}; other = {"id": "open@29,34 up"}
m.sense(lv, 30, 2, 8)
o = m.order([key, other], lv, None)
print("first pick:", o[0]["id"])
m.observe({"level": lv, "id": "0@46,51", "result": "unreachable"})
m.sense(lv, 28, 2, 10)
o = m.order([other], lv, None)
print("at since 10, first pick:", o[0]["id"], "(should NOT be the key: she waits)")
m.sense(lv, 20, 2, 19)
o = m.order([other], lv, None)
print("at since 19, first pick:", o[0]["id"], "(still waiting)")
m.sense(lv, 18, 2, 20)
o = m.order([other], lv, None)
print("at since 20, first pick:", o[0]["id"], "(asks again)")
for i in range(5):
    m.observe({"level": lv, "id": "0@46,51", "result": "unreachable"})
print("recipe off after 6 unreachable:", lv in m.recipe_off)
m2 = mm.MikaMind(j, log=print)
m2.sense(lv, 30, 2, 8)
m2.observe({"level": lv, "id": "0@46,51", "result": "changed"})
print("changed advances to step", m2.rec_pos.get(lv))
print("recipe_log:", m.recipe_log[:2])
