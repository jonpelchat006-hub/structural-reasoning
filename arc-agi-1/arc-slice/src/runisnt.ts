import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { equal } from "./grid";
import { synthIsnt } from "./isnt";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const combined=new Set(fs.readFileSync(path.join(__dirname,"..","combined_solved.txt"),"utf8").trim().split(/\s+/));
const eqAll=(p:any,tr:any[])=>tr.every((x:any)=>{const o=p(x.input);return o&&equal(o,x.output);});
let solved=0; const netnew:any[]=[];
for(const t of tasks){
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>1200)) continue;
  let r:any=null; try{r=synthIsnt(t.train);}catch{}
  if(r&&eqAll(r.prog,t.train)){
    const testPass=t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&equal(o,te.output);});
    if(testPass){ solved++; if(!combined.has(t.id)) netnew.push(`${t.id}(${r.kind})`); }
  }
}
console.log(`isnt-generator solves (test-pass): ${solved}`);
console.log(`NET-NEW over combined-79: ${netnew.length}`);
netnew.forEach(h=>console.log("  "+h));
