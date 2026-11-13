import * as path from "path";
import { loadTasks } from "./loader";
import { equal } from "./grid";
import { synthIsnt } from "./isnt";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const eqAll=(p:any,tr:any[])=>tr.every((x:any)=>{const o=p(x.input);return o&&equal(o,x.output);});
let trainFit=0, testPass=0; const kinds:Record<string,number>={};
for(const t of tasks){
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>1200)) continue;
  let r:any=null; try{r=synthIsnt(t.train);}catch{}
  if(r&&eqAll(r.prog,t.train)){ trainFit++; const fam=r.kind.split("/")[0].replace(/[0-9x]+$/,"");kinds[fam]=(kinds[fam]??0)+1;
    if(t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&equal(o,te.output);})) testPass++;
    else console.log("OVERFIT", t.id, r.kind);
  }
}
console.log(`train-fit: ${trainFit}  test-pass: ${testPass}`);
console.log("families:", JSON.stringify(kinds));
