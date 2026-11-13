// runtwin.ts — twin-anchor transfer (ISOLATION_TEST lever). Lift each SOLVED
// task's program to a template tagged by 7D signature. For each UNSOLVED task,
// try ONLY the templates of its signature-twins (anchored adapt), bind to its
// palette + cmap. Does targeting by twin beat the blind morphPass?
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { Program } from "../../arc-slice/src/program";
import { lift, bind, taskFeatures, Template } from "../../arc-slice/src/morph";
import { encode, sigKey } from "./signature";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
function solveProg(train: any): Program | null {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return c.best;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return f; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return f; }
  return null;
}
function main() {
  const tasks = loadTasks(DATA);
  const sig = new Map<string,string>();          // taskId -> signature key
  const solvedProg = new Map<string, Program>(); // solved taskId -> program
  let i=0, solvedCount=0, codonOnly=0;
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[solve ${i}/${tasks.length}]\n`);
    sig.set(t.id, sigKey(encode(t.train)));
    const p = solveProg(t.train);
    if (p) { solvedProg.set(t.id, p); solvedCount++; }
    else if (solveCodon(t.train)) { codonOnly++; }   // counted solved but no liftable program
  }
  // build templates per signature from solved programs
  const bySig = new Map<string, Template[]>();
  for (const [id, prog] of solvedProg) {
    const k = sig.get(id)!;
    const tmpl: Template = { ops: lift(prog, taskFeatures(tasks.find(t=>t.id===id)!.train)), heat:1, tasks:1 };
    if (!bySig.has(k)) bySig.set(k, []); bySig.get(k)!.push(tmpl);
  }
  // unsolved tasks: try ONLY their signature-twins' templates
  let twinNew=0; const ex:string[]=[];
  for (const t of tasks) {
    if (solvedProg.has(t.id)) continue;
    if (solveCodon(t.train)) continue;             // already solved by codon
    const k = sig.get(t.id)!;
    const twins = bySig.get(k); if (!twins) continue;
    const f = taskFeatures(t.train);
    let done=false;
    for (const tmpl of twins) { for (const prog of bind(tmpl, f, 80)) { if (solves(prog, t.train)) { twinNew++; if(ex.length<16)ex.push(`  ${t.id}  <= twin`); done=true; break; } } if (done) break; }
  }
  const base = solvedCount + codonOnly;
  console.log(`\n=== TWIN-ANCHOR TRANSFER ===`);
  console.log(`base solved (program ${solvedCount} + codon ${codonOnly}) = ${base}/${tasks.length}`);
  console.log(`unsolved tasks newly solved by adapting a SOLVED TWIN's program: ${twinNew}`);
  console.log(`=> total ${base+twinNew}/${tasks.length} (${(100*(base+twinNew)/tasks.length).toFixed(1)}%)`);
  if (ex.length) console.log(ex.join("\n"));
}
main();
