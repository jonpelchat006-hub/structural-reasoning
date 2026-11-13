import * as path from "path";
import { loadTasks } from "./loader";
import { equal } from "./grid";
import { synthGenerator } from "./gen2";
import * as fs from "fs";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,"..","gen_fixture.json"),"utf8")) as {id:string,testPass:boolean}[];
const fixIds=new Set(fixture.map(f=>f.id));
const eqAll=(prog:any,train:any[])=>train.every((p:any)=>{const o=prog(p.input);return o&&equal(o,p.output);});
const solved:any[]=[];
for(const t of tasks){
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>900)) continue;
  let r:any=null; try{r=synthGenerator(t.train);}catch{}
  if(r&&eqAll(r.prog,t.train)){
    const testPass=t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&equal(o,te.output);});
    solved.push({id:t.id,testPass,kind:r.kind});
  }
}
const solvedIds=new Set(solved.map(s=>s.id));
const missing=[...fixIds].filter(id=>!solvedIds.has(id));
const extra=solved.filter(s=>!fixIds.has(s.id));
console.log("gen2 solved:", solved.length, "| fixture:", fixIds.size);
console.log("MISSING from fixture (REGRESSION):", missing.length?missing.join(" "):"none — no loss");
console.log("EXTRA beyond fixture (GAIN):", extra.length?extra.map(e=>e.id+(e.testPass?"*":"(train-only)")).join(" "):"none");
console.log("--- all gen2 solves ---");
for(const s of solved) console.log(`  ${s.id}  ${s.testPass?"TEST":"train"}  ${s.kind}`);
