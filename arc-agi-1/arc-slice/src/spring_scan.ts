// spring_scan.ts — §16b: the SECOND bounce. Run depth-3; for the springs that poke furthest into the
// void (high near-miss but unlocked), do "another recursive cycle" = retry at depth+1 exactly there.
// Report which springs break (top near-misses = where to build next).
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { bounceSearchDiag } from "./bounce_scan";
type Grid = number[][];
const eqG = (a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

const ev = loadTasks(path.join(__dirname,"..","data-eval"));
const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
let s3=0,n3=0, deepened=0,nD=0; const breaks:[string,number,string][]=[]; const hist:Record<string,number>={};
for(let i=START;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(!t.test||t.test.some((te:any)=>!te.output)) continue;
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r) continue;
  if(r.prog && t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);})){ s3++; if(!verified.has(t.id))n3++; continue; }
  // unsolved at depth 3: the spring's furthest poke
  const b=r.bestScore; const band=b>=0.95?"0.95+":b>=0.9?"0.90-95":b>=0.8?"0.80-90":b>=0.6?"0.60-80":"<0.60"; hist[band]=(hist[band]||0)+1;
  if(b>=0.9){ // a spring poking far but not locked -> another recursive cycle (depth+1)
    const prog=r.bestProg?r.bestProg.map(p=>p[0]).join("->"):""; breaks.push([t.id, +b.toFixed(3), prog]);
    let r4:any=null; try{r4=bounceSearchDiag(t.train,4,24);}catch{}
    if(r4&&r4.prog && t.test.every((te:any)=>{const o=r4.prog(te.input);return o&&eqG(o,te.output);})){ deepened++; if(!verified.has(t.id))nD++; }
  }
  if((i+1)%40===0) process.stderr.write(`[${i+1}] s3=${s3} deepened=${deepened}\n`);
}
console.log("\n=== §16b SPRING-SCAN (depth3 + recurse-on-poke) EVAL ["+START+","+END+") ===");
console.log("depth-3 solved="+s3+"  net-new="+n3);
console.log("near-miss (broken-spring) distribution: "+JSON.stringify(hist));
console.log("DEEPENED (depth-4 on springs poking >=0.90): new solves="+deepened+"  net-new="+nD);
console.log("top broken springs (id, near-miss, partial program):");
breaks.sort((a,b)=>b[1]-a[1]).slice(0,8).forEach(b=>console.log("  "+b[0]+"  "+b[1]+"  "+b[2]));
