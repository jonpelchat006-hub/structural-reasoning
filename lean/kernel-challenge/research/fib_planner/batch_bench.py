#!/usr/bin/env python3
"""Price many fib plans in one go: one module with a chain per plan (`cand<i>`), one Perf file with a
theorem per (plan, n), then one export and one callgrind replay-window count per theorem.

usage: batch_bench.py OUT.json   (plans and inputs are chosen in `candidates()` below)
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.set_int_max_str_digits(0)
sys.path.insert(0, str(Path(__file__).parent))
import planner as pl

WORK = Path("/home/claude/lkc/problems/fib")
TIMER_VG = Path("/home/claude/timer-vg/.lake/build/bin/kernel")
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))
REP = {13: 5375, 14: 9250, 15: 21500, 16: 37000, 17: 86000, 18: 140000}


def window(exp, tag):
    out = f"/tmp/bb_{tag}.out"
    for f in Path("/tmp").glob(f"bb_{tag}.out*"): f.unlink()
    subprocess.run(["valgrind", "--tool=callgrind", "--collect-atstart=no", f"--callgrind-out-file={out}",
                    str(TIMER_VG), "--count-instructions", "--target", tag, str(exp)],
                   capture_output=True, text=True, timeout=3600, env=ENV)
    for f in Path("/tmp").glob(f"bb_{tag}.out.*"):
        txt = f.read_text()
        if "replay-window" in txt:
            for l in txt.splitlines():
                if l.startswith("summary:"): return int(l.split()[1])
    return None


def run(cands, out_json, module_name="Cands"):
    """cands: list of (plan, n). Writes the module, builds it, measures each."""
    src = [pl.HEADER]
    for i, (p, n) in enumerate(cands):
        src.append(pl.emit(p, f"cand{i}"))
    src.append("end Submission\n")
    (WORK / f"{module_name}.lean").write_text("\n".join(src))
    # the lakefile only builds Spec/Submission: put the candidates in Submission (not submitted)
    (WORK / "Submission.lean").write_text("\n".join(src))
    r = subprocess.run(["lake", "build", "Submission"], cwd=WORK, capture_output=True, text=True, env=ENV)
    if r.returncode: print(r.stdout[-3000:]); sys.exit(1)
    perf = ["import Submission", "import Lean", "set_option maxRecDepth 4000000", "set_option maxHeartbeats 0",
            "open Lean Meta Elab in", "run_meta do"]
    for i, (p, n) in enumerate(cands):
        v = pl.fib_pair(n)[0]
        perf += [f"  Lean.addDecl (.thmDecl {{ name := `Bench.c{i}, levelParams := [], "
                 f"type := ← mkEq (Lean.mkApp (Lean.mkConst ``Submission.cand{i}) (Lean.mkNatLit {n})) (Lean.mkNatLit {v}), "
                 f"value := ← mkEqRefl (Lean.mkNatLit {v}) }})"]
    (WORK / "PerfB.lean").write_text("\n".join(perf) + "\n")
    t0 = time.time()
    r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/PerfB.olean", "PerfB.lean"], cwd=WORK,
                       capture_output=True, text=True, timeout=7200, env=ENV)
    if r.returncode: print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
    print(f"elaborated {len(cands)} theorems in {time.time() - t0:.0f}s", flush=True)

    def one(i):
        exp = WORK / f"pb_{i}.ndjson"
        with open(exp, "w") as f:
            subprocess.run(["lake", "env", str(EXPORT), "PerfB", "--", f"Bench.c{i}"], cwd=WORK,
                           stdout=f, stderr=subprocess.PIPE, text=True, timeout=3600, env=ENV)
        w = window(exp, f"Bench.c{i}")
        exp.unlink()
        return i, w
    res = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        for i, w in ex.map(one, range(len(cands))):
            p, n = cands[i]
            res[i] = {"plan": p.name(), "L": p.L, "t": p.t, "P": p.P, "c": p.c, "fin": p.fin, "n": n, "ir": w}
            if i % 10 == 0: print(i, res[i]["plan"], n, w, flush=True)
    Path(out_json).write_text(json.dumps(list(res.values()), indent=1))
    return res


def candidates():
    out = []
    for L in range(13, 19):
        for p in pl.plans_for(L):
            if p.c in (0, p.P - 2, p.P - 1, p.P) or p.fin in "CA":
                out.append((p, REP[L]))
    return out


if __name__ == "__main__":
    cands = candidates()
    print(len(cands), "candidates", flush=True)
    run(cands, sys.argv[1])
