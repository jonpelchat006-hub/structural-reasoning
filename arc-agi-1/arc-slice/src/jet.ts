// jet.ts — FORCE-CANCELLATION beam search. Residual = the unknown force the game
// applies (mismatch to train outputs, felt not seen). Each action is a force vector
// with a primary axis + COUPLING (side-effects on other axes). Beam keeps non-greedy
// states so coupling can find combinations greedy/flat search misses. Accept at θ=1.
import * as path from "path";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
const HEAVY=new Set(["mapObjects","mapTopK","fractal","nested","colorByShape","overlayPanels","combinePanels","periodicFill","stamp","moveContact","connectObjects","completeDiag","grow","drawRays","alignLargest","gravityObj"]);
const FORCE_OPS=OP_NAMES.filter(n=>!HEAVY.has(n));
import { taskPalette } from "./transfer";
import { equal, palette } from "./grid";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data"));
const baseline=new Set(require("fs").readFileSync(path.join(__dirname,"..","out_dump.log"),"utf8").trim().split(/\s+/));

// tension VECTOR of a state vs target (per-axis force components)
function tension(c:Grid,o:Grid):number{
  if(!c||!c.length) return 1e9;
  const sizePen = (c.length!==o.length||c[0].length!==o[0].length) ? 1 : 0;
  if(sizePen){ // size axis dominates: compare scale-invariant colour histograms
    const h=(g:Grid)=>{const m=new Map<number,number>();let n=0;for(const r of g)for(const v of r){m.set(v,(m.get(v)??0)+1);n++;}return {m,n};};
    const a=h(c),b=h(o); let d=0; const keys=new Set([...a.m.keys(),...b.m.keys()]);
    for(const k of keys) d+=Math.abs((a.m.get(k)??0)/a.n-(b.m.get(k)??0)/b.n);
    return 0.5+0.5*d/2; // size-mismatch band [0.5,1]
  }
  let mis=0,tot=0; for(let y=0;y<o.length;y++)for(let x=0;x<o[0].length;x++){tot++;if(c[y][x]!==o[y][x])mis++;}
  return mis/tot;
}
function totalTension(prog:{op:string,params:any}[], train:any[]):number{
  let s=0; for(const p of train){ let g=p.input; for(const step of prog){ const o=applyOp({name:step.op,params:step.params} as any,g); if(!o)return 1e9; g=o; } s+=tension(g,p.output);} return s/train.length;
}
function solvesProg(prog:{op:string,params:any}[],train:any[]):boolean{
  return train.every(p=>{let g=p.input;for(const step of prog){const o=applyOp({name:step.op,params:step.params} as any,g);if(!o)return false;g=o;}return equal(g,p.output);});
}
function candParams(op:string,pal:number[]):any[]{ try{return (OPS as any)[op].enumerate(pal).slice(0,4);}catch{return [{}];} }

function jetSearch(train:any[], beamW=4, depth=3):boolean{
  let budget=4000;
  const pal=taskPalette(train);
  let beam:{prog:{op:string,params:any}[],t:number}[]=[{prog:[],t:totalTension([],train)}];
  for(let d=0; d<depth; d++){
    const next:{prog:{op:string,params:any}[],t:number}[]=[];
    for(const b of beam){
      for(const op of FORCE_OPS){ if(budget--<=0) break; for(const pr of candParams(op,pal)){
        const prog=[...b.prog,{op,params:pr}];
        if(solvesProg(prog,train)) return true;
        const t=totalTension(prog,train);
        if(t<b.t-1e-9) next.push({prog,t}); // only keep force-REDUCING moves... 
        else if(t<b.t+0.05 && next.length<4000) next.push({prog,t}); // near-flat coupling, capped
      }}
    }
    if(!next.length||budget<=0) break;
    next.sort((a,b)=>a.t-b.t);
    // dedupe by tension+len, keep diverse beam
    beam=next.slice(0,beamW);
  }
  return false;
}

let solved=0, netnew:string[]=[]; let i=0;
for(const t of tasks){ i++;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>420)) continue;
  let ok=false; try{ok=jetSearch(t.train);}catch{}
  if(ok){ solved++; if(!baseline.has(t.id)) netnew.push(t.id); }
  if(i%100===0) process.stderr.write(`[${i}/400] solved=${solved}\n`);
}
console.log(`\njet (force-cancellation beam) solved: ${solved}`);
console.log(`NET-NEW over 77 baseline: ${netnew.length}  ${netnew.join(" ")}`);
