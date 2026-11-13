// run11.ts — unified DETERMINISTIC pipeline (no swarm), deduplicated.
// base op (exact) -> base op + bug-finder -> combinator (exact) -> combinator + bug-finder
import * as path from "path";
import { loadTasks } from "./loader";
import { solves, applyToTest } from "./verify";
import { repair, diagnose } from "./bugfinder";
import { taskPalette } from "./transfer";
import { OPS, OP_NAMES } from "./dsl";
import { fmt } from "./program";

const DATA = path.join(__dirname, "..", "data");
const COMBO = new Set(["keepTopK","mapTopK","selectUnique","selectMajority","mapObjects","cmap"]);
const BASE = OP_NAMES.filter((n) => !COMBO.has(n));
const COMBOS = ["keepTopK","mapTopK","selectUnique","selectMajority","mapObjects"];

function trySet(names: string[], train: any, withRepair: boolean) {
  const pal = taskPalette(train);
  for (const name of names) for (const params of OPS[name].enumerate(pal)) {
    const prog = [{ name, params }];
    if (solves(prog, train)) return prog;
    if (withRepair && diagnose(prog, train) !== "none") {
      const f = repair(prog, train, pal); if (f && solves(f, train)) return f;
    }
  }
  return null;
}

function main() {
  const tasks = loadTasks(DATA);
  const how: Record<string, number> = { base:0, baseRepair:0, combo:0, comboRepair:0 };
  let solved = 0, testOK = 0, testTot = 0, i = 0; const newOnes: string[] = [];
  const t0 = Date.now();
  for (const task of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const big = task.train.some((pp:any)=>pp.input.length*pp.input[0].length>400);
    let prog: any = null, tag = "";
    prog = trySet(BASE, task.train, false); if (prog) tag = "base";
    if (!prog && !big) { prog = trySet(BASE, task.train, true); if (prog) tag = "baseRepair"; }
    if (!prog && !big) { prog = trySet(COMBOS, task.train, false); if (prog) tag = "combo"; }
    if (!prog && !big) { prog = trySet(COMBOS, task.train, true); if (prog) tag = "comboRepair"; }
    if (prog) {
      solved++; how[tag]++;
      if ((tag === "combo" || tag === "comboRepair") && newOnes.length < 20) newOnes.push(`  ${task.id} [${tag}] ${fmt(prog)}`);
      for (const t of applyToTest(prog, task)) { testTot++; if (t.correct) testOK++; }
    } else for (const _ of task.test) testTot++;
  }
  const secs = ((Date.now() - t0)/1000).toFixed(1);
  console.log(`\n=== UNIFIED DETERMINISTIC (no swarm, ${tasks.length} tasks, ${secs}s) ===`);
  console.log(`TOTAL solved: ${solved}/${tasks.length} (${(100*solved/tasks.length).toFixed(1)}%)   test-correct: ${testOK}/${testTot} (${(100*testOK/testTot).toFixed(1)}%)`);
  console.log(`breakdown: ${JSON.stringify(how)}`);
  console.log(`solved via combinators (beyond base+bugfinder):\n${newOnes.join("\n")}`);
}
main();
