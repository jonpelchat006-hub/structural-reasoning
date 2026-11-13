// dna_scan.ts — §19: the DNA rung. A solution is a GENOME (op sequence) written in a 64-codon code
// (§13.1 4×4×4 = the genetic code's 64), evolved by mutation + crossover under a fitness = forward
// train-agreement. The DNA-SPECIFIC mechanism is COMPLEMENTARITY: an accepted genome's invertible core
// is reverse-complemented and applied to the OUTPUT; if it templates back to the INPUT, the genome is
// DOUBLE-STRANDED (semi-conservative replication holds). This generalizes the §18.19 isotope-convergence
// survival law into a selection gate: a genome its own complement can rebuild should generalize.
// We MEASURE whether double-strandedness predicts test survival. Resumable: START END [state] [budgetSec].
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];

// ── the genetic code: op index → 3-letter codon over {A,C,G,U} (base-4 triplet). 63 ops ⊂ 64 codons. ──
const BASES=["A","C","G","U"];
const codonOf=(op:string)=>{let i=OP_NAMES.indexOf(op);if(i<0)i=63;return BASES[(i>>4)&3]+BASES[(i>>2)&3]+BASES[i&3];};
const genomeCodons=(g:Genome)=>g.map(([o])=>codonOf(o)).join("");

// ── the complement: inverse op for the invertible "bases" (rotate/flip/transpose/bijective-recolor/swap) ──
function invGene(gn:Gene):Gene|null{ const[o,p]=gn;
  switch(o){ case "identity":case "flipH":case "flipV":case "transpose":case "antiTranspose":return[o,p];
    case "rotate":{const ik=(4-((p.k||0)%4))%4; return ik===0?["identity",{}]:["rotate",{k:ik}];} // rotate k -> rotate 4-k
    case "swap":return["swap",p]; // colour swap is its own inverse
    case "recolor":return["recolor",{from:p.to,to:p.from}]; // bijective only; caller checks templating
    default:return null; } } // crop/scale/gravity/keep*/… are NOT invertible
const buildFn=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
// reverse-complement applied to output should template back to input, over the invertible suffix
function doubleStranded(g:Genome,train:any[]):boolean{
  const inv:Genome=[]; for(let i=g.length-1;i>=0;i--){const iv=invGene(g[i]);if(!iv)return false;inv.push(iv);} // whole genome must be invertible
  const R=buildFn(inv);
  return train.every((p:any)=>{const back=R(p.output);return back&&eqG(back,p.input);});
}

function score(gs:(Grid|null)[],outs:Grid[]):number{ let s=0;
  for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i]; if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
    let eq=0,tot=g.length*g[0].length; for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++; s+=eq/tot; }
  return s/gs.length; }

// ── evolution ──
const rnd=(n:number)=>Math.floor(Math.random()*n);
function randGene(pal:number[]):Gene{ const o=OP_NAMES[rnd(OP_NAMES.length)]; let ps:Record<string,number>[];
  try{ps=(OPS as any)[o].enumerate(pal);}catch{ps=[{}];} if(!ps||!ps.length)ps=[{}]; return[o,ps[rnd(ps.length)]]; }
function randGenome(pal:number[],maxLen:number):Genome{ const n=1+rnd(maxLen); const g:Genome=[]; for(let i=0;i<n;i++)g.push(randGene(pal)); return g; }
function mutate(g:Genome,pal:number[],maxLen:number):Genome{ const c=g.map(x=>[x[0],{...x[1]}] as Gene); const r=Math.random();
  if(r<0.4&&c.length){c[rnd(c.length)]=randGene(pal);}                       // point substitution
  else if(r<0.7&&c.length<maxLen){c.splice(rnd(c.length+1),0,randGene(pal));} // insertion
  else if(r<0.85&&c.length>1){c.splice(rnd(c.length),1);}                     // deletion
  else if(c.length){const i=rnd(c.length),j=rnd(c.length);[c[i],c[j]]=[c[j],c[i]];} // transposition (reorder)
  return c; }
