// run7.ts — measure the bug-finder's contribution.
// Pipeline per task: brute1 -> swarm(with repair strategy) -> repair pass on
// the swarm's best near-miss. Count solves attributable to the bug-finder.
import * as path from "path";
import { loadTasks } from "./loader";
import { solves, applyToTest } from "./verify";
import { searchTask, bruteDepth1 } from "./search";
import { Program, fmt } from "./program";
import { repair } from "./bugfinder";
import { taskPalette } from "./transfer";
import { OPS, OP_NAMES } from "./dsl";
import { diagnose } from "./bugfinder";

const DATA = path.join(__dirname, "..", "data");
const LIMIT = Number(process.env.LIMIT ?? 400);
const RESTARTS = Number(process.env.RESTARTS ?? 6);
const STEPS = Number(process.env.STEPS ?? 400);
const USE_REPAIR = process.env.REPAIR !== "0";

function solveTask(train: any): { prog: Program; how: string } | null {
  const b1 = bruteDepth1(train);
  if (b1.bestScore === 1 && solves(b1.best, train)) return { prog: b1.best, how: "brute1" };
  // BUG-FINDER pass over single-op near-misses (shape right, colour/size wrong)
  if (USE_REPAIR) {
    const pal = taskPalette(train);
    for (const name of OP_NAMES) for (const params of OPS[name].enumerate(pal)) {
      const prog = [{ name, params }];
      if (diagnose(prog, train) === "none") continue;       // not a near-miss
      const fixed = repair(prog, train, pal);
      if (fixed && solves(fixed, train)) return { prog: fixed, how: "bugfix" };
    }
  }
  let best = b1;
  for (let i = 0; i < RESTARTS; i++) {
    const r = searchTask(train, 1337 + i * 101, STEPS);
    if (r.bestScore > best.bestScore) best = r;
    if (best.bestScore === 1) break;
  }
  if (best.bestScore === 1 && solves(best.best, train)) return { prog: best.best, how: "swarm" };
  // BUG-FINDER repair pass on the best near-miss
  if (USE_REPAIR) {
    const fixed = repair(best.best, train, taskPalette(train));
    if (fixed && solves(fixed, train)) return { prog: fixed, how: "bugfix" };
  }
  return null;
}

function main() {
  const tasks = loadTasks(DATA).slice(0, LIMIT);
  const how: Record<string, number> = {};
  let solved = 0, testOK = 0, testTot = 0; const ex: string[] = [];
  const t0 = Date.now();
  tasks.forEach((task, idx) => {
    if (idx % 100 === 0) process.stderr.write(`[${idx}/${tasks.length}]\n`);
    const r = solveTask(task.train);
    if (r) {
      solved++; how[r.how] = (how[r.how] ?? 0) + 1;
      for (const t of applyToTest(r.prog, task)) { testTot++; if (t.correct) testOK++; }
      if (r.how === "bugfix" && ex.length < 16) ex.push(`  ${task.id}  ${fmt(r.prog)}`);
    } else for (const _ of task.test) testTot++;
  });
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n=== BUG-FINDER RUN (repair ${USE_REPAIR ? "ON" : "OFF"}, ${tasks.length} tasks, ${secs}s) ===`);
  console.log(`train-solved: ${solved}/${tasks.length} (${(100*solved/tasks.length).toFixed(1)}%)   test-correct: ${testOK}/${testTot} (${(100*testOK/testTot).toFixed(1)}%)`);
  console.log(`by phase: ${JSON.stringify(how)}`);
  if (ex.length) console.log("bug-finder solves:\n" + ex.join("\n"));
}
main();
