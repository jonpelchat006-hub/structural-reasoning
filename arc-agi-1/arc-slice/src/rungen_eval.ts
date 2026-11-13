// rungen_eval.ts — run the discovery engine (with the leave-one-out gate) over the EVAL set,
// to measure what the new generative draw inducers (rays, connect) catch on held-out tasks.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { solveDiscovery } from "./discover";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

const evalTasks=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||evalTasks.length);

let solved=0, netnew:string[]=[], draw:string[]=[]; const kinds:Record<string,number>={};
for(let i=START;i<Math.min(END,evalTasks.length);i++){ const t=evalTasks[i];
  if(!t.test || t.test.some((te:any)=>!te.output)) continue;            // need answers to verify
  let r:{prog:(g:Grid)=>Grid|null,kind:string}|null=null;
  try{ r=solveDiscovery(t.train, undefined, true); }catch{}             // looGate=true
  if(!r) continue;
  const tp=t.test.every((te:any)=>{const o=r!.prog(te.input);return o&&eqG(o,te.output);});
  if(!tp) continue;
  solved++; kinds[r.kind]=(kinds[r.kind]||0)+1;
  if(!verified.has(t.id)) netnew.push(`${t.id}[${r.kind}]`);
  if(/rays|connect|stamp|hole/.test(r.kind)) draw.push(`${t.id}[${r.kind}]`);
  if((i+1)%100===0) process.stderr.write(`[${i+1}/${evalTasks.length}] solved=${solved} netnew=${netnew.length}\n`);
}
console.log("\n=== DISCOVERY on EVAL (leave-one-out gated) ===");
console.log("eval discovery-solved (this range): " + solved);
console.log("NET-NEW vs verified_eval(26):        " + netnew.length + "   " + netnew.join(" "));
console.log("solves using NEW draw inducers (rays/connect): " + draw.length + "   " + draw.join(" "));
console.log("by kind: " + Object.entries(kinds).sort((a,b)=>b[1]-a[1]).map(([k,n])=>`${k}:${n}`).join("  "));
