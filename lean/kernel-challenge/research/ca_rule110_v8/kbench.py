#!/usr/bin/env python3
"""Count kernel instructions inside the judge's replay window (callgrind), for any problem.

usage: kbench.py PROBLEM TAG SUBMISSION.lean [n1,n2,...]   (IMPL=name to time another definition)
Builds SUBMISSION in a scratch copy of the fixed workspace (/home/claude/bench/TAG), then for each
input builds the judge's theorem `impl n = v := Eq.refl v`, exports it, and replays it with the
callgrind build of the judge's timer kernel. Prints one count per input and the total.
With no inputs: the default public plan (group endpoints, or seeds 1 and 2 at each scale).
"""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.set_int_max_str_digits(0)
ROOT = Path("/home/claude/lkc_src/repo")
sys.path.insert(0, str(ROOT / "evaluation" / "judge"))
import reference_answers as ref  # noqa: E402

TIMER_VG = Path("/home/claude/timer-vg/.lake/build/bin/kernel")
EXPORT = Path("/home/claude/lkc_src/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))


def default_inputs(problem):
    cfg = json.loads((ROOT / f"evaluation/problems/{problem}/config.json").read_text())
    out = []
    for g in cfg["evaluation"]["groups"]:
        s = g["sampling"]
        if s["kind"] == "packed":
            out += [ref.packed(s["scale"], seed) for seed in (1, 2)]
        elif "min" in s:
            out += [s["min"], s["max"]]
        else:
            lo, hi = s.get("range", s.get("bounds"))
            out += [lo, hi]
    return out


def rhs(v, out_is_int):
    if v < 0:
        return f"Lean.mkApp (Lean.mkConst ``Int.negSucc) (Lean.mkNatLit {-v - 1})"
    if out_is_int:
        return f"Lean.mkApp (Lean.mkConst ``Int.ofNat) (Lean.mkNatLit {v})"
    return f"Lean.mkNatLit {v}"


def main():
    problem, tag, sub = sys.argv[1], sys.argv[2], Path(sys.argv[3]).resolve()
    ns = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else default_inputs(problem)
    impl = os.environ.get("IMPL", "impl")
    work = Path("/home/claude/bench") / tag
    if not work.exists():
        shutil.copytree(ROOT / "evaluation/problems" / problem, work, symlinks=True)
    shutil.copy(sub, work / "Submission.lean")
    r = subprocess.run(["lake", "build", "Submission"], cwd=work, capture_output=True, text=True, env=ENV)
    if r.returncode:
        print(r.stdout[-4000:], r.stderr[-2000:]); sys.exit(1)
    out_is_int = ref.OUTPUT_TYPES[problem] == "Int"
    perf = ["import Submission", "import Lean", "set_option maxRecDepth 4000000", "set_option maxHeartbeats 0",
            "open Lean Meta Elab in", "run_meta do"]
    for i, n in enumerate(ns):
        v = ref.compute_answer(problem, n)
        perf += [f"  Lean.addDecl (.thmDecl {{ name := `Bench.m{i}, levelParams := [], "
                 f"type := ← mkEq (Lean.mkApp (Lean.mkConst ``Submission.{impl}) (Lean.mkNatLit {n})) ({rhs(v, out_is_int)}), "
                 f"value := ← mkEqRefl ({rhs(v, out_is_int)}) }})"]
    (work / "PerfM.lean").write_text("\n".join(perf) + "\n")
    r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/PerfM.olean", "PerfM.lean"], cwd=work,
                       capture_output=True, text=True, timeout=7200, env=ENV)
    if r.returncode:
        print("PERF BUILD FAIL", r.stdout[-3000:], r.stderr[-2000:]); sys.exit(1)

    def one(i):
        exp = work / f"pm_{i}.ndjson"
        with open(exp, "w") as f:
            subprocess.run(["lake", "env", str(EXPORT), "PerfM", "--", f"Bench.m{i}"], cwd=work, stdout=f,
                           stderr=subprocess.PIPE, text=True, timeout=3600, env=ENV)
        cg = f"/tmp/pm_{tag}_{i}.out"
        for g in Path("/tmp").glob(f"pm_{tag}_{i}.out*"):
            g.unlink()
        rr = subprocess.run(["valgrind", "--tool=callgrind", "--collect-atstart=no", f"--callgrind-out-file={cg}",
                             str(TIMER_VG), "--count-instructions", "--target", f"Bench.m{i}", str(exp)],
                            capture_output=True, text=True, timeout=7200, env=ENV)
        total = None
        for g in Path("/tmp").glob(f"pm_{tag}_{i}.out.*"):
            t = g.read_text(errors="ignore")
            if "replay-window" in t:
                for l in t.splitlines():
                    if l.startswith("summary:"):
                        total = int(l.split()[1])
            g.unlink()
        if total is None:
            print("REPLAY FAIL", ns[i], rr.stdout[-600:], rr.stderr[-600:])
        exp.unlink()
        return ns[i], total

    res = {}
    with ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "2"))) as ex:
        for n, t in ex.map(one, range(len(ns))):
            res[n] = t
            print(f"  n={n}: {t:,}" if t is not None else f"  n={n}: FAIL", flush=True)
    tot = sum(v for v in res.values() if v)
    print(f"TOTAL {tag}: {tot:,}")
    if os.environ.get("OUT"):
        json.dump({str(k): v for k, v in res.items()}, open(os.environ["OUT"], "w"), indent=1)


if __name__ == "__main__":
    main()
