import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { solveDiscovery } from "./discover";
import { equal } from "./grid";
const tasks=loadTasks(path.join(__dirname,"..","data-eval"));
const ev=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).filter(Boolean));
const eqG=(a:any,b:any)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r:any,i:number)=>r.every((v:any,j:number)=>v===b[i][j]));
for(const t of tasks){ if(t.train.some((p:any)=>p.input.length*p.input[0].length>450))continue;
  let r:any=null; try{r=solveDiscovery(t.train,undefined,true);}catch{}
  if(r && /Feat/.test(r.kind)){ const tp=t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&eqG(o,te.output);});
    console.log(`${t.id}  ${r.kind}  test:${tp?"PASS":"fail"}  ${ev.has(t.id)?"(already)":"NEW"}`); } }
