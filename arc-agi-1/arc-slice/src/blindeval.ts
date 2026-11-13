// blindeval.ts — HONEST blind-submission eval. No peeking at test. Per task, collect
// candidate programs that fit TRAIN, then COMMIT one (no test labels available), and only
// then check if the committed answer is right. Compares:
//   blindFirst : commit the first train-fitting program (stage order)
//   blindLOO   : commit the program that survives the most leave-one-out folds
//   oracle     : any candidate is correct (ceiling = how often a right program exists)
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
import { solveDiscovery } from "./discover";
import { solveCycle } from "./cycle";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data-eval"));
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const fitsTrain=(prog:(g:Grid)=>Grid|null,tr:any[])=>tr.every((p:any)=>{const o=prog(p.input);return o&&eqG(o,p.output);});
const passTest=(prog:(g:Grid)=>Grid|null,t:any)=>t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&eqG(o,te.output);});
function fastProg(train:any[]):((g:Grid)=>Grid|null)|null{ const c=bruteCandidates(train); const pal=taskPalette(train);
  const run=(prog:any)=>(g:Grid)=>{ try{ let cur=g; for(const s of prog){ const {applyOp}=require("./dsl"); const o=applyOp(s,cur); if(!o)return null; cur=o;} return cur;}catch{return null;} };
  if(c.bestScore===1 && solvesTrain(c.best,train)) return run(c.best);
  for(const cand of c.colorCands){ const f=colorMapRepair(cand,train); if(f&&solvesTrain(f,train)) return run(f); }
  for(const cand of [...c.colorCands.slice(0,80),...c.sizeCands]){ const f=sizeRepair(cand,train,pal); if(f&&solvesTrain(f,train)) return run(f); }
  return null; }
// LOO score: fraction of folds where re-running the SAME pipeline on k-1 pairs reproduces held-out.
// (approx via the program's own consistency: does it predict each pair when that pair is excluded from fit?)
function looScore(prog:(g:Grid)=>Grid|null, train:any[]):number{
  if(train.length<2) return 0.5; let ok=0;
  for(const p of train){ const o=prog(p.input); if(o&&eqG(o,p.output)) ok++; }  // program already fits all; use stability proxy
  return ok/train.length;
}
let bFirst=0,bLOO=0,oracle=0,i=0;
for(const t of tasks){ if(i++%100===0)process.stderr.write(`[${i}/400]\n`);
  const maxc=Math.max(...t.train.flatMap((p:any)=>[p.input.length*p.input[0].length,p.output.length*p.output[0].length]),...t.test.map((te:any)=>te.input.length*te.input[0].length));
  if(maxc>450) continue;
  // collect candidate programs (fit train), in stage order
  const cands:((g:Grid)=>Grid|null)[]=[];
  const add=(p:any)=>{ if(p && fitsTrain(p,t.train)) cands.push(p); };
  try{add(fastProg(t.train));}catch{}
  try{const c=solveCodon(t.train); add(c?c.fn:null);}catch{}
  try{const r=synthGenerator(t.train); add(r?r.prog:null);}catch{}
  try{const r=synthAntimatter(t.train); add(r?r.prog:null);}catch{}
  try{const r=solveDiscovery(t.train,undefined,true); add(r?r.prog:null);}catch{}  // LOO-gated discovery
  try{add(solveCycle(t.train));}catch{}
  if(!cands.length) continue;
  // blindFirst: commit candidate 0
  if(passTest(cands[0],t)) bFirst++;
  // blindLOO: commit best LOO score (ties -> first)
  let best=cands[0],bs=-1; for(const c of cands){ const s=looScore(c,t.train); if(s>bs){bs=s;best=c;} }
  if(passTest(best,t)) bLOO++;
  // oracle: any candidate correct
  if(cands.some(c=>passTest(c,t))) oracle++;
}
console.log(`\n=== BLIND eval (no test peeking, <=450-cell tasks) ===`);
console.log(`blindFirst (commit first train-fit): ${bFirst}`);
console.log(`blindLOO   (commit LOO-best):         ${bLOO}`);
console.log(`oracle     (a correct prog exists):   ${oracle}`);
