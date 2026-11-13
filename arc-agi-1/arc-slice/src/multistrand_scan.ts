// multistrand_scan.ts — §19.8: MORE THAN TWO STRANDS. A "strand" = an independent derivation that
// reconstructs the answer (§18.19 survival was 2 routes agreeing; §19 double-strand was fwd+complement).
// Jonathan: if single & double, why not triple+? — and k strands bound a (k-1)-simplex of void (§11.6
// point→line→sheet→tunnel; §18.15 tetrahedra) = §18.16's k-channel registration. Test: run the evolution
// K times INDEPENDENTLY; a task is k-STRANDED if k independent solving genomes AGREE on the test
// prediction (largest agreeing cluster = strand count). Measure survival vs strand count — does more
// agreement predict generalization? (the k>2 form of the convergence law, and a precision knob).
// Resumable: START END [state] [budgetSec] [K].
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
function evolve(train:any[]):Genome|null{
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
// serialize a genome's prediction over all test inputs (the "phenotype" it votes for)
const pheno=(g:Genome,test:any[]):string|null=>{const f=buildFn(g);const outs=test.map((te:any)=>f(te.input));if(outs.some(o=>!o))return null;return outs.map(o=>o!.length+"x"+o![0].length+":"+o!.flat().join(",")).join("|");};

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, K=+(process.argv[6]||3), T0=Date.now();
let recs:{id:string;solvers:number;strand:number;correct:boolean}[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));recs=s.recs;RESUME=s.next;}
const rep=()=>{ console.log("\n=== §19.8 MULTI-STRAND (K="+K+" independent evolutions, agreement=strand count) ["+START+","+END+") ===");
  console.log("tasks with >=1 solving strand: "+recs.length);
  for(let k=1;k<=K;k++){ const at=recs.filter(r=>r.strand===k); const ok=at.filter(r=>r.correct).length;
    console.log("  strand-count "+k+": "+at.length+" tasks   test-correct: "+ok+"/"+at.length+(at.length?"  ("+(ok/at.length*100).toFixed(0)+"%)":"")); }
  const net=recs.filter(r=>r.correct&&!verified.has(r.id));
  console.log("net-new (correct & unverified): "+net.length+"   "+net.map(r=>r.id+"[s"+r.strand+"]").join(" ")); };
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,recs}));console.log("PAUSED at "+i+" tasks="+recs.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  const phenos:Record<string,number>={}; let solvers=0;
  for(let k=0;k<K;k++){ let g:Genome|null=null; try{g=evolve(t.train);}catch{} if(!g)continue; const ph=pheno(g,t.test); if(!ph)continue; solvers++; phenos[ph]=(phenos[ph]||0)+1; }
  if(!solvers)continue;
  // strand count = largest agreeing cluster; the agreed phenotype is that cluster's prediction
  let bestPh="", strand=0; for(const[ph,c]of Object.entries(phenos)) if(c>strand){strand=c;bestPh=ph;}
  const truth=t.test.map((te:any)=>te.output.length+"x"+te.output[0].length+":"+te.output.flat().join(",")).join("|");
  recs.push({id:t.id,solvers,strand,correct:bestPh===truth}); rec("multistrand",t.id,bestPh===truth?"solved":"overfit");
  if((i+1)%10===0)process.stderr.write("["+(i+1)+"] tasks="+recs.length+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),recs}));
rep();
