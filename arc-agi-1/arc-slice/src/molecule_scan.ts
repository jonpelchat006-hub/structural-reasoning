// molecule_scan.ts — §17: a program is a MOLECULE; some tasks need TWO atoms BONDED, not one longer
// chain. Find a base molecule P1 (best single-chain near-miss), then BOND a second molecule P2 in
// PARALLEL on the original input, joined at the void-line via overlay (P2's non-bg overrides P1).
// Tests Jonathan's hypothesis: the residual is an open valence that closes only by a 2nd atom.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { bounceSearchDiag } from "./bounce_scan";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const sameDims=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length;
function golden(names:string[]){const n=names.length,phi=(Math.sqrt(5)-1)/2,o:string[]=[],u=new Set<number>();let x=0;for(let i=0;i<n;i++){x=(x+phi)%1;let k=Math.floor(x*n);while(u.has(k))k=(k+1)%n;u.add(k);o.push(names[k]);}return o;}
const ORDER = golden(OP_NAMES);

// overlay bond: base, then where the second grid is non-bg, override
const bond=(a:Grid,b:Grid):Grid|null=>{ if(!sameDims(a,b))return null; return a.map((r,y)=>r.map((v,x)=>b[y][x]!==0?b[y][x]:v)); };

const ev = loadTasks(path.join(__dirname,"..","data-eval"));
const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
let oneSolved=0, bonded=0, netBond:string[]=[];
for(let i=START;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(!t.test||t.test.some((te:any)=>!te.output)) continue;
  const pal=taskPalette(t.train);
  let r:any=null; try{r=bounceSearchDiag(t.train,2,24);}catch{}
  if(!r||!r.bestProg) continue;
  if(r.prog && t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);})){ oneSolved++; continue; }
  // P1 = base molecule; require it preserves dims so a parallel atom can bond
  const P1=(g:Grid)=>{let c:Grid|null=g; for(const[o,p]of r.bestProg){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
  const dimsOk=t.train.every((p:any)=>{const a=P1(p.input);return a&&sameDims(a,p.output);});
  if(!dimsOk) continue;
  // BOND a 2nd atom P2 (single op on the original input), join by overlay
  let found=false;
  for(const op2 of ORDER){ if(found)break; let params:any[]; try{params=(OPS as any)[op2].enumerate(pal).slice(0,4);}catch{params=[{}];}
    for(const pr2 of params){ const P2=(g:Grid)=>{try{return applyOp({name:op2,params:pr2} as any,g);}catch{return null;}};
      const combined=(g:Grid)=>{const a=P1(g),b=P2(g);return a&&b?bond(a,b):null;};
      if(t.train.every((p:any)=>{const o=combined(p.input);return o&&eqG(o,p.output);})){
        // must be a REAL 2nd atom (P2 actually changes the result somewhere)
        const trivial=t.train.every((p:any)=>{const a=P1(p.input);return a&&eqG(a,combined(p.input) as Grid);});
        if(trivial) continue;
        if(t.test.every((te:any)=>{const o=combined(te.input);return o&&eqG(o,te.output);})){ bonded++; if(!verified.has(t.id))netBond.push(t.id); found=true; break; }
      } } }
  if((i+1)%40===0) process.stderr.write(`[${i+1}] one=${oneSolved} bonded=${bonded}\n`);
}
console.log("\n=== §17 MOLECULE (2-atom parallel bond) EVAL ["+START+","+END+") ===");
console.log("single-molecule solved: "+oneSolved);
console.log("closed only by BONDING a 2nd atom: "+bonded+"   net-new(non-verified): "+netBond.length+"  "+netBond.join(" "));
