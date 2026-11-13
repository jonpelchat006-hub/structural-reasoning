import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves, applyToTest } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
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
  let stack = 0, induced = 0, i = 0, testOK = 0, testTot = 0; const ex: string[] = [];
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (stackSolves(t.train)) { stack++; continue; }
    const fn = induceMove(t.train);
    if (fn) { induced++; if (ex.length<16) ex.push(`  ${t.id}`); 
      for (const tt of t.test) { testTot++; const got=fn(tt.input); if (tt.output && got && equal(got,tt.output)) testOK++; } }
  }
  console.log(`\n=== INDUCED-MOVE (operator induction) ===`);
  console.log(`stack: ${stack}   + induced-move NEW: ${induced}   = ${stack+induced}/${tasks.length} (${(100*(stack+induced)/tasks.length).toFixed(1)}%)`);
  console.log(`induced-move test correct: ${testOK}/${testTot}`);
  if (ex.length) console.log("induced-move solves:\n" + ex.join("\n"));
}
main();
