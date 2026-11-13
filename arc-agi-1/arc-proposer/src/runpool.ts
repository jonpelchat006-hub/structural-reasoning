// runpool.ts — compatibility pooling. Route each task by features to a small
// compatible op pool (loaded), search it UNDILUTED, swap to broader pool if
// exhausted. Tests whether un-diluting past the cap beats the all-ops 73.
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { OP_NAMES } from "../../arc-slice/src/dsl";
import { background } from "../../arc-slice/src/grid";
import { components } from "../../arc-slice/src/objects";
import { panels } from "../../arc-slice/src/ops-panel";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");

const SAME = ["identity","recolor","swap","keepColor","removeColor","cmap","fillHoles","fillObjHoles","symmetrize","completeSym","gravity","gravityObj","mapObjects","mapTopK","paintRank","colorByShape","outline","connect","denoise","keepTouching","shift","flipH","flipV","rotate","transpose"];
const SMALLER = ["crop","trim","cropToColor","largest","keepLargest","keepSmallest","keepRare","keepCommon","selectUnique","selectMajority","keepTopK","half","oddPanel","majPanel","panelBy","combinePanels","overlayPanels","overlayHalves","cmap","downscale"];
const BIGGER = ["scale","tile","fractal","mirrorConcat","drawRays","grow","cross","addBorder","stamp","cmap"];

function pool(train: any): string[] {
  const dimsEq = train.every((p:any)=>p.input.length===p.output.length && p.input[0].length===p.output[0].length);
  const szIn = train.reduce((s:number,p:any)=>s+p.input.length*p.input[0].length,0);
  const szOut = train.reduce((s:number,p:any)=>s+p.output.length*p.output[0].length,0);
  const set = new Set<string>(["identity","cmap"]);
  if (dimsEq) SAME.forEach(o=>set.add(o));
  else if (szOut < szIn) SMALLER.forEach(o=>set.add(o));
  else BIGGER.forEach(o=>set.add(o));
  // structural add-ons
  if (panels(train[0].input, background(train[0].input))) ["oddPanel","majPanel","panelBy","combinePanels","overlayPanels"].forEach(o=>set.add(o));
  return [...set].filter(o=>OP_NAMES.includes(o));
}

function solveWith(train:any, names:string[]): boolean {
  const c = bruteCandidates(train, names);
  if (c.bestScore===1 && solves(c.best,train)) return true;
  const pal=taskPalette(train);
  for (const cand of c.colorCands) { const f=colorMapRepair(cand,train); if(f&&solves(f,train)) return true; }
  for (const cand of [...c.colorCands.slice(0,24), ...c.sizeCands]) { const f=sizeRepair(cand,train,pal); if(f&&solves(f,train)) return true; }
  return false;
}

function main() {
  const tasks = loadTasks(DATA);
  let pooled=0, fullOnly=0, codon=0, i=0;
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (solveWith(t.train, pool(t.train))) { pooled++; continue; }      // tight pool first
    if (solveWith(t.train, OP_NAMES)) { fullOnly++; continue; }          // fallback: all ops
    if (solveCodon(t.train)) { codon++; }
  }
  console.log(`\n=== COMPATIBILITY POOLING ===`);
  console.log(`solved by tight pool: ${pooled}   + needed full-op fallback: ${fullOnly}   + codon: ${codon}`);
  console.log(`= ${pooled+fullOnly+codon}/${tasks.length} (${(100*(pooled+fullOnly+codon)/tasks.length).toFixed(1)}%)`);
  console.log(`(pooled/${pooled+fullOnly} = ${(100*pooled/Math.max(1,pooled+fullOnly)).toFixed(0)}% of program-solves came from the small loaded pool)`);
}
main();