function crossover(a:Genome,b:Genome):Genome{ const i=rnd(a.length+1),j=rnd(b.length+1); return[...a.slice(0,i),...b.slice(j)].slice(0,8); }

type Res={prog:((g:Grid)=>Grid|null)|null;genome:Genome|null;ds:boolean};
function evolve(train:any[],pop=60,gens=40):Res{
  if(train.length<2)return{prog:null,genome:null,ds:false};
  if(train.some((p:any)=>p.input.length*p.input[0].length>460))return{prog:null,genome:null,ds:false};
  const pal=taskPalette(train), outs=train.map((p:any)=>p.output);
  let P:Genome[]=Array.from({length:pop},()=>randGenome(pal,5));
  const fit=(g:Genome)=>{const f=buildFn(g);const sc=score(train.map((p:any)=>f(p.input)),outs); return sc;};
  for(let gen=0;gen<gens;gen++){
    const scored=P.map(g=>({g,s:fit(g)})).sort((a,b)=>b.s-a.s);
    const best=scored[0];
    if(best.s>=1){ const f=buildFn(best.g); // phase-lock: exact on all train
      if(train.every((p:any)=>{const o=f(p.input);return o&&eqG(o,p.output);}) && !(best.g.length===1&&best.g[0][0]==="identity"))
        return{prog:f,genome:best.g,ds:doubleStranded(best.g,train)}; }
    const elite=scored.slice(0,Math.max(2,pop>>3)).map(x=>x.g); // elitism
    const next:Genome[]=[...elite];
    while(next.length<pop){ const a=elite[rnd(elite.length)], b=elite[rnd(elite.length)];
      let child=Math.random()<0.5?crossover(a,b):a.map(x=>[x[0],{...x[1]}] as Gene);
      if(Math.random()<0.8)child=mutate(child,pal,7); if(!child.length)child=[randGene(pal)]; next.push(child); }
    P=next;
  }
  return{prog:null,genome:null,ds:false};
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
let solved=0, dsSolved=0, dsSurv=0, dsN=0, ssSurv=0, ssN=0, net:string[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));({solved,dsSolved,dsSurv,dsN,ssSurv,ssN,net}=s);RESUME=s.next;}
const rep=()=>{ console.log("\n=== §19 DNA (evolutionary codon genomes) EVAL ["+START+","+END+") ===");
  console.log("train phase-locked genomes: "+solved+"   of which DOUBLE-STRANDED: "+dsSolved);
  console.log("test survival | double-stranded: "+dsSurv+"/"+dsN+"   single-stranded: "+ssSurv+"/"+ssN);
  console.log("NET-NEW vs verified_eval: "+net.length+"   "+net.join(" ")); };
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,solved,dsSolved,dsSurv,dsN,ssSurv,ssN,net}));console.log("PAUSED at "+i+" solved="+solved+" ds="+dsSolved);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let r:Res={prog:null,genome:null,ds:false}; try{r=evolve(t.train,60,40);}catch{}
  if(!r.prog||!r.genome)continue; solved++;
  const surv=t.test.every((te:any)=>{const o=r.prog!(te.input);return o&&eqG(o,te.output);}); rec("dna",t.id,surv?"solved":"overfit",r.genome!.map((x:any)=>x[0]).join(">"));
  if(r.ds){dsSolved++;dsN++;if(surv)dsSurv++;} else {ssN++;if(surv)ssSurv++;}
  if(surv&&!verified.has(t.id))net.push(t.id+(r.ds?"(ds:":"(ss:")+genomeCodons(r.genome)+")");
  if((i+1)%10===0)process.stderr.write("["+(i+1)+"] solved="+solved+" ds="+dsSolved+" net="+net.length+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),solved,dsSolved,dsSurv,dsN,ssSurv,ssN,net}));
rep();
