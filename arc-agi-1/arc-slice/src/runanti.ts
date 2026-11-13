import * as path from "path";
import { loadTasks } from "./loader";
import { equal } from "./grid";
import { synthAntimatter } from "./antimatter";
import * as fs from "fs";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const baseline=new Set(fs.readFileSync(path.join(__dirname,"..","out_dump.log"),"utf8").trim().split(/\s+/));
const eqAll=(prog:any,train:any[])=>train.every((p:any)=>{const o=prog(p.input);return o&&equal(o,p.output);});
const solved:any[]=[]; const netnew:string[]=[];
for(const t of tasks){
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>1200)) continue;
  let r:any=null; try{r=synthAntimatter(t.train);}catch{}
  if(r&&eqAll(r.prog,t.train)){
    const testPass=t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&equal(o,te.output);});
    solved.push({id:t.id,testPass,kind:r.kind});
    if(testPass && !baseline.has(t.id)) netnew.push(t.id);
  }
}
console.log(`antimatter solves (train+test pass): ${solved.filter(s=>s.testPass).length} / train-fit ${solved.length}`);
console.log(`NET-NEW over 76 baseline (test-generalizing): ${netnew.length}`);
console.log(`net-new ids: ${netnew.join(" ")}`);
console.log("--- breakdown by predicate/action ---");
const by:Record<string,number>={}; for(const s of solved) if(s.testPass){const k=s.kind.split("/").slice(0,2).join("/");by[k]=(by[k]??0)+1;}
for(const[k,v]of Object.entries(by).sort((a,b)=>b[1]-a[1])) console.log(`  ${k.padEnd(22)} ${v}`);
