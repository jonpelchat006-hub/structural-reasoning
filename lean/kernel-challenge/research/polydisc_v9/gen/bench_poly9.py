#!/usr/bin/env python3
"""Replay-window instruction bench for polydisc (as bench_fib.py): builds SUBMISSION in a scratch copy
of problems/polydisc, makes the judge's `Submission.impl n = v` theorem per n, exports it and counts the
timer kernel's measured window under callgrind. usage: bench_poly.py SUBMISSION.lean n [n ...]"""
import json, os, shutil, subprocess, sys
sys.set_int_max_str_digits(0)
from pathlib import Path
ROOT = Path("/home/claude/lkc")
sys.path.insert(0, str(ROOT / "evaluation" / "judge"))
import reference_answers as ref
WORK = Path(os.environ.get("BENCH_WORK", "/home/claude/polywork2"))
TIMER_VG = Path("/home/claude/timer-vg/.lake/build/bin/kernel")
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))

def window(exp, tag):
    out = f"/tmp/pw2_{os.path.basename(str(WORK))}_{tag}.out"
    for f in Path("/tmp").glob(f"pw2_{os.path.basename(str(WORK))}_{tag}.out*"): f.unlink()
    subprocess.run(["valgrind", "--tool=callgrind", "--collect-atstart=no", f"--callgrind-out-file={out}",
                    str(TIMER_VG), "--count-instructions", "--target", "Bench.check", str(exp)],
                   capture_output=True, text=True, timeout=7200, env=ENV)
    for f in sorted(Path("/tmp").glob(f"pw2_{os.path.basename(str(WORK))}_{tag}.out.*")):
        txt = f.read_text()
        if "replay-window" in txt:
            for l in txt.splitlines():
                if l.startswith("summary:"): return int(l.split()[1]), f
    raise RuntimeError("no window dump")

def rhs(v):
    return (f"Lean.mkApp (Lean.mkConst ``Int.negSucc) (Lean.mkNatLit {-v - 1})" if v < 0
            else f"Lean.mkApp (Lean.mkConst ``Int.ofNat) (Lean.mkNatLit {v})")

def measure(n, tag):
    v = ref.compute_answer("polydisc", n)
    (WORK / "Perf.lean").write_text(
        "import Submission\nimport Lean\nset_option maxRecDepth 4000000\nset_option maxHeartbeats 0\n"
        "open Lean Meta Elab in\nrun_meta do\n"
        f"  let lhs := Lean.mkApp (Lean.mkConst ``Submission.impl) (Lean.mkNatLit {n})\n"
        f"  let rhs := {rhs(v)}\n  let ty ← mkEq lhs rhs\n  let pf ← mkEqRefl rhs\n"
        "  Lean.addDecl (.thmDecl { name := `Bench.check, levelParams := [], type := ty, value := pf })\n")
    r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/Perf.olean", "Perf.lean"], cwd=WORK,
                       capture_output=True, text=True, timeout=3600, env=ENV)
    if r.returncode: raise RuntimeError(f"build n={n}: {r.stdout[-800:]} {r.stderr[-800:]}")
    exp = WORK / f"perf_{tag}.ndjson"
    with open(exp, "w") as f:
        r = subprocess.run(["lake", "env", str(EXPORT), "Perf", "--", "Bench.check"], cwd=WORK, stdout=f,
                           stderr=subprocess.PIPE, text=True, timeout=3600, env=ENV)
    if r.returncode: raise RuntimeError(f"export n={n}: {r.stderr[-800:]}")
    return window(exp, tag)

def main():
    sub, ns = Path(sys.argv[1]).resolve(), [int(a) for a in sys.argv[2:]]
    if not WORK.exists():
        shutil.copytree(ROOT / "problems" / "polydisc", WORK)
    shutil.copy(sub, WORK / "Submission.lean")
    r = subprocess.run(["lake", "build", "Submission"], cwd=WORK, capture_output=True, text=True, env=ENV)
    if r.returncode: print(r.stdout[-3000:]); sys.exit(1)
    res = {}
    for n in ns:
        res[n], f = measure(n, str(n))
        print(f"n={n}: {res[n]:,}  ({f})", flush=True)
    print("JSON " + json.dumps({"sub": str(sub), "ir": res, "total": sum(res.values())}))

if __name__ == "__main__":
    main()
