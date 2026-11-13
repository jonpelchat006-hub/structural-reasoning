import * as path from "path";
import { loadTasks } from "./loader";
import { solveNested, solvesNested, runNested, fmtNested } from "./nested";
import { equal } from "./grid";

const DATA = path.join(__dirname, "..", "data");
const DEPTH = Number(process.env.DEPTH ?? 2);

function main() {
  const tasks = loadTasks(DATA);
  let solved = 0, nestedSolved = 0, testOK = 0, testTot = 0, i = 0; const ex: string[] = [];
  const t0 = Date.now();
  for (const task of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[d${DEPTH} ${i}/${tasks.length}]\n`);
    const prog = solveNested(task.train, DEPTH, Date.now() + 800);
    if (prog) {
      solved++;
      const isNested = prog.some((n:any)=>n.kind!=="op");
      if (isNested) { nestedSolved++; if (ex.length<16) ex.push(`  ${task.id}  ${fmtNested(prog)}`); }
      for (const t of task.test) { testTot++; const got = runNested(prog, t.input); if (t.output && got && equal(got, t.output)) testOK++; }
    } else for (const _ of task.test) testTot++;
  }
  const secs = ((Date.now()-t0)/1000).toFixed(1);
  console.log(`\n=== NESTED depth=${DEPTH} (${tasks.length} tasks, ${secs}s) ===`);
  console.log(`solved: ${solved}/${tasks.length} (${(100*solved/tasks.length).toFixed(1)}%)   of which use nesting: ${nestedSolved}   test ${testOK}/${testTot}`);
  if (ex.length) console.log("nested solves:\n" + ex.join("\n"));
}
main();
