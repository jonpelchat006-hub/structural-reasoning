// role_closure_scan.ts — §20.6: the CONSCIOUSNESS-LOOP closure as the acceptance gate.
// Three ROLE-strands + the observer, per lib/agents/consciousness-loop.ts + quaternion.ts (w=observer):
//   IMAGINATION (i) = the GA proposes a candidate program (genome).
//   FACTS       (j) = it must close train EXACTLY (phase-lock θ=1). [enforced by evolve()]
//   MEMORY      (k) = every op it uses must TRANSFER — attested in at least one OTHER task's solution
//                     (leave-one-out), i.e. grounded in prior experience, not idiosyncratic to this task.
//   OBSERVER    (w) = accept only when all three hold (CONJUNCTION, not a vote).
// Unlike §19.8's homogeneous K-run vote (clones share overfits → 9ddd00f0 lost), the roles measure
// different things, so their agreement is meaningful. TEST: does the MEMORY conjunct raise test survival?
// Memory library is built from THIS run's own solutions, applied leave-one-out (no second sweep needed).
// Resumable: START END [state] [budgetSec].
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildFn=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
function score(gs:(Grid|null)[],outs:Grid[]):number{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;}
const rnd=(n:number)=>Math.floor(Math.random()*n);
function randGene(pal:number[]):Gene{const o=OP_NAMES[rnd(OP_NAMES.length)];let ps:any[];try{ps=(OPS as any)[o].enumerate(pal);}catch{ps=[{}];}if(!ps||!ps.length)ps=[{}];return[o,ps[rnd(ps.length)]];}
function randGenome(pal:number[],m:number):Genome{const n=1+rnd(m);const g:Genome=[];for(let i=0;i<n;i++)g.push(randGene(pal));return g;}
function mutate(g:Genome,pal:number[],m:number):Genome{const c=g.map(x=>[x[0],{...x[1]}] as Gene);const r=Math.random();if(r<0.4&&c.length)c[rnd(c.length)]=randGene(pal);else if(r<0.7&&c.length<m)c.splice(rnd(c.length+1),0,randGene(pal));else if(r<0.85&&c.length>1)c.splice(rnd(c.length),1);else if(c.length){const i=rnd(c.length),j=rnd(c.length);[c[i],c[j]]=[c[j],c[i]];}return c;}
function crossover(a:Genome,b:Genome):Genome{const i=rnd(a.length+1),j=rnd(b.length+1);return[...a.slice(0,i),...b.slice(j)].slice(0,8);}
function evolve(train:any[]):Genome|null{ // IMAGINATION + FACTS (returns only train-exact genomes)
  if(train.length<2||train.some((p:any)=>p.input.length*p.input[0].length>460))return null;
  const pal=taskPalette(train),outs=train.map((p:any)=>p.output);
  let P:Genome[]=Array.from({length:60},()=>randGenome(pal,5));
  const fit=(g:Genome)=>score(train.map((p:any)=>buildFn(g)(p.input)),outs);
  for(let gen=0;gen<40;gen++){const sc=P.map(g=>({g,s:fit(g)})).sort((a,b)=>b.s-a.s);const bt=sc[0];
    if(bt.s>=1){const f=buildFn(bt.g);if(train.every((p:any)=>{const o=f(p.input);return o&&eqG(o,p.output);})&&!(bt.g.length===1&&bt.g[0][0]==="identity"))return bt.g;}
    const el=sc.slice(0,7).map(x=>x.g);const nx:Genome[]=[...el];
    while(nx.length<60){const a=el[rnd(el.length)],b=el[rnd(el.length)];let ch=Math.random()<0.5?crossover(a,b):a.map(x=>[x[0],{...x[1]}] as Gene);if(Math.random()<0.8)ch=mutate(ch,pal,7);if(!ch.length)ch=[randGene(pal)];nx.push(ch);}
    P=nx;}
  return null;}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
let recs:{id:string;ops:string[];survived:boolean}[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));recs=s.recs;RESUME=s.next;}
const rep=()=>{
  // MEMORY (leave-one-out): op is "remembered" if used by >=1 OTHER solved task
  const opTasks=new Map<string,Set<string>>();
  for(const r of recs)for(const o of new Set(r.ops)){if(!opTasks.has(o))opTasks.set(o,new Set());opTasks.get(o)!.add(r.id);}
  const memPass=(r:{id:string;ops:string[]})=>r.ops.every(o=>{const s=opTasks.get(o)!;return s.size>1||(s.size===1&&!s.has(r.id))?[...s].some(t=>t!==r.id):false;});
  const pass=recs.filter(memPass), fail=recs.filter(r=>!memPass(r));
  const sv=(a:any[])=>a.filter(r=>r.survived).length;
  console.log("\n=== §20.6 ROLE-CLOSURE (imagination ∧ facts ∧ memory) EVAL ["+START+","+END+") ===");
  console.log("imagination+facts solves (train-exact genomes): "+recs.length+"   overall test-survival: "+sv(recs)+"/"+recs.length);
  console.log("+ MEMORY gate PASS (all ops transfer, LOO): "+pass.length+"   survived: "+sv(pass)+"/"+pass.length+(pass.length?"  ("+(sv(pass)/pass.length*100).toFixed(0)+"%)":""));
  console.log("  MEMORY gate FAIL (has an idiosyncratic op): "+fail.length+"   survived: "+sv(fail)+"/"+fail.length+(fail.length?"  ("+(sv(fail)/fail.length*100).toFixed(0)+"%)":""));
  const netAll=recs.filter(r=>r.survived&&!verified.has(r.id)).map(r=>r.id);
  const netMem=pass.filter(r=>r.survived&&!verified.has(r.id)).map(r=>r.id);
  console.log("net-new (imag+facts only): "+netAll.length+"  "+netAll.join(" "));
  console.log("net-new SURVIVING the full closure (imag+facts+memory): "+netMem.length+"  "+netMem.join(" ")); };
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,recs}));console.log("PAUSED at "+i+" solves="+recs.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let g:Genome|null=null; try{g=evolve(t.train);}catch{}
  if(!g)continue;
  const f=buildFn(g); const survived=t.test.every((te:any)=>{const o=f(te.input);return o&&eqG(o,te.output);});
  recs.push({id:t.id,ops:g.map(x=>x[0]),survived}); rec("roleclosure",t.id,survived?"solved":"overfit",g.map(x=>x[0]).join(">"));
  if((i+1)%10===0)process.stderr.write("["+(i+1)+"] solves="+recs.length+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),recs}));
rep();
