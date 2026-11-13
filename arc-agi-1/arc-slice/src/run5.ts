// run5.ts — distinguish genuine cross-task TRANSFER from self-recall.
// Build templates with their SOURCE task ids. Then for each task, try only
// templates that were learned from a DIFFERENT task (leave-one-out). A solve
// under that rule is the bridge actually carrying structure between problems.
import * as path from "path";
import { loadTasks } from "./loader";
import { solves } from "./verify";
import { searchTask, bruteDepth1 } from "./search";
import { Program } from "./program";
import { lift, keyOf, taskFeatures, bind, Template } from "./morph";

const DATA = path.join(__dirname, "..", "data");
const LIMIT = Number(process.env.LIMIT ?? 400);
const RESTARTS = Number(process.env.RESTARTS ?? 5);
const STEPS = Number(process.env.STEPS ?? 300);

function swarmSolve(train: any): Program | null {
  let best = bruteDepth1(train);
  if (best.bestScore === 1 && solves(best.best, train)) return best.best;
  for (let i = 0; i < RESTARTS; i++) { const r = searchTask(train, 1337 + i*101, STEPS); if (r.bestScore > best.bestScore) best = r; if (best.bestScore === 1) break; }
  return best.bestScore === 1 && solves(best.best, train) ? best.best : null;
}

interface Entry { ops: Template["ops"]; sources: Set<string>; heat: number; }

function main() {
  const tasks = loadTasks(DATA).slice(0, LIMIT);
  const T: Record<string, Entry> = {};

  // build templates with source-task tracking
  tasks.forEach((task, idx) => {
    if (idx % 100 === 0) process.stderr.write(`[build ${idx}/${tasks.length}]\n`);
    const b1 = bruteDepth1(task.train);
    const prog = (b1.bestScore === 1 && solves(b1.best, task.train)) ? b1.best : swarmSolve(task.train);
    if (!prog) return;
    if (prog.filter((o)=>o.name!=="identity").length < 2) return;
    const ops = lift(prog, taskFeatures(task.train));
    const k = keyOf(ops);
    if (!T[k]) T[k] = { ops, sources: new Set(), heat: 0 };
    T[k].sources.add(task.id); T[k].heat++;
  });

  const all = Object.values(T);
  const multi = all.filter((e) => e.sources.size > 1);
  console.log(`\n=== TRANSFER DIAGNOSTIC (ARC-1, ${tasks.length} tasks) ===`);
  console.log(`multi-op templates: ${all.length}`);
  console.log(`templates seen in >1 task (shared skeletons): ${multi.length}`);

  // leave-one-out morph: solve task X using only templates from OTHER tasks
  let transfer = 0; const hits: string[] = [];
  for (const task of tasks) {
    const f = taskFeatures(task.train);
    const usable = all.filter((e) => [...e.sources].some((s) => s !== task.id));
    for (const e of usable.sort((a,b)=>b.heat-a.heat).slice(0, 40)) {
      let done = false;
      for (const prog of bind({ ops: e.ops, heat: e.heat, tasks: e.sources.size }, f)) {
        if (solves(prog, task.train)) { transfer++; hits.push(`  ${task.id}  <= template from {${[...e.sources].filter(s=>s!==task.id).join(",")}}`); done = true; break; }
      }
      if (done) break;
    }
  }
  console.log(`\nGENUINE cross-task transfer solves (leave-one-out): ${transfer}`);
  if (hits.length) console.log(hits.slice(0, 20).join("\n"));
  else console.log("(none — every multi-op solution skeleton is unique to its task)");
}
main();
