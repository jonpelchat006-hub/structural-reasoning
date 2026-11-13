// run.ts — end-to-end baseline: load -> brute depth-1 -> swarm restarts -> verify.
import * as path from "path";
import { loadTasks } from "./loader";
import { solves, applyToTest } from "./verify";
import { searchTask, bruteDepth1, SearchOut } from "./search";
import { Program, fmt } from "./program";

const DATA = path.join(__dirname, "..", "data");
const LIMIT = Number(process.env.LIMIT ?? 400);
const RESTARTS = Number(process.env.RESTARTS ?? 6);
const STEPS = Number(process.env.STEPS ?? 400);

function solveTask(train: any[]): { prog: Program; how: string } | null {
  // 1) deterministic single-op pass
  const b1 = bruteDepth1(train);
  if (b1.bestScore === 1 && solves(b1.best, train)) return { prog: b1.best, how: "brute1" };
  // 2) swarm-core search with random restarts (compositions)
  let best: SearchOut = b1;
  for (let r = 0; r < RESTARTS; r++) {
    const res = searchTask(train, 1337 + r * 101, STEPS);
    if (res.bestScore > best.bestScore) best = res;
    if (best.bestScore === 1) break;
  }
  if (best.bestScore === 1 && solves(best.best, train)) return { prog: best.best, how: "swarm" };
  return null;
}

function main() {
  const tasks = loadTasks(DATA).slice(0, LIMIT);
  let trainSolved = 0, brute = 0, swarm = 0, testCorrect = 0, testTotal = 0;
  const examples: string[] = [];
  const t0 = Date.now();
  for (const task of tasks) {
    const r = solveTask(task.train);
    if (r) {
      trainSolved++;
      if (r.how === "brute1") brute++; else swarm++;
      const tests = applyToTest(r.prog, task);
      for (const t of tests) { testTotal++; if (t.correct) testCorrect++; }
      if (examples.length < 12) examples.push(`  ${task.id}  [${r.how}]  ${fmt(r.prog)}`);
    } else {
      for (const _ of task.test) testTotal++;
    }
  }
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n=== ARC-AGI-1 training baseline (${tasks.length} tasks, ${secs}s) ===`);
  console.log(`train-solved (rule fits ALL train pairs): ${trainSolved}/${tasks.length}  (${(100*trainSolved/tasks.length).toFixed(1)}%)`);
  console.log(`   via brute depth-1: ${brute}   via swarm-core search: ${swarm}`);
  console.log(`held-out TEST correct (generalised): ${testCorrect}/${testTotal}  (${(100*testCorrect/testTotal).toFixed(1)}%)`);
  console.log(`\nsample solved rules:`);
  console.log(examples.join("\n"));
}
main();
