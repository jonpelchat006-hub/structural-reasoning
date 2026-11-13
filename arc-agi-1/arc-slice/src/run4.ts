// run4.ts — morph (corkscrew) experiment.
//  Epoch 1: solve with brute1 + swarm, lifting every multi-op solution into the
//           template roof (colors abstracted to role-slots).
//  Epoch 2: re-solve, but try MORPH (bind templates into each task's language)
//           BEFORE swarm. Any task solved by morph here used a template learned
//           from a DIFFERENT task -> that is genuine cross-task transfer.
import * as path from "path";
import { loadTasks, Task } from "./loader";
import { solves, applyToTest } from "./verify";
import { searchTask, bruteDepth1 } from "./search";
import { Program, fmt } from "./program";
import { Templates, imprintTemplate, taskFeatures, hottestTemplates, morphPass } from "./morph";

const DATA = path.join(__dirname, "..", "data");
const LIMIT = Number(process.env.LIMIT ?? 400);
const RESTARTS = Number(process.env.RESTARTS ?? 5);
const STEPS = Number(process.env.STEPS ?? 300);

function swarmSolve(train: Task["train"]): Program | null {
  let best = bruteDepth1(train);
  if (best.bestScore === 1 && solves(best.best, train)) return best.best;
  for (let i = 0; i < RESTARTS; i++) {
    const r = searchTask(train, 1337 + i * 101, STEPS);
    if (r.bestScore > best.bestScore) best = r;
    if (best.bestScore === 1) break;
  }
  return best.bestScore === 1 && solves(best.best, train) ? best.best : null;
}

function main() {
  const tasks = loadTasks(DATA).slice(0, LIMIT);
  const T: Templates = {};

  // ── Epoch 1: build the template roof ──
  let e1 = 0;
  const t0 = Date.now();
  tasks.forEach((task, idx) => {
    if (idx % 100 === 0) process.stderr.write(`[epoch1 ${idx}/${tasks.length}]\n`);
    const b1 = bruteDepth1(task.train);
    let prog: Program | null = (b1.bestScore === 1 && solves(b1.best, task.train)) ? b1.best : swarmSolve(task.train);
    if (prog) { e1++; imprintTemplate(T, prog, taskFeatures(task.train)); }
  });
  const nTemplates = Object.keys(T).length;

  // ── Epoch 2: brute1 -> MORPH(roof) -> swarm ──
  let brute = 0, morph = 0, swarm = 0, morphFirst = 0, morphSecond = 0, testOK = 0, testTot = 0;
  const examples: string[] = [];
  tasks.forEach((task, idx) => {
    if (idx % 100 === 0) process.stderr.write(`[epoch2 ${idx}/${tasks.length}]\n`);
    const b1 = bruteDepth1(task.train);
    let prog: Program | null = null, how = "";
    if (b1.bestScore === 1 && solves(b1.best, task.train)) { prog = b1.best; how = "brute1"; }
    if (!prog) { const m = morphPass(hottestTemplates(T, 30), task.train); if (m) { prog = m.prog; how = "morph"; } }
    if (!prog) { const s = swarmSolve(task.train); if (s) { prog = s; how = "swarm"; } }
    if (prog) {
      if (how === "brute1") brute++; else if (how === "morph") { morph++; if (idx < tasks.length/2) morphFirst++; else morphSecond++; } else swarm++;
      for (const t of applyToTest(prog, task)) { testTot++; if (t.correct) testOK++; }
      if (how === "morph" && examples.length < 16) examples.push(`  ${task.id} [morph] ${fmt(prog)}`);
    } else { for (const _ of task.test) testTot++; }
  });
  const total = brute + morph + swarm;
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n=== MORPH EXPERIMENT (ARC-1, ${tasks.length} tasks, ${secs}s) ===`);
  console.log(`epoch-1 solved: ${e1}   templates learned (len>=2 shapes): ${nTemplates}`);
  console.log(`epoch-2 solved: ${total}/${tasks.length} (${(100*total/tasks.length).toFixed(1)}%)`);
  console.log(`  brute1: ${brute}   MORPH (cross-task transfer): ${morph}   swarm: ${swarm}`);
  console.log(`  morph solves 1st-half vs 2nd-half: ${morphFirst} vs ${morphSecond}`);
  console.log(`held-out TEST correct: ${testOK}/${testTot} (${(100*testOK/testTot).toFixed(1)}%)`);
  if (examples.length) console.log("morph (transferred) solves:\n" + examples.join("\n"));
}
main();
