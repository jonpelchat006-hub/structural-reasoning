import * as path from "path";
import { loadTasks } from "./loader";
import { solveDiscovery } from "./discover";
import { equal } from "./grid";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const eqG=(a:any,b:any)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r:any,i:number)=>r.every((v:any,j:number)=>v===b[i][j]));
const hit:Record<string,number>={};
for(const t of tasks){ if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
  let r:any=null; try{r=solveDiscovery(t.train);}catch{}
  if(r && /Feat|shear|SlideByRank/.test(r.kind)){ const k=r.kind.split("∘")[1]||r.kind; hit[k]=(hit[k]??0)+1;
    const tp=t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&eqG(o,te.output);});
    console.log(`${t.id}  ${r.kind}  test:${tp?"PASS":"fail"}`); } }
console.log("derivative-inducer fires on training:", JSON.stringify(hit));
