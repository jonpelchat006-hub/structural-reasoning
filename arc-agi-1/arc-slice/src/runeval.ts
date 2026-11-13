// runall.ts — CONSOLIDATED pipeline: one reproducible number.
// Per task, try each solver in order; count a task solved when a program also
// reproduces the held-out TEST output (true generalization, not just train-fit).
import * as path from "path";
import { loadTasks } from "./loader";
import { solves as solvesTrain, applyToTest } from "./verify";
import { bruteCandidates } from "./search";
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { taskPalette } from "./transfer";
import { equal } from "./grid";
import { solveCodon } from "./codon";
import { synthGenerator } from "./gen2";
import { synthAntimatter } from "./antimatter";
import { solveDiscovery } from "./discover";
import { solveCycle } from "./cycle";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data-eval"));
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const testPass=(prog:(g:Grid)=>Grid|null,t:any)=>t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&eqG(o,te.output);});

// transformer fast pipeline -> returns a prog that solves train (for test-check we re-derive)
function fastProg(train:any[]):((g:Grid)=>Grid|null)|null{
  const c=bruteCandidates(train); const pal=taskPalette(train);
  const run=(prog:any)=>(g:Grid)=>{ try{ let cur=g; for(const s of prog){ const {applyOp}=require("./dsl"); const o=applyOp(s,cur); if(!o)return null; cur=o;} return cur;}catch{return null;} };
  if(c.bestScore===1 && solvesTrain(c.best,train)) return run(c.best);
  for(const cand of c.colorCands){ const f=colorMapRepair(cand,train); if(f&&solvesTrain(f,train)) return run(f); }
  for(const cand of [...c.colorCands.slice(0,80),...c.sizeCands]){ const f=sizeRepair(cand,train,pal); if(f&&solvesTrain(f,train)) return run(f); }
  return null;
}

const STAGES:[string,(t:any)=>((g:Grid)=>Grid|null)|null][]=[
  ["fast",     t=>fastProg(t.train)],
  ["codon",    t=>{const c=solveCodon(t.train);return c?c.fn:null;}],
  ["generator",t=>{const r=synthGenerator(t.train);return r?r.prog:null;}],
  ["antimatter",t=>{const r=synthAntimatter(t.train);return r?r.prog:null;}],
  ["discovery",t=>{const r=solveDiscovery(t.train);return r?r.prog:null;}],
  ["cycle",    t=>solveCycle(t.train)],
];

let total=0; const byStage:Record<string,number>={}; const solvedIds:string[]=[]; let i=0; const t0=Date.now();
for(const t of tasks){ if(i++%100===0)process.stderr.write(`[${i}/400]\n`);
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>900)) { /* still try light stages */ }
  const cells=(g:any)=>g.length*g[0].length; const maxc=Math.max(...t.train.flatMap((p:any)=>[cells(p.input),cells(p.output)]),...t.test.map((te:any)=>cells(te.input)));
  if(maxc>450){ continue; }  // skip oversized tasks (unsolved); keeps the run bounded
  const big=false;
  const HEAVY=new Set(["codon","discovery","cycle"]);
  let solvedBy=""; 
  for(const [name,fn] of STAGES){ if(big&&HEAVY.has(name))continue; let prog:any=null; try{prog=fn(t);}catch{}
    if(prog && testPass(prog,t)){ solvedBy=name; break; } }
  if(solvedBy){ total++; byStage[solvedBy]=(byStage[solvedBy]??0)+1; solvedIds.push(t.id); }
}
const secs=((Date.now()-t0)/1000).toFixed(1);
console.log(`\n=== CONSOLIDATED (test-verified) — ${secs}s ===`);
console.log(`TOTAL: ${total}/400 (${(100*total/400).toFixed(2)}%)`);
console.log(`by stage (first to solve): ${JSON.stringify(byStage)}`);
require("fs").writeFileSync(path.join(__dirname,"..","verified_eval.txt"),solvedIds.sort().join("\n"));
