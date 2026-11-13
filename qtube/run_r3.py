"""run_r3.py - round 3 (Nov 1): mirror turns + the river map. Stops starting new parts after 11:38 local
(Mika's ARC daily runs at 11:52)."""
import datetime, subprocess, sys
PY = sys.executable
C = ["--near", "7", "--nkind", "move", "--flips", "1-1", "--device", "cuda", "--seeds", "3", "--save-dir", "models_r3"]
parts = [
    ("r3_rotmirror_m4", ["--split", "rotmirror", "--mirror-turns", "4", "--kinds", "quat,nested_fit,nested_loss,nested_random", "--steps-list", "1000,3000"]),
    ("r3_rotmirror_m0", ["--split", "rotmirror", "--mirror-turns", "0", "--kinds", "real,quat,nested_fit,nested_loss,nested_random", "--steps-list", "1000,3000"]),
    ("r3_quarter_m4", ["--split", "quarter", "--mirror-turns", "4", "--kinds", "quat,nested_fit,nested_random", "--steps-list", "3000"]),
    ("r3_quarter_m0", ["--split", "quarter", "--mirror-turns", "0", "--kinds", "nested_fit", "--steps-list", "3000"]),
]
for name, args in parts:
    now = datetime.datetime.now()
    if (now.hour, now.minute) >= (11, 38):
        print(f"{now:%H:%M} skipping {name} (too close to Mika's daily)", flush=True); continue
    print(f"{now:%H:%M} starting {name}", flush=True)
    with open(name + ".log", "w") as lo, open(name + ".err", "w") as le:
        subprocess.run([PY, "-u", "qtest.py", *C, *args, "--out", name + ".json"], stdout=lo, stderr=le)
    print(f"{datetime.datetime.now():%H:%M} done {name}", flush=True)
print(f"{datetime.datetime.now():%H:%M} starting rivers", flush=True)
with open("rivers_r3.log", "w") as lo, open("rivers_r3.err", "w") as le:
    subprocess.run([PY, "-u", "rivers.py", "--dir", "models_r3", "--device", "cuda", "--out", "rivers_r3.json"], stdout=lo, stderr=le)
print(f"{datetime.datetime.now():%H:%M} all done", flush=True)
