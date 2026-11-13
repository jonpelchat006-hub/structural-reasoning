// run2.ts — roof + frustration pipeline, with A/B vs the plain baseline.
// Phases per task:  brute1 -> roof recall -> swarm (warm-started) -> frustration
// On any solve, imprint the program onto the roof so later tasks start warmer.
import * as path from "path";
import { loadTasks, Task } from "./loader";
import { solves, applyToTest } from "./verify";
import { searchTask, bruteDepth1 } from "./search";
import { Program, fmt } from "./program";
import { Roof, emptyRoof, imprint, hottest } from "./roof";
import { roofPass } from "./transfer";
import { frustrationSearch } from "./frustration";

const DATA = path.join(__dirname, "..", "data");
const LIMIT = Number(process.env.LIMIT ?? 400);
const RESTARTS = Number(process.env.RESTARTS ?? 6);
const STEPS = Number(process.env.STEPS ?? 400);
const FRUST = Number(process.env.FRUST ?? 6000);

interface Solve { prog: Program; how: string; }

function solveTask(task: Task, roof: Roof | null): Solve | null {
  const train = task.train;
  // 1) deterministic single-op
  const b1 = bruteDepth1(train);
  if (b1.bestScore === 1 && solves(b1.best, train)) return { prog: b1.best, how: "brute1" };
  // 2) roof recall (the bridge): try hot learned shapes from earlier tasks
  if (roof) {
    const r = roofPass(hottest(roof, 40), train);
    if (r) return { prog: r.prog, how: "roof" };
  }
  // 3) swarm-core search, warm-started from the roof if present
  const seeds = roof ? hottest(roof, 12) : [];
  let best = b1;
  for (let i = 0; i < RESTARTS; i++) {
    const res = searchTask(train, 1337 + i * 101, STEPS, seeds);
    if (res.bestScore > best.bestScore) best = res;
    if (best.bestScore === 1) break;
  }
  if (best.bestScore === 1 && solves(best.best, train)) return { prog: best.best, how: "swarm" };
  // 4) frustration: golden-ratio irrational burst
  const f = frustrationSearch(train, FRUST);
  if (f.bestScore === 1 && solves(f.best, train)) return { prog: f.best, how: "frustration" };
  // even if unsolved, hand back best partial so the roof can imprint its heat
  return null;
}

function pass(useRoof: boolean) {
  const tasks = loadTasks(DATA).slice(0, LIMIT);
  const roof: Roof | null = useRoof ? emptyRoof() : null;
  const how: Record<string, number> = {};
  let solved = 0, testCorrect = 0, testTotal = 0, firstHalf = 0, secondHalf = 0;
  const examples: string[] = [];
  const t0 = Date.now();
  tasks.forEach((task, idx) => {
    if (idx % 50 === 0) process.stderr.write(`[${useRoof?"roof":"base"} ${idx}/${tasks.length}]\n`);
    const r = solveTask(task, roof);
    if (r) {
      solved++; how[r.how] = (how[r.how] ?? 0) + 1;
      if (idx < tasks.length / 2) firstHalf++; else secondHalf++;
      if (roof) imprint(roof, r.prog, 1.0);
      for (const t of applyToTest(r.prog, task)) { testTotal++; if (t.correct) testCorrect++; }
      if (r.how !== "brute1" && examples.length < 14) examples.push(`  ${task.id} [${r.how}] ${fmt(r.prog)}`);
    } else {
      for (const _ of task.test) testTotal++;
      // imprint partial heat from the best swarm attempt so the roof still warms
      if (roof) { const b = bruteDepth1(task.train); if (b.bestScore > 0.3) imprint(roof, b.best, b.bestScore); }
    }
  });
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  return { label: useRoof ? "ROOF+FRUSTRATION" : "BASELINE", tasks: tasks.length, solved, how, testCorrect, testTotal, firstHalf, secondHalf, secs, examples };
}

function report(r: ReturnType<typeof pass>) {
  console.log(`\n=== ${r.label} (${r.tasks} tasks, ${r.secs}s) ===`);
  console.log(`train-solved: ${r.solved}/${r.tasks} (${(100*r.solved/r.tasks).toFixed(1)}%)   test-correct: ${r.testCorrect}/${r.testTotal} (${(100*r.testCorrect/r.testTotal).toFixed(1)}%)`);
  console.log(`by phase: ${JSON.stringify(r.how)}`);
  console.log(`solved in 1st half vs 2nd half: ${r.firstHalf} vs ${r.secondHalf}  (roof warming if 2nd > 1st on non-brute)`);
  if (r.examples.length) console.log("non-trivial solves:\n" + r.examples.join("\n"));
}

const base = pass(false);
const roof = pass(true);
report(base);
report(roof);
console.log(`\n=== DELTA: ${roof.solved - base.solved} extra tasks solved with roof+frustration ===`);
