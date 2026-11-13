"""Bounded real-engine contact learning and verified goal-directed execution.

--bootstrap active probes controls and discovers an object/display from fresh
frames. --goal visible --navigate-goal selects a visible target hypothesis and
tests it against engine level completion. The original demonstration bootstrap
and observed-start goal remain available as scoped diagnostics. Body extraction,
visual hypothesis classes and geometric laws are supplied priors. No game
implementation is inspected and no LLM is used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import torch

from qmoments import QuaternionMoments
from qrecording import load_demo, find_bootstrap, load_observation_core
from qtransition import ContactPoseRule, plan_contacts, same_mask, mask_json
from qscene import detect_goal_candidates, select_unambiguous, discover_state_display
from qnav import learn_motion, plan_to_box
from qbudget import infer_budget


ROOT = Path(__file__).resolve().parents[1]


def serial_prediction(value):
    if value is None:
        return None
    return {k: mask_json(v) if k == "mask" else [mask_json(m) for m in v]
            if k == "possible_masks" else v for k, v in value.items()}


class EngineClient:
    def __init__(self, python, game, output):
        self.output = output
        self.log = (output / "transitions.jsonl").open("w", encoding="utf-8")
        self.err = (output / "engine_stderr.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(python), "-u", str(ROOT / "qtube/qengine_rpc.py"), "--game", game],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err,
            text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.last = self._read()
        if not self.last.get("ready"):
            raise RuntimeError(f"Engine initialization failed: {self.last}")
        self.frames = [np.asarray(self.last["frame"], dtype=np.int16)]
        self.actions = []
        self.write({"phase": "initial", "observation": self.last})
        self.closed = False

    def _read(self):
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Offline engine exited; inspect engine_stderr.log")
        value = json.loads(line)
        if value.get("ok") is False:
            raise RuntimeError(f"Offline engine error: {value}")
        return value

    def write(self, value):
        self.log.write(json.dumps(value) + "\n")
        self.log.flush()

    def step(self, action, *, phase, prediction=None):
        # This record is flushed before the environment receives the action.
        self.write({"phase": "prediction", "step": len(self.actions) + 1,
                    "purpose": phase, "action": int(action), "prediction": prediction})
        request = {"action": int(action), "data": {}}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        self.last = self._read()
        self.actions.append(int(action))
        self.frames.append(np.asarray(self.last["frame"], dtype=np.int16))
        self.write({"phase": "observation", "step": len(self.actions), "purpose": phase,
                    "action": int(action), "observation": self.last})
        return self.frames[-1]

    def close(self):
        if self.closed:
            return None
        self.closed = True
        result = None
        try:
            self.process.stdin.write(json.dumps({"command": "close"}) + "\n")
            self.process.stdin.flush()
            result = self._read()
            self.write({"phase": "scorecard", "result": result})
        finally:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=10)
            self.log.close()
            self.err.close()
            np.savez_compressed(self.output / "frames_actions.npz", F=np.stack(self.frames),
                                A=np.asarray(self.actions, dtype=np.int16))
        return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--bootstrap", choices=("demo", "active"), default="demo")
    ap.add_argument("--demo-frames", type=Path, default=ROOT / "eye/play_ls20.npz")
    ap.add_argument("--demo-actions", type=Path, default=ROOT / "eye/play_ls20.jsonl")
    ap.add_argument("--region", default="auto",
                    help="auto discovers a changing panel from observed demo frames; or y0,y1,x0,x1.")
    ap.add_argument("--discovery-frames", type=int, default=32)
    ap.add_argument("--source-dir", type=Path,
                    default=ROOT / "kaggle_push/out_gemma_26b_qtube_v1/planet")
    ap.add_argument("--engine-python", type=Path, default=ROOT / "arc3/venv/Scripts/python.exe")
    ap.add_argument("--checkpoint", type=Path,
                    default=ROOT / "qtube/models_r6_ports_clean/dist_s0.pt")
    ap.add_argument("--holdout", type=int, default=4)
    ap.add_argument("--fit-steps", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--goal", choices=("observed-start", "visible"), default="observed-start")
    ap.add_argument("--navigate-goal", action="store_true",
                    help="After matching a visible target, execute a verified local approach and test entry.")
    ap.add_argument("--out", type=Path, default=ROOT / "qtube/game_loop_ls20_s0")
    args = ap.parse_args()
    if args.holdout < 0 or args.fit_steps < 1 or args.discovery_frames < 2:
        ap.error("Supply nonnegative holdout count and positive fit/discovery sizes.")
    if args.navigate_goal and args.goal != "visible":
        ap.error("--navigate-goal requires --goal visible")
    if args.out.exists():
        ap.error("Output directory already exists; choose a new --out to preserve the previous run.")
    args.out.mkdir(parents=True)
    torch.set_num_threads(2)
    started = time.perf_counter()
    core = load_observation_core(args.source_dir)
    demo_frames = demo_actions = bootstrap = region = None
    discovery = None
    if args.bootstrap == "demo":
        demo_frames, demo_actions = load_demo(args.demo_frames, args.demo_actions, args.source_dir)
        if args.region == "auto":
            discovery = discover_state_display(demo_frames[:args.discovery_frames], body_pos=core.body_pos)
            if discovery["region"] is None:
                ap.error("Observed frames do not identify one changing display; provide more observations or --region.")
            region = tuple(discovery["region"])
        else:
            region = tuple(map(int, args.region.split(",")))
            if len(region) != 4:
                ap.error("--region requires auto or four comma-separated values")
        bootstrap = find_bootstrap(demo_frames, demo_actions, region, core=core)
    encoder = QuaternionMoments.from_checkpoint(args.checkpoint)
    rule = ContactPoseRule(encoder, name="observed-contact", seed=args.seed)
    client = None
    summary = {"schema_version": 1, "game": args.game, "seed": args.seed,
               "status": "running", "priors": {
                   "navigation": "Replay observed route, then use empirically witnessed inverse displacement.",
                   "perception": "Supplied observed HUD crop and existing glyph/body extractors.",
                   "geometry": "D4 group and quaternion/moment transformation laws; frozen synthetic encoder.",
                   "goal": "Return to pre-contact observed glyph; supplied experiment goal, not game objective.",
                   "learning": "Contact effect learned from first two fresh engine transitions only."},
               "holdout": [], "plan_execution": []}
    summary["bootstrap_mode"] = args.bootstrap
    summary["display_discovery"] = discovery
    summary["priors"]["perception"] = (
        "Existing body/enclosure extractors; changing display inferred from demonstration observations."
        if discovery is not None else "Supplied observed HUD crop and existing glyph/body extractors.")
    summary["goal_mode"] = args.goal
    summary["navigation_execution"] = []
    if args.goal == "visible":
        summary["priors"]["goal"] = (
            "Select one visible enclosed glyph with compatible shape/colour as a target hypothesis; "
            "only the engine's level completion confirms it.")
    summary["evaluation_protocol"] = (
        "Development/regression experiment on one shape orbit; the fitting method "
        "was revised after a failed pilot. Frozen evaluation does not establish "
        "new-shape, new-mechanic or new-game generalization.")
    try:
        client = EngineClient(args.engine_python, args.game, args.out)
        if args.bootstrap == "active":
            from qbootstrap import active_bootstrap
            bootstrap = active_bootstrap(client, core)
            discovery = bootstrap["display_discovery"]
            region = tuple(discovery["region"])
            summary["display_discovery"] = discovery
            summary["object_candidates"] = bootstrap.get("object_candidates")
            summary["priors"]["navigation"] = (
                "Probe available controls; infer movement/floor; approach one small enclosed foreground island.")
            summary["priors"]["perception"] = (
                "Existing body/enclosure/island extractors; changing display inferred from fresh live frames.")
        else:
            if not np.array_equal(client.frames[0], demo_frames[0]):
                raise RuntimeError("Fresh initial frame differs from the observation demo; abstain from replay.")
            for i, action in enumerate(bootstrap["prefix"]):
                if int(action["a"]) == 6:
                    raise RuntimeError("Click navigation is not supported by this first contact-loop runner.")
                frame = client.step(action["a"], phase="demonstration_bootstrap")
                if not np.array_equal(frame, demo_frames[i + 1]):
                    raise RuntimeError(f"Demo diverged at action {i + 1}; no inferred route is trusted.")
        summary.update(region=list(region), bootstrap_event_index=bootstrap["event_index"],
                       bootstrap_actions=len(bootstrap["prefix"]), incoming_action=bootstrap["incoming_action"],
                       reverse_action=bootstrap["reverse_action"], reverse_evidence=bootstrap["reverse_evidence"])
        colour, mask = core.read_glyph(client.frames[-1], region)
        target = bootstrap["before_glyph"][1].copy()
        initial_colour = bootstrap["before_glyph"][0]
        if colour != initial_colour:
            raise RuntimeError("Bootstrap includes recoloring; this experiment isolates pose changes.")
        target_hypothesis = None
        if args.goal == "visible":
            position = core.body_pos(client.frames[-1])
            body_box = [position[0], position[1], position[0] + 4, position[1] + 4] if position else None
            candidates = detect_goal_candidates(client.frames[-1], (colour, mask),
                                                hud_region=region, body_box=body_box)
            target_hypothesis = select_unambiguous(candidates)
            summary["target_candidates"] = [{**c, "glyph": [c["glyph"][0], mask_json(c["glyph"][1])]}
                                             for c in candidates]
            if target_hypothesis is None:
                raise RuntimeError("No unambiguous compatible visible target hypothesis; abstain.")
            target = target_hypothesis["glyph"][1].copy()
            initial_colour = target_hypothesis["glyph"][0]
            summary["selected_target"] = {**target_hypothesis,
                "glyph": [initial_colour, mask_json(target)]}
        event = rule.observe(bootstrap["before_glyph"][1], mask, steps=args.fit_steps,
                             provenance={"fresh_engine_step": len(client.actions), "phase": "acquisition"})
        client.write({"phase": "learning", "event": event})
        incoming, reverse = bootstrap["incoming_action"], bootstrap["reverse_action"]
        contact_body, away_body = tuple(bootstrap["target_body"]), tuple(bootstrap["source_body"])
        fixed_level = client.last["levels_completed"]

        def contact(phase):
            before_colour, before = core.read_glyph(client.frames[-1], region)
            prediction = rule.predict(before)
            # Moving away is a separate action whose lack of glyph effect is checked.
            frame = client.step(reverse, phase=phase + ":step_off",
                                prediction={"glyph_unchanged": mask_json(before)})
            if (client.last["levels_completed"] != fixed_level
                    or client.last["state"] != "NOT_FINISHED" or client.last.get("full_reset")):
                raise RuntimeError("Episode/level boundary after stepping off; do not send the return action.")
            off_colour, off = core.read_glyph(frame, region)
            if (off_colour != before_colour or not same_mask(off, before)
                    or tuple(core.body_pos(frame) or ()) != away_body):
                raise RuntimeError("Observed reverse movement/contact gate changed; revise navigation model.")
            frame = client.step(incoming, phase=phase + ":contact",
                                prediction=serial_prediction(prediction))
            after_colour, after = core.read_glyph(frame, region)
            if (client.last["levels_completed"] != fixed_level
                    or client.last["state"] != "NOT_FINISHED" or client.last.get("full_reset")):
                raise RuntimeError("Episode/level boundary invalidates this within-level contact rule.")
            if tuple(core.body_pos(frame) or ()) != contact_body:
                raise RuntimeError("The action no longer reaches the observed contact location.")
            if after_colour != before_colour:
                raise RuntimeError("Contact changes colour; represent this outside quaternion pose.")
            row = {"step": len(client.actions), "prediction": serial_prediction(prediction),
                   "observed_mask": mask_json(after),
                   "correct": prediction is not None and same_mask(prediction["mask"], after),
                   "identity_baseline_correct": same_mask(before, after)}
            client.write({"phase": "verification", "purpose": phase, **row})
            return before, after, row

        # A second distinct source pose can resolve rotation/reflection aliasing.
        before, after, acquisition_prediction = contact("acquisition")
        event = rule.observe(before, after, steps=args.fit_steps,
                             provenance={"fresh_engine_step": len(client.actions), "phase": "acquisition"})
        client.write({"phase": "learning", "event": event})
        summary["acquisition_prediction"] = acquisition_prediction
        summary["support_after_two_contacts"] = sorted(rule.support)
        training_reconstructed = []
        for source, expected in rule.examples:
            prediction = rule.predict(source)
            training_reconstructed.append(bool(prediction is not None
                and prediction["verified"] and same_mask(prediction["mask"], expected)))
        summary["training_fit_gate"] = {"pose_loss": rule.fit_loss,
            "tolerance": 1e-6, "all_acquired_transitions_reconstructed": all(training_reconstructed)}
        if not rule.fit_ok or not all(training_reconstructed):
            raise RuntimeError("Acquired transitions do not fit; abstain before frozen evaluation/planning.")
        selected_holdout = args.holdout
        if args.navigate_goal:
            budget = infer_budget(client.frames)
            motion = learn_motion(client.frames, client.actions, core.body_pos)
            approach = plan_to_box(client.frames[-1], core.body_pos(client.frames[-1]),
                                   target_hypothesis["box"], motion)
            if approach is None:
                raise RuntimeError("No visible route; conserve the remaining action budget.")
            current = core.read_glyph(client.frames[-1], region)[1]
            options = []
            for count in range(args.holdout, -1, -1):
                simulated = current.copy()
                for _ in range(count):
                    prediction = rule.predict(simulated)
                    if prediction is None or not prediction["verified"]:
                        break
                    simulated = prediction["mask"]
                else:
                    remaining_plan = plan_contacts(simulated, target, {rule.name: rule})
                    if remaining_plan is not None:
                        actions_needed = 2 * count + 2 * len(remaining_plan) + len(approach)
                        options.append({"frozen_checks": count, "actions_needed": actions_needed,
                                        "affordable": budget.can_afford(actions_needed, reserve=1)})
            viable = [o for o in options if o["affordable"]]
            summary["budget_before_plan"] = budget.to_dict()
            summary["budget_options"] = options
            if not viable:
                raise RuntimeError("Observed action budget cannot cover a supported plan plus reserve.")
            selected_holdout = viable[0]["frozen_checks"]
        summary["requested_holdout"] = args.holdout
        summary["selected_holdout"] = selected_holdout
        for _ in range(selected_holdout):
            before, after, row = contact("frozen_holdout")
            summary["holdout"].append(row)
            if not row["correct"]:
                rule.contradictions += 1
                rule.support.clear()
                raise RuntimeError("Frozen next-pose prediction failed; invalidate law before planning.")
        current_colour, current = core.read_glyph(client.frames[-1], region)
        plan = plan_contacts(current, target, {rule.name: rule}, max_depth=8)
        summary["planned_contacts"] = plan
        if plan is None:
            raise RuntimeError("Evidence/model cannot produce a supported plan; abstain.")
        for _ in plan:
            before, after, row = contact("planned_execution")
            summary["plan_execution"].append(row)
            if not row["correct"]:
                rule.contradictions += 1
                rule.support.clear()
                raise RuntimeError("Plan prediction contradicted observation; stop and revise.")
        colour, result = core.read_glyph(client.frames[-1], region)
        summary.update(status="complete", experimental_goal_reached=bool(
            colour == initial_colour and same_mask(result, target)),
            game_levels_completed=client.last["levels_completed"],
            game_state=client.last["state"],
            holdout_accuracy=(float(np.mean([r["correct"] for r in summary["holdout"]]))
                              if summary["holdout"] else None),
            identity_baseline_accuracy=(float(np.mean([
                r["identity_baseline_correct"] for r in summary["holdout"]]))
                if summary["holdout"] else None))
        if args.navigate_goal:
            if not summary["experimental_goal_reached"]:
                raise RuntimeError("Pose plan did not match the visible target; do not navigate to it.")
            motion = learn_motion(client.frames, client.actions, core.body_pos)
            summary["motion_hypothesis"] = motion
            position = core.body_pos(client.frames[-1])
            route = plan_to_box(client.frames[-1], position, target_hypothesis["box"], motion)
            summary["navigation_plan"] = route
            if route is None:
                raise RuntimeError("No route under the observed floor/movement model; abstain.")
            budget = infer_budget(client.frames)
            summary["budget_before_navigation"] = budget.to_dict()
            if not budget.can_afford(len(route), reserve=1):
                raise RuntimeError("Remaining budget no longer covers navigation plus reserve.")
            reached_level = False
            for step in route:
                if tuple(core.body_pos(client.frames[-1]) or ()) != tuple(step["from"]):
                    raise RuntimeError("Body position disagrees with navigation plan; replan required.")
                frame = client.step(step["action"], phase="visible_goal_navigation",
                    prediction={"body": step["to"], "glyph": mask_json(target),
                                "target_entry_is_unverified_probe": step["target_probe"]})
                row = {**step, "observed_body": core.body_pos(frame),
                       "levels_completed": client.last["levels_completed"], "state": client.last["state"]}
                summary["navigation_execution"].append(row)
                if client.last["levels_completed"] > fixed_level:
                    reached_level = True
                    break
                if (client.last["state"] != "NOT_FINISHED" or client.last.get("full_reset")
                        or client.last["levels_completed"] != fixed_level):
                    raise RuntimeError("Unexpected episode boundary during navigation.")
                observed = core.read_glyph(frame, region)
                if (observed is None or observed[0] != initial_colour
                        or not same_mask(observed[1], target)):
                    raise RuntimeError("Navigation changed the glyph; revise contact/effect model.")
                if tuple(row["observed_body"] or ()) != tuple(step["to"]):
                    raise RuntimeError("Predicted movement was blocked or changed; revise local route.")
            summary.update(game_goal_confirmed=reached_level,
                           game_levels_completed=client.last["levels_completed"],
                           game_state=client.last["state"])
            if not reached_level:
                raise RuntimeError("Candidate box entry did not complete a level; goal hypothesis unconfirmed.")
    except Exception as error:
        summary.update(status="failed", error=f"{type(error).__name__}: {error}")
    finally:
        if client is not None:
            summary["actions"] = len(client.actions)
            try:
                summary["scorecard"] = client.close()
            except Exception as error:
                summary["close_error"] = f"{type(error).__name__}: {error}"
                summary["status"] = "failed"
        summary["rule"] = rule.summary()
        summary["seconds"] = round(time.perf_counter() - started, 3)
        (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out.resolve()), "status": summary["status"],
        "bootstrap": args.bootstrap, "region": summary.get("region"),
        "actions": summary.get("actions"), "levels": summary.get("game_levels_completed"),
        "goal_confirmed": summary.get("game_goal_confirmed"),
        "frozen_checks": len(summary["holdout"]),
        "frozen_correct": sum(r["correct"] for r in summary["holdout"]),
        "planned_contacts": len(summary.get("planned_contacts") or []),
        "seconds": summary["seconds"], "error": summary.get("error")}), flush=True)
    if summary["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
