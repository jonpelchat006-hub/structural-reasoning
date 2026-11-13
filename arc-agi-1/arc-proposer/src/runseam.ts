// runseam.ts — full stack + seam-typed repair; report new solves + seam histogram.
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { classifySeam, seamRepair } from "./seam";
import { fmt } from "../../arc-slice/src/program";

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
  let stack = 0, seamNew = 0, i = 0; const seamHist = new Map<string, number>(); const ex: string[] = [];
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (stackSolves(t.train)) { stack++; continue; }
    // unsolved -> try seam-typed repair on the near-miss candidates
    const c = bruteCandidates(t.train);
    let solvedHere: any = null;
    for (const cand of [c.best, ...c.colorCands.slice(0,20)]) {
      const seam = classifySeam(cand, t.train);
      seamHist.set(seam, (seamHist.get(seam) ?? 0) + 1);
      if (seam === "uniform_offset" || seam === "spike") { const f = seamRepair(cand, t.train); if (f) { solvedHere = f; break; } }
    }
    if (solvedHere) { seamNew++; if (ex.length < 16) ex.push(`  ${t.id}  ${fmt(solvedHere)}`); }
  }
  console.log(`\n=== SEAM-TYPED REPAIR (${tasks.length} tasks) ===`);
  console.log(`stack solved: ${stack}   + seam-repair NEW: ${seamNew}   = ${stack + seamNew}/${tasks.length} (${(100*(stack+seamNew)/tasks.length).toFixed(1)}%)`);
  console.log(`seam shapes seen on unsolved near-misses: ${JSON.stringify(Object.fromEntries(seamHist))}`);
  if (ex.length) console.log("seam solves:\n" + ex.join("\n"));
}
main();
