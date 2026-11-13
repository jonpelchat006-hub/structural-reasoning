"""Before run 28 (Oct 28): run 27's voluntary resets were not shown to her, so the key put back by a reset was read as a
touch on the next press. Drop those changes from level 6's nodes. A backup is taken first."""
import json, time, shutil
p = r"D:\planet\mika\ls20.json"
shutil.copy(p, r"D:\planet\mika\think\ls20_before_run28_clean.json")
j = json.load(open(p, encoding="utf-8"))
START = "14|##. / .## / #.#"                             # level 6's start key: a change TO it is a reset, not a touch
out = []
for k in [k for k in list(j["core_nodes"]) if k.startswith("L5:")]:
    e = j["core_nodes"][k]
    tr = [t for t in e["trans"] if not (isinstance(t, list) and t[1] == START and t[0] != START)]
    if len(tr) != len(e["trans"]):
        out.append((k, len(e["trans"]) - len(tr)))
        if tr: e["trans"] = tr
        else: j["core_nodes"].pop(k)
j.setdefault("core_fixes", []).append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "what": f"before run 28: removed key changes back to level 6's start key (resets read as touches in run 27): {out}"})
json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False)
print(out, [k for k in j["core_nodes"] if k.startswith("L5:")])
