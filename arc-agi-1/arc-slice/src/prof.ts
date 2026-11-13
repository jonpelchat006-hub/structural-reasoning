import * as path from "path";
import { loadTasks } from "./loader";
import { bruteDepth1 } from "./search";
import { dims } from "./grid";
import { components } from "./objects";
const tasks = loadTasks(path.join(__dirname,"..","data"));
const rows: any[] = [];
for (const t of tasks) {
  const [r,c] = dims(t.train[0].input);
  const nObj = components(t.train[0].input, 0, "blob").length;
  const t0 = process.hrtime.bigint();
  bruteDepth1(t.train);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  rows.push({ id: t.id, ms, cells: r*c, dim:`${r}x${c}`, nObj, pairs: t.train.length });
}
rows.sort((a,b)=>b.ms-a.ms);
const total = rows.reduce((s,x)=>s+x.ms,0);
console.log(`total bruteDepth1: ${(total/1000).toFixed(1)}s over ${rows.length} tasks`);
console.log("slowest 12:");
for (const r of rows.slice(0,12)) console.log(`  ${r.id}  ${r.ms.toFixed(0)}ms  ${r.dim} (${r.cells} cells)  objs=${r.nObj}  pairs=${r.pairs}`);
console.log(`top-12 share of total: ${(100*rows.slice(0,12).reduce((s,x)=>s+x.ms,0)/total).toFixed(0)}%`);
