// run8.ts — isolate the bug-finder: brute1 (exact) + single-op repair pass, no swarm.
import * as path from "path";
import { loadTasks } from "./loader";
import { solves, applyToTest } from "./verify";
import { bruteDepth1 } from "./search";
import { repair, diagnose } from "./bugfinder";
import { taskPalette } from "./transfer";
import { OPS, OP_NAMES } from "./dsl";
import { fmt } from "./program";

const DATA = path.join(__dirname, "..", "data");
// skip the costly object combinators in the repair enumeration (rarely the colour-repair base)
const REPAIR_OPS = OP_NAMES.filter((n) => !["selectUnique","selectMajority","mapObjects","cmap"].includes(n));

function main() {
  const tasks = loadTasks(DATA);
  let brute = 0, bugfix = 0, testOK = 0, testTot = 0; const ex: string[] = [];
  const t0 = Date.now();
  tasks.forEach((task) => {
    const b1 = bruteDepth1(task.train);
    let prog = null as any, how = "";
    if (b1.bestScore === 1 && solves(b1.best, task.train)) { prog = b1.best; how = "brute1"; }
    if (!prog) {
      const pal = taskPalette(task.train);
      outer:
      for (const name of REPAIR_OPS) for (const params of OPS[name].enumerate(pal)) {
        const p = [{ name, params }];
        if (diagnose(p, task.train) === "none") continue;
        const f = repair(p, task.train, pal);
        if (f && solves(f, task.train)) { prog = f; how = "bugfix"; break outer; }
      }
    }
    if (prog) {
      if (how === "brute1") brute++; else { bugfix++; if (ex.length < 16) ex.push(`  ${task.id}  ${fmt(prog)}`); }
      for (const t of applyToTest(prog, task)) { testTot++; if (t.correct) testOK++; }
    } else for (const _ of task.test) testTot++;
  });
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n=== BUG-FINDER ISOLATED (brute1 + repair, no swarm, ${tasks.length} tasks, ${secs}s) ===`);
  console.log(`brute1 exact: ${brute}   + bug-finder repair: ${bugfix}   = ${brute + bugfix} total`);
  console.log(`held-out TEST correct: ${testOK}/${testTot} (${(100*testOK/testTot).toFixed(1)}%)`);
  console.log("bug-finder solves:\n" + ex.join("\n"));
}
main();
