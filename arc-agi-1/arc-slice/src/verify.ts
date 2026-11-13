// verify.ts — the oracle. This is sandbox-runner's engine specialised to ARC:
// each train pair is a SandboxJob {input, expected}; the candidate program is
// the Runner; score = mean exact-cell match; solved = every pair matches fully.
import { Program, run } from "./program";
import { Task, Pair } from "./loader";
import { cellMatch, equal } from "./grid";

/** Smooth score in [0,1] for the search to climb (1.0 only if every pair is exact). */
export function score(prog: Program, train: Pair[]): number {
  let sum = 0;
  for (const { input, output } of train) {
    const got = run(prog, input);
    sum += got ? cellMatch(got, output) : 0; // dims mismatch / illegal -> 0 for that pair
  }
  return sum / train.length;
}

/** Hard pass: every training pair reproduced exactly. */
export function solves(prog: Program, train: Pair[]): boolean {
  for (const { input, output } of train) {
    const got = run(prog, input);
    if (!got || !equal(got, output)) return false;
  }
  return true;
}

/** Apply a solved rule to the held-out test input(s). */
export function applyToTest(prog: Program, task: Task) {
  return task.test.map((t) => {
    const got = run(prog, t.input);
    const correct = t.output ? (got != null && equal(got, t.output)) : null;
    return { got, correct };
  });
}
