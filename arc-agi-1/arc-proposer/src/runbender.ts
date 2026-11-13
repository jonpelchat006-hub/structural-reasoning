import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bend } from "./bender";
import { fmt } from "../../arc-slice/src/program";
const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
function main() {
  const tasks = loadTasks(DATA);
  let solved = 0, deep = 0, i = 0; const ex: string[] = [];
  const t0 = Date.now();
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const r = bend(t.train, Date.now() + 350);
    if (r) { solved++; if (r.depth >= 2) { deep++; if (ex.length < 18) ex.push(`  ${t.id} (d${r.depth}) ${fmt(r.prog)}`); } }
  }
  const secs = ((Date.now()-t0)/1000).toFixed(1);
  console.log(`\n=== TENSION BEAM BENDER (no model, ${tasks.length} tasks, ${secs}s) ===`);
  console.log(`solved (pure structure): ${solved}/${tasks.length} (${(100*solved/tasks.length).toFixed(1)}%)`);
  console.log(`of which depth>=2 (composed/bent): ${deep}`);
  if (ex.length) console.log("composed solves:\n" + ex.join("\n"));
}
main();
