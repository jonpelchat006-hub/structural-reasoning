// runcollapse.ts — THE compounding test. Floor-collapse: each solved composition
// is abstracted into a parameterized primitive (morph template) and banked to a
// GROWING library. On each new task, try the library FIRST (reuse). Genuine
// cross-task reuse = solved by a primitive abstracted from an EARLIER task.
// Question: does reuse RISE as the library grows (compounding) or stay ~0?
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { Program, fmt } from "../../arc-slice/src/program";
import { Templates, imprintTemplate, taskFeatures, hottestTemplates, morphPass } from "../../arc-slice/src/morph";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");

// returns the solving Program (so we can abstract/collapse it), or null
function stackSolveProg(train: any): Program | null {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return c.best;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return f; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return f; }
  return null;
}

function main() {
  const tasks = loadTasks(DATA);
  const lib: Templates = {};                 // the growing floor (generated primitives)
  let solved = 0, reuse = 0, i = 0;
  let fhReuse = 0, shReuse = 0, fhSolved = 0, shSolved = 0;
  const reuseEx: string[] = [];
  for (const t of tasks) {
    if (i % 100 === 0) process.stderr.write(`[${i}/${tasks.length}] lib=${Object.keys(lib).length}\n`);
    const half = i < tasks.length / 2;
    // 1) REUSE the floor: try primitives abstracted from EARLIER tasks
    const m = Object.keys(lib).length ? morphPass(hottestTemplates(lib, 40), t.train) : null;
    if (m) {
      solved++; reuse++; if (half) { fhReuse++; fhSolved++; } else { shReuse++; shSolved++; }
      if (reuseEx.length < 16) reuseEx.push(`  ${t.id}  REUSE ${fmt(m.prog)}`);
      imprintTemplate(lib, m.prog, taskFeatures(t.train));   // reinforce
      i++; continue;
    }
    // 2) solve from scratch; on a multi-op solve, COLLAPSE it into a new primitive
    const prog = stackSolveProg(t.train);
    if (prog) {
      solved++; if (half) fhSolved++; else shSolved++;
      imprintTemplate(lib, prog, taskFeatures(t.train));     // floor-collapse: abstract -> bank
    }
    i++;
  }
  console.log(`\n=== FLOOR-COLLAPSE COMPOUNDING TEST (${tasks.length} tasks, online) ===`);
  console.log(`library primitives generated: ${Object.keys(lib).length}`);
  console.log(`total solved: ${solved}/${tasks.length} (${(100*solved/tasks.length).toFixed(1)}%)`);
  console.log(`solved by REUSE (primitive from an earlier task): ${reuse}`);
  console.log(`reuse rate 1st half: ${(100*fhReuse/Math.max(1,fhSolved)).toFixed(1)}%  vs 2nd half: ${(100*shReuse/Math.max(1,shSolved)).toFixed(1)}%  (rising = COMPOUNDING)`);
  if (reuseEx.length) console.log("reuse solves:\n" + reuseEx.join("\n"));
  else console.log("(no cross-task reuse — ARC diversity beats it; the honest floor)");
}
main();
