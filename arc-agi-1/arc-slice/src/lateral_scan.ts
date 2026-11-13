// lateral_scan.ts — §18.7: the Shark needs a compass. Anchor it at a KNOWN BRANCH already further out
// (the best forward NEAR-MISS — a spring poking ~0.99 into the target region), then search LATERALLY
// (vary it by one op) and converge. Fixes the beam-pruning gap: the 0.99 state's one-op continuations
// were dropped from the beam and never tried; anchoring explicitly at it tries them.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { bounceSearchDiag } from "./bounce_scan";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
function golden(names:string[]){const n=names.length,phi=(Math.sqrt(5)-1)/2,o:string[]=[],u=new Set<number>();let x=0;for(let i=0;i<n;i++){x=(x+phi)%1;let k=Math.floor(x*n);while(u.has(k))k=(k+1)%n;u.add(k);o.push(names[k]);}return o;}
const ORDER = golden(OP_NAMES);
const build=(prog:[string,any][])=>(g:Grid)=>{let c:Grid|null=g;for(const[o,p]of prog){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};

const ev = loadTasks(path.join(__dirname,"..","data-eval"));
const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
let base=0, lateral=0, net:string[]=[];
for(let i=START;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(!t.test||t.test.some((te:any)=>!te.output)) continue;
  const pal=taskPalette(t.train);
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r||!r.bestProg) continue;
  if(r.prog && t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);})){ base++; continue; }
  // ANCHOR at the known branch further out (best near-miss). Only bother if it is genuinely far out.
  if(r.bestScore < 0.5) continue;
  const anchor=r.bestProg as [string,any][]; const A=build(anchor);
  const Ain=t.train.map((p:any)=>A(p.input)); if(Ain.some((g:any)=>!g)) continue;
  let closed:((g:Grid)=>Grid|null)|null=null, how="";
  // LATERAL move 1: append one op after the anchor
  for(const op of ORDER){ if(closed)break; let params:any[]; try{params=(OPS as any)[op].enumerate(pal).slice(0,6);}catch{params=[{}];}
    for(const pr of params){ const cand=(g:Grid)=>{const a=A(g);if(!a)return null;try{return applyOp({name:op,params:pr} as any,a);}catch{return null;}};
      if(t.train.every((p:any)=>{const o=cand(p.input);return o&&eqG(o,p.output);})){ closed=cand; how="append:"+op; break; } } }
  // LATERAL move 2: swap the anchor's LAST op for a different one
  if(!closed && anchor.length>=1){ const head=anchor.slice(0,-1); const H=build(head);
    for(const op of ORDER){ if(closed)break; let params:any[]; try{params=(OPS as any)[op].enumerate(pal).slice(0,6);}catch{params=[{}];}
      for(const pr of params){ const cand=(g:Grid)=>{const h=H(g);if(!h)return null;try{return applyOp({name:op,params:pr} as any,h);}catch{return null;}};
        if(t.train.every((p:any)=>{const o=cand(p.input);return o&&eqG(o,p.output);})){ closed=cand; how="swapLast:"+op; break; } } } }
  if(closed && t.test.every((te:any)=>{const o=closed!(te.input);return o&&eqG(o,te.output);})){ lateral++; if(!verified.has(t.id)) net.push(t.id+"["+how+"]"); }
  if((i+1)%40===0) process.stderr.write(`[${i+1}] base=${base} lateral=${lateral}\n`);
}
console.log("\n=== §18.7 LATERAL-from-anchor (Shark with a compass) EVAL ["+START+","+END+") ===");
console.log("base forward solved: "+base);
console.log("closed by LATERAL search around near-miss anchor: "+lateral+"   net-new: "+net.length+"  "+net.join(" "));
