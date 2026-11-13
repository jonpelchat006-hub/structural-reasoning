// run6.ts — rigorous leave-one-out transfer test, now TRANSFORM-AWARE.
// For each task, use only templates learned from OTHER tasks, and try each
// template both directly AND conjugated by every D4 symmetry (the quaternion
// angle-difference). Report transfers, and how many are NET-new (a task NOT
// already solvable by the deterministic single-op pass).
import * as path from "path";
import { loadTasks } from "./loader";
import { solves } from "./verify";
import { searchTask, bruteDepth1 } from "./search";
import { Program } from "./program";
import { lift, keyOf, taskFeatures, bind, Template } from "./morph";
import { D4_ALL, conjugate, d4Label } from "./qtransform";

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
  const bruteSolvable = new Set<string>();

  tasks.forEach((task, idx) => {
    if (idx % 100 === 0) process.stderr.write(`[build ${idx}/${tasks.length}]\n`);
    const b1 = bruteDepth1(task.train);
    if (b1.bestScore === 1 && solves(b1.best, task.train)) bruteSolvable.add(task.id);
    const prog = (b1.bestScore === 1 && solves(b1.best, task.train)) ? b1.best : swarmSolve(task.train);
    if (!prog || prog.filter((o)=>o.name!=="identity").length < 2) return;
    const ops = lift(prog, taskFeatures(task.train));
    const k = keyOf(ops);
    if (!T[k]) T[k] = { ops, sources: new Set(), heat: 0 };
    T[k].sources.add(task.id); T[k].heat++;
  });

  const all = Object.values(T);
  let exact = 0, viaTransform = 0, netNew = 0;
  const hits: string[] = [];
  for (const task of tasks) {
    const f = taskFeatures(task.train);
    const usable = all.filter((e) => [...e.sources].some((s) => s !== task.id)).sort((a,b)=>b.heat-a.heat).slice(0,40);
    let solved = false, usedG = "", src = "";
    outer:
    for (const e of usable) {
      const tpl: Template = { ops: e.ops, heat: e.heat, tasks: e.sources.size };
      for (const prog of bind(tpl, f, 60)) {
        for (const g of D4_ALL) {
          const cand = conjugate(prog, g);
          if (solves(cand, task.train)) { solved = true; usedG = d4Label(g); src = [...e.sources].filter(s=>s!==task.id)[0]; break outer; }
        }
      }
    }
    if (solved) {
      if (usedG === "rot0") exact++; else viaTransform++;
      if (!bruteSolvable.has(task.id)) netNew++;
      if (hits.length < 24) hits.push(`  ${task.id}  <= ${src}  [${usedG}]${bruteSolvable.has(task.id)?"":"  *NET-NEW*"}`);
    }
  }
  console.log(`\n=== TRANSFORM-AWARE TRANSFER (ARC-1, ${tasks.length} tasks) ===`);
  console.log(`multi-op templates: ${all.length}`);
  console.log(`leave-one-out transfer solves: ${exact + viaTransform}   (exact: ${exact}, via D4 transform: ${viaTransform})`);
  console.log(`of which NET-NEW (not single-op solvable): ${netNew}`);
  console.log(hits.join("\n") || "(none)");
}
main();
