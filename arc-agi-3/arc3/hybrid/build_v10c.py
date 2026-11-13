"""Hybrid v10c = the v10b notebook (kernel version 10) with the layer replaced by mika_layer_core_v10c.py: Jonathan's
notes (D:/planet/mika/notes_from_jonathan.md), each said only when its "When" shows up in the frames, and the step bar
measured per life and said in presses.

    python build_v10c.py <v10b notebook dir> <out dir>"""
import base64, json, sys
from pathlib import Path
HERE = Path(__file__).parent
src, out = Path(sys.argv[1]), Path(sys.argv[2])
j = json.load(open(src / "mika-duck.ipynb"))
cells = j["cells"]
cell = "".join(cells[6]["source"])
assert "MIKA_LAYER = True\n" in cell
old_core = (HERE / "mika_layer_core_v10b.py").read_text()
new_core = (HERE / "mika_layer_core_v10c.py").read_text()
compile(new_core, "core", "exec")
b_old = base64.b64encode(old_core.encode()).decode()
assert cell.count(b_old) == 1, "v10b core not found exactly once in cell 6"
cells[6]["source"] = [cell.replace(b_old, base64.b64encode(new_core.encode()).decode())]
head = "".join(cells[0]["source"])
old = "What we add (v10b, the core layer)"
assert head.count(old) == 1
head = head.replace(old, "What we add (v10c, the core layer and Jonathan's notes)")
k = head.index("Switch: `MIKA_LAYER`.")
head = head[:k] + (
    "v10c adds notes written by Jonathan, each said only when its situation shows up in the frames: reaching the end "
    "without winning means there is at least one objective to solve first; each direction button moves the body one step, "
    "so a press that doesn't is a mechanic; moving things follow their own pattern; things are related only if they share "
    "more than one property; a death is an unplanned reset, and lives are small pips; the step bar is a budget, measured "
    "per life and said in presses; a small far picture that touching changes is a display. ") + head[k:]
cells[0]["source"] = [head]
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "mika-duck.ipynb", "w"), indent=1)
json.dump(json.load(open(src / "kernel-metadata.json")), open(out / "kernel-metadata.json", "w"), indent=1)
print("built", out / "mika-duck.ipynb")
