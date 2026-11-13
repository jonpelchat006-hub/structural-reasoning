// run10.ts — isolate the NEW combinators' contribution (with bug-finder).
// For each task, test the combinator family as a base op, exact AND repaired.
import * as path from "path";
import { loadTasks } from "./loader";
import { solves } from "./verify";
import { repair, diagnose } from "./bugfinder";
import { taskPalette } from "./transfer";
import { OPS } from "./dsl";
import { fmt } from "./program";

const DATA = path.join(__dirname, "..", "data");
const FAM = ["keepTopK","mapTopK","selectUnique","selectMajority","mapObjects"];

function main() {
  const tasks = loadTasks(DATA);
  let exact = 0, repaired = 0; const ex: string[] = [];
  const t0 = Date.now();
  let i = 0;
  for (const task of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const pal = taskPalette(task.train);
    let hitExact = false, hitRep: any = null;
    outer:
    for (const name of FAM) for (const params of OPS[name].enumerate(pal)) {
      const prog = [{ name, params }];
      if (solves(prog, task.train)) { hitExact = true; break outer; }
      if (diagnose(prog, task.train) !== "none") {
        const f = repair(prog, task.train, pal);
        if (f && solves(f, task.train)) { hitRep = f; break outer; }
      }
    }
    if (hitExact) exact++;
    else if (hitRep) { repaired++; if (ex.length < 16) ex.push(`  ${task.id}  ${fmt(hitRep)}`); }
  }
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n=== NEW COMBINATORS isolated (${tasks.length} tasks, ${secs}s) ===`);
  console.log(`combinator exact solves: ${exact}`);
  console.log(`combinator + bug-finder solves: ${repaired}`);
  console.log("examples:\n" + ex.join("\n"));
}
main();
