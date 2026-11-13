import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { changeTypes } from "./repgap";

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
  const solvedHist = new Map<string, number>(), unsolvedHist = new Map<string, number>();
  let solved = 0, unsolved = 0, i = 0;
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const tags = changeTypes(t.train);
    const ok = stackSolves(t.train);
    const h = ok ? solvedHist : unsolvedHist; if (ok) solved++; else unsolved++;
    for (const tg of tags) h.set(tg, (h.get(tg) ?? 0) + 1);
  }
  console.log(`\n=== REPRESENTATION-GAP DIAGNOSTIC (solved ${solved}, unsolved ${unsolved}) ===`);
  console.log(`change-type frequency among UNSOLVED (what we can't yet do), with solved-rate per type:`);
  const allTypes = new Set([...solvedHist.keys(), ...unsolvedHist.keys()]);
  const rows = [...allTypes].map(t => {
    const u = unsolvedHist.get(t) ?? 0, s = solvedHist.get(t) ?? 0;
    return { t, u, s, rate: s/(s+u) };
  }).sort((a,b)=>b.u-a.u);
  for (const r of rows) console.log(`  ${String(r.u).padStart(3)} unsolved  ${String(r.s).padStart(3)} solved  (${(100*r.rate).toFixed(0)}% solve-rate)  ${r.t}`);
}
main();
