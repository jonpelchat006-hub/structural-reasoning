// learnedeval.ts — eval WITH learned priors. Per task: pick the inducer order from the
// learned bucket; attempt ALL 400 (big grids get a cheap ordered-discovery pass instead
// of being skipped). Tests whether meta-learned priors transfer + extend coverage.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { solves as solvesTrain } from "./verify";
import { bruteCandidates } from "./search";
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { taskPalette } from "./transfer";
import { equal } from "./grid";
import { solveCodon } from "./codon";
import { synthGenerator } from "./gen2";
import { synthAntimatter } from "./antimatter";
import { solveDiscovery, INDUCERS } from "./discover";
import { solveCycle } from "./cycle";
import { featureSig } from "./learn";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data-eval"));
const priors=JSON.parse(fs.readFileSync(path.join(__dirname,"..","learned_priors.json"),"utf8"));
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const tp=(prog:(g:Grid)=>Grid|null,t:any)=>t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&eqG(o,te.output);});
function fastProg(train:any[]):((g:Grid)=>Grid|null)|null{ const c=bruteCandidates(train); const pal=taskPalette(train);
  const run=(prog:any)=>(g:Grid)=>{ try{ let cur=g; for(const s of prog){ const {applyOp}=require("./dsl"); const o=applyOp(s,cur); if(!o)return null; cur=o;} return cur;}catch{return null;} };
  if(c.bestScore===1 && solvesTrain(c.best,train)) return run(c.best);
  for(const cand of c.colorCands){ const f=colorMapRepair(cand,train); if(f&&solvesTrain(f,train)) return run(f); }
  for(const cand of [...c.colorCands.slice(0,80),...c.sizeCands]){ const f=sizeRepair(cand,train,pal); if(f&&solvesTrain(f,train)) return run(f); }
  return null; }

let total=0; const byStage:Record<string,number>={}; let i=0; const t0=Date.now();
for(const t of tasks){ if(i++%100===0)process.stderr.write(`[${i}/400]\n`);
  const maxc=Math.max(...t.train.flatMap((p:any)=>[p.input.length*p.input[0].length,p.output.length*p.output[0].length]),...t.test.map((te:any)=>te.input.length*te.input[0].length));
  const sig=featureSig(t.train); const order:string[]=priors.ranked[sig]||priors.globalOrder;
  const big = maxc>450;
  let solvedBy="";
  // learned-ordered discovery FIRST (cheap, prioritized) — works at all sizes
  try{ const r=solveDiscovery(t.train, order); if(r && tp(r.prog,t)){ solvedBy="discovery*"; } }catch{}
  if(!solvedBy && !big){ // full stages only on tractable grids
    const stages:[string,()=>((g:Grid)=>Grid|null)|null][]=[
      ["fast",()=>fastProg(t.train)],
      ["codon",()=>{const c=solveCodon(t.train);return c?c.fn:null;}],
      ["generator",()=>{const r=synthGenerator(t.train);return r?r.prog:null;}],
      ["antimatter",()=>{const r=synthAntimatter(t.train);return r?r.prog:null;}],
      ["cycle",()=>solveCycle(t.train)],
    ];
    for(const [name,fn] of stages){ let prog:any=null; try{prog=fn();}catch{} if(prog && tp(prog,t)){ solvedBy=name; break; } }
  }
  if(!solvedBy && big){ // BIG grids: cheap learned-priority attempt (identity ∘ top inducers)
    const topInds = order.slice(0,3);
    for(const iname of topInds){ const ent=INDUCERS.find((e:any)=>e[0]===iname); if(!ent)continue;
      let resid:any=null; try{resid=ent[1](t.train);}catch{} if(!resid)continue;
      if(t.train.every((p:any)=>{const o=resid(p.input);return o&&eqG(o,p.output);}) && tp(resid,t)){ solvedBy="discovery(big)"; break; } }
  }
  if(solvedBy){ total++; byStage[solvedBy]=(byStage[solvedBy]??0)+1; }
}
console.log(`\n=== LEARNED EVAL (all 400 attempted, learned priors) — ${((Date.now()-t0)/1000).toFixed(1)}s ===`);
console.log(`TOTAL: ${total}/400 (${(100*total/400).toFixed(2)}%)`);
console.log(`by stage: ${JSON.stringify(byStage)}`);
