import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { induceComplete } from "./complete";
import { induceMove } from "./induce";
import { equal } from "../../arc-slice/src/grid";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
function stackSolves(train: any): boolean {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return true;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return true; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return true; }
  return !!solveCodon(train);
}
function main() {
  const tasks = loadTasks(DATA);
  let stack=0, gen=0, mv=0, i=0, testOK=0, testTot=0; const by: Record<string,number>={}; const ex:string[]=[];
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (stackSolves(t.train)) { stack++; continue; }
    const m = induceMove(t.train);
    if (m) { mv++; for (const tt of t.test){testTot++; const g=m(tt.input); if(tt.output&&g&&equal(g,tt.output))testOK++;} continue; }
    const c = induceComplete(t.train);
    if (c) { gen++; by[c.desc]=(by[c.desc]??0)+1; if(ex.length<16)ex.push(`  ${t.id} [${c.desc}]`);
      for (const tt of t.test){testTot++; const g=c.fn(tt.input); if(tt.output&&g&&equal(g,tt.output))testOK++;} }
  }
  const total=stack+mv+gen;
  console.log(`\n=== TWO-POLE: stack(knot) + induced-move + generative completion(tail) ===`);
  console.log(`stack: ${stack}   + induced-move: ${mv}   + generative completion: ${gen}   = ${total}/${tasks.length} (${(100*total/tasks.length).toFixed(1)}%)`);
  console.log(`generative wins by rule: ${JSON.stringify(by)}`);
  if (ex.length) console.log("generative completion solves:\n"+ex.join("\n"));
}
main();
