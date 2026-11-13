#!/usr/bin/env python3
"""Compare kernel declaration-check wall time; NOT official instruction scoring.

Run in a scratch Lake package containing Submission and Baseline modules.
Both modules must have impl and impl_correct in their corresponding namespaces.
Uses organizer reference answers and kernel-checked Eq.refl declarations, never #eval.
"""
import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation/judge"))
import reference_answers as ref


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("problem")
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--inputs", type=int, nargs="+")
    ap.add_argument("--repeats", type=int, default=7)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error("--repeats must be positive")
    work = args.workspace.resolve()
    source_names = ("Submission.lean", "Baseline.lean", "Spec.lean")
    def source_hashes():
        return {name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                for name in source_names}
    hashes = source_hashes()
    # Never time stale .olean imports while reporting hashes of newer source files.
    build = subprocess.run(["lake", "build", "Submission", "Baseline"], cwd=work,
                           capture_output=True, text=True, encoding="utf-8", timeout=600)
    if build.returncode:
        print(build.stdout)
        print(build.stderr, file=sys.stderr)
        raise SystemExit(build.returncode)
    inputs = args.inputs
    if not inputs:
        cfg = json.loads((ROOT / "evaluation/problems" / args.problem / "config.json").read_text())
        inputs = []
        for group in cfg["evaluation"]["groups"]:
            sampling = group["sampling"]
            if sampling["kind"] == "packed":
                inputs.extend(ref.packed(sampling["scale"], seed) for seed in (1, 2))
            else:
                inputs.extend((sampling["min"], sampling["max"]))
    source = ["import Submission", "import Baseline", "import Lean",
              "set_option maxRecDepth 4000000", "set_option maxHeartbeats 0",
              "#print axioms Submission.impl_correct", "#print axioms Baseline.impl_correct",
              "open Lean Meta Elab in", "run_meta do"]
    cases = []
    for n in inputs:
        value = ref.compute_answer(args.problem, n)
        if ref.OUTPUT_TYPES[args.problem] == "Int":
            ctor, magnitude = ("Int.negSucc", -value - 1) if value < 0 else ("Int.ofNat", value)
            rhs = f"mkApp (mkConst ``{ctor}) (mkNatLit {magnitude})"
        else:
            rhs = f"mkNatLit {value}"
        cases.append(f"({n}, {rhs})")
    source.extend([
        "  let cases : List (Nat × Expr) := [" + ", ".join(cases) + "]",
        "  let env := (← getEnv).toKernelEnv",
        "  for (n, rhs) in cases do",
        f"    for rep in [: {args.repeats}] do",
        "      let order := if rep % 2 == 0 then [`Baseline, `Submission] else [`Submission, `Baseline]",
        "      for ns in order do",
        "        let lhs := mkApp (mkConst (ns ++ `impl)) (mkNatLit n)",
        "        let ty ← mkEq lhs rhs",
        "        let pf ← mkEqRefl rhs",
        '        let name := Name.str ns s!"bench{n}r{rep}"',
        "        let decl := Declaration.thmDecl { name, levelParams := [], type := ty, value := pf }",
        "        let start ← IO.monoNanosNow",
        "        match env.addDeclCore 0 4000000 decl none with",
        "        | .error ex => throwError (ex.toMessageData {})",
        "        | .ok checked =>",
        "          unless (checked.find? name).isSome do",
        '            throwError "checked declaration missing"',
        "        let stop ← IO.monoNanosNow",
        '        IO.println s!"SAMPLE {ns} {n} {rep} {stop - start}"',
    ])
    (work / "V3Bench.lean").write_text("\n".join(source) + "\n", encoding="utf-8")
    result = subprocess.run(["lake", "env", "lean", "V3Bench.lean"], cwd=work,
                            capture_output=True, text=True, encoding="utf-8", timeout=600)
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    samples = {}
    for line in result.stdout.splitlines():
        if line.startswith("SAMPLE "):
            _, ns, n, repeat, nanos = line.split()
            samples.setdefault(n, {}).setdefault(ns, []).append(int(nanos))
    rows = []
    for n, values in samples.items():
        medians = {ns: statistics.median(times) for ns, times in values.items()}
        rows.append({"n": int(n), "samples_ns": values, "median_ns": medians,
                     "candidate_over_baseline": medians["Submission"] / medians["Baseline"]})
    if set(samples) != {str(n) for n in inputs} or any(
        set(values) != {"Submission", "Baseline"}
        or any(len(times) != args.repeats for times in values.values())
        for values in samples.values()
    ):
        raise RuntimeError("incomplete benchmark samples; refusing to publish a result")
    if source_hashes() != hashes:
        raise RuntimeError("source files changed during build/timing; refusing to publish a result")
    version = subprocess.run(["lean", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    report = {"problem": args.problem, "metric": "local Windows synchronous Kernel.Environment.addDeclCore wall time, not official score",
              "lean_version": version, "source_sha256": hashes,
              "repeats": args.repeats, "cases": rows, "stdout": result.stdout,
              "preflight_build": build.stdout + build.stderr}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(row["n"], f'candidate/baseline={row["candidate_over_baseline"]:.3f}')


if __name__ == "__main__":
    main()
