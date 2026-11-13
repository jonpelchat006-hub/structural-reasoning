// fold_scan.ts — §32: the OUTER-SHELL FOLDING SOLVER with the BALANCE acceptance rule (§31).
// The outer shell is not statically supported: a lone point unbalances the spin (§31.2). So a per-task
// answer must be a BALANCED ASSEMBLY, not a single program. We generate K independent strands (the swarm),
// then accept a test-prediction ONLY IF: (a) UNANIMITY — >=2 strands AGREE on it (counterweights around the
// shell), AND (b) TORQUE-FREE — the agreeing set SPANS >=SPAN_MIN of the 5 property-dimensions (points in
// all directions, §23.4/§31.4). Lone or narrow points are rejected. Test: does balance beat lone acceptance
// on PRECISION (fewer overfits accepted)? Resumable: START END [state] [budgetSec].
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildFn=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
function score(gs:(Grid|null)[],outs:Grid[]):number{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;}
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(__dirname,"..",f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,string[]>={}; for(const c of CARDS) VAL[c.op]=(c.valence||[]);
const spanOf=(g:Genome)=>{const d=new Set<string>(); for(const[o]of g) for(const v of (VAL[o]||[])) d.add(v); return d.size;};
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
const pheno=(g:Genome,test:any[]):string|null=>{const f=buildFn(g);const o=test.map((te:any)=>f(te.input));if(o.some(x=>!x))return null;return o.map(x=>x!.length+"x"+x![0].length+":"+x!.flat().join(",")).join("|");};

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, K=+(process.argv[6]||3), SPAN_MIN=4, T0=Date.now();
let recs:{id:string;loneOK:boolean;balanced:boolean;balOK:boolean}[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));recs=s.recs;RESUME=s.next;}
const rep=()=>{
  const lone=recs; const bal=recs.filter(r=>r.balanced);
  const loneOK=lone.filter(r=>r.loneOK).length, balOK=bal.filter(r=>r.balOK).length;
  console.log("\n=== §32 FOLD — balance acceptance (K="+K+", span>="+SPAN_MIN+") ["+START+","+END+") ===");
  console.log("tasks with a strand: "+recs.length);
  console.log("LONE accept (any single strand): accepted="+lone.length+"  correct="+loneOK+"  precision="+(lone.length?(100*loneOK/lone.length).toFixed(0):"0")+"%");
  console.log("BALANCED accept (>=2 agree AND span>="+SPAN_MIN+"): accepted="+bal.length+"  correct="+balOK+"  precision="+(bal.length?(100*balOK/bal.length).toFixed(0):"0")+"%   (abstains on "+(recs.length-bal.length)+" lone/narrow points)");
};
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,recs}));console.log("PAUSED at "+i+" recs="+recs.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  const strands:Genome[]=[]; for(let k=0;k<K;k++){ let g:Genome|null=null; try{g=evolve(t.train);}catch{} if(g)strands.push(g); }
  if(!strands.length)continue;
  const truth=t.test.map((te:any)=>te.output.length+"x"+te.output[0].length+":"+te.output.flat().join(",")).join("|");
  // LONE = the first strand's prediction
  const lonePh=pheno(strands[0],t.test); const loneOK=lonePh===truth;
  // BALANCED = largest agreeing cluster; require size>=2 AND the cluster's union span>=SPAN_MIN
  const groups:Record<string,Genome[]>={}; for(const g of strands){ const ph=pheno(g,t.test); if(!ph)continue; (groups[ph]=groups[ph]||[]).push(g); }
  let bestPh="", best:Genome[]=[]; for(const[ph,gs]of Object.entries(groups)) if(gs.length>best.length){best=gs;bestPh=ph;}
  const unionSpan=new Set<string>(); for(const g of best) for(const[o]of g) for(const v of (VAL[o]||[])) unionSpan.add(v);
  const balanced = best.length>=2 && unionSpan.size>=SPAN_MIN;
  recs.push({id:t.id, loneOK, balanced, balOK: balanced && bestPh===truth});
  if((i+1)%10===0)process.stderr.write("["+(i+1)+"] recs="+recs.length+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),recs}));
rep();
