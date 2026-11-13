import * as path from "path";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES } from "./dsl";
import { repair, diagnose } from "./bugfinder";
import { taskPalette } from "./transfer";
import { dims } from "./grid";
const tasks = loadTasks(path.join(__dirname,"..","data"));
const rows:any[]=[];
for (const t of tasks) {
  const pal = taskPalette(t.train);
  const t0 = process.hrtime.bigint();
  for (const name of OP_NAMES) for (const params of OPS[name].enumerate(pal)) {
    const prog=[{name,params}];
    if (diagnose(prog,t.train)!=="none") repair(prog,t.train,pal);
  }
  const ms = Number(process.hrtime.bigint()-t0)/1e6;
  const [r,c]=dims(t.train[0].input);
  rows.push({id:t.id,ms,dim:`${r}x${c}`});
}
rows.sort((a,b)=>b.ms-a.ms);
const total=rows.reduce((s,x)=>s+x.ms,0);
console.log(`total repair pass: ${(total/1000).toFixed(1)}s`);
console.log("slowest 12:");
for (const r of rows.slice(0,12)) console.log(`  ${r.id} ${r.ms.toFixed(0)}ms ${r.dim}`);
