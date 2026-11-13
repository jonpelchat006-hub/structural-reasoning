"""run_r5.py - round 5 (Nov 1): 5a spread-out nodes in the flat-object model, 5b the sedenion bridge on quaternion nodes."""
import datetime, subprocess, sys
PY = sys.executable
C = ["--steps", "3000", "--seeds", "3", "--device", "cuda"]
parts = [
    ("r5a_base", ["qlift.py", "--syms", "free,spin,flat"]),
    ("r5a_sharp", ["qlift.py", "--syms", "free,spin,flat", "--on-shape", "--sharp", "4"]),
    ("r5b_bridge", ["qbridge.py", "--kinds", "dist,socket,socket_random"]),
]
for name, args in parts:
    print(f"{datetime.datetime.now():%H:%M} starting {name}", flush=True)
    with open(name + ".log", "w") as lo, open(name + ".err", "w") as le:
        subprocess.run([PY, "-u", args[0], *C, *args[1:], "--out", name + ".json"], stdout=lo, stderr=le)
    print(f"{datetime.datetime.now():%H:%M} done {name}", flush=True)
print(f"{datetime.datetime.now():%H:%M} all done", flush=True)
