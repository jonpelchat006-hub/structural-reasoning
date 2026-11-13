"""Fresh, complete, corpus-identified offline evaluation results.

The final report is replaced only after every selected recording succeeds.
Progress/failure is stored separately; it is never a completed score.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from uuid import uuid4

from arc3_preflight import manifest


def atomic_json(path, value):
    path = Path(path)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as out:
            tmp = Path(out.name)
            json.dump(value, out, indent=1, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def run_batch(directory, output, runner, *, games=None, run_id=None):
    report = manifest(directory)
    valid = [r for r in report["records"] if r["valid"]]
    if games is not None:
        wanted = set(games)
        found = {Path(r["path"]).stem for r in valid}
        if not wanted or wanted - found:
            raise ValueError(f"requested games absent or invalid: {sorted(wanted - found)}")
        valid = [r for r in valid if Path(r["path"]).stem in wanted]
    if not valid:
        raise ValueError("no valid transition recordings; evaluation cannot be scored")
    signature = sorted((Path(r["path"]).name, r["sha256"]) for r in valid)
    corpus_id = hashlib.sha256(json.dumps(signature).encode()).hexdigest()
    output = Path(output)
    progress = output.with_name(output.name + ".progress.json")
    results = {"schema": "induction-batch-v2", "run_id": run_id or uuid4().hex,
               "corpus_id": corpus_id, "status": "running", "started": time.strftime("%Y-%m-%d %H:%M:%S"),
               "expected_games": [Path(r["path"]).stem for r in valid], "manifest": valid,
               "rejected": [r for r in report["records"] if not r["valid"]], "games": {}}
    atomic_json(progress, results)
    try:
        for record in valid:
            name = Path(record["path"]).stem
            # Refuse an input changed after its manifest was built.
            if hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"recording changed during evaluation: {name}")
            value = runner(name, record["path"])
            if not isinstance(value, dict):
                raise ValueError(f"no evaluation result for {name}")
            if hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"recording changed during evaluation: {name}")
            results["games"][name] = value
            atomic_json(progress, results)
        results.update(status="complete", finished=time.strftime("%Y-%m-%d %H:%M:%S"))
        atomic_json(output, results)
        atomic_json(progress, results)
        return results
    except Exception as e:
        results.update(status="failed", error=f"{type(e).__name__}: {e}")
        atomic_json(progress, results)
        raise


def validate_completed(result, run_id):
    if (result.get("schema") != "induction-batch-v2" or result.get("status") != "complete"
            or result.get("run_id") != run_id or not result.get("corpus_id")):
        raise ValueError("stale, incompatible, or incomplete induction report")
    if not result.get("expected_games") or set(result["games"]) != set(result["expected_games"]):
        raise ValueError("induction report does not cover its expected corpus")
    return result


def practice_verdict(practice, history, margin=5):
    """Compare only complete evaluations of exactly the same recorded corpus."""
    if practice.get("status") != "complete":
        return None, "FAILED"
    comparable = [h["practice"]["wins"] for h in history if h.get("practice")
                  and h["practice"].get("status") == "complete"
                  and h["practice"].get("agent") == practice.get("agent")
                  and h["practice"].get("corpus_id") == practice.get("corpus_id")]
    baseline = max(comparable, default=None)
    if baseline is None: return None, "first-baseline"
    wins = practice["wins"]
    return baseline, ("improved" if wins > baseline else "same" if wins == baseline
                      else "noise" if wins >= baseline - margin else "REGRESSED")
