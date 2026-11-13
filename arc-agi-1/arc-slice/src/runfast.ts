import * as path from "path";
import { loadTasks } from "./loader";
import { solves, applyToTest } from "./verify";
import { bruteCandidates } from "./search";
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { taskPalette } from "./transfer";
import { fmt } from "./program";

const DATA = path.join(__dirname, "..", "data");
const K = Number(process.env.K ?? 10);

function main() {
  const tasks = loadTasks(DATA);
  let exact = 0, fixed = 0, testOK = 0, testTot = 0, i = 0; const ex: string[] = [];
  const t0 = Date.now();
  for (const task of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const c = bruteCandidates(task.train);
    let prog: any = null, tag = "";
    if (c.bestScore === 1 && solves(c.best, task.train)) { prog = c.best; tag = "exact"; }
    if (!prog) {
      const pal = taskPalette(task.train);
      // cheap broad colour repair
      for (const cand of c.colorCands) { const f = colorMapRepair(cand, task.train); if (f && solves(f, task.train)) { prog = f; tag = "repair"; break; } }
      // bounded size repair on the most promising candidates (size op +/- colour)
      if (!prog) { const sizeTargets = [...c.colorCands.slice(0,24), ...c.sizeCands]; // dims-guided -> cheap
        for (const cand of sizeTargets) { const f = sizeRepair(cand, task.train, pal); if (f && solves(f, task.train)) { prog = f; tag = "repair"; break; } } }
    }
    if (prog) { if (tag === "exact") exact++; else { fixed++; if (ex.length < 14) ex.push(`  ${task.id} ${fmt(prog)}`); }
      for (const t of applyToTest(prog, task)) { testTot++; if (t.correct) testOK++; } }
    else for (const _ of task.test) testTot++;
  }
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n=== FAST DETERMINISTIC (no swarm, no guards, ${tasks.length} tasks, ${secs}s) ===`);
  console.log(`solved: ${exact + fixed}/${tasks.length} (${(100*(exact+fixed)/tasks.length).toFixed(1)}%)  [exact ${exact} + repair ${fixed}]   test ${testOK}/${testTot}`);
  console.log("repair solves:\n" + ex.join("\n"));
}
main();
