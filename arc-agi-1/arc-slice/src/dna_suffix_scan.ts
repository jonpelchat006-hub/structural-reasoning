// dna_suffix_scan.ts — §19.6 fix: SEMI-CONSERVATIVE replication check on the INVERTIBLE SUFFIX only.
// §19's whole-genome complementarity gate never fired (ARC genomes are mostly non-invertible). Per §18.3,
// the honest check is on the reversible part: take the maximal trailing run of invertible genes, reverse-
// complement it, apply to the OUTPUT, and require it to template back to the MID state (= prefix(input)).
// dsLen = the longest such suffix that templates (0 = single-stranded). We MEASURE whether dsLen>=1
// predicts test survival — the direct test of "does replication predict generalization" (cf. §18.19).
// Resumable: START END [state] [budgetSec].
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const BASES=["A","C","G","U"];
const codonOf=(op:string)=>{let i=OP_NAMES.indexOf(op);if(i<0)i=63;return BASES[(i>>4)&3]+BASES[(i>>2)&3]+BASES[i&3];};
const genomeCodons=(g:Genome)=>g.map(([o])=>codonOf(o)).join("");
function invGene(gn:Gene):Gene|null{ const[o,p]=gn;
  switch(o){ case "identity":case "flipH":case "flipV":case "transpose":case "antiTranspose":return[o,p];
    case "rotate":{const ik=(4-((p.k||0)%4))%4; return ik===0?["identity",{}]:["rotate",{k:ik}];}
    case "swap":return["swap",p];
    case "recolor":return["recolor",{from:p.to,to:p.from}];
    default:return null; } }
const buildFn=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
// longest invertible trailing suffix that templates output→mid across all train pairs (0 if none)
function dsSuffixLen(g:Genome,train:any[]):number{
  let run=0; for(let i=g.length-1;i>=0&&invGene(g[i]);i--)run++; // maximal trailing invertible run
  for(let L=run;L>=1;L--){ const prefix=g.slice(0,g.length-L), suffix=g.slice(g.length-L);
    const inv:Genome=[]; for(let i=suffix.length-1;i>=0;i--)inv.push(invGene(suffix[i])!);
    const P=buildFn(prefix), R=buildFn(inv);
    if(train.every((p:any)=>{const mid=P(p.input); if(!mid)return false; const back=R(p.output); return back&&eqG(back,mid);})) return L;
  } return 0; }
function score(gs:(Grid|null)[],outs:Grid[]):number{ let s=0;
  for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i]; if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
    let eq=0,tot=g.length*g[0].length; for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++; s+=eq/tot; }
  return s/gs.length; }
const rnd=(n:number)=>Math.floor(Math.random()*n);
function randGene(pal:number[]):Gene{const o=OP_NAMES[rnd(OP_NAMES.length)];let ps:any[];try{ps=(OPS as any)[o].enumerate(pal);}catch{ps=[{}];}if(!ps||!ps.length)ps=[{}];return[o,ps[rnd(ps.length)]];}
function randGenome(pal:number[],m:number):Genome{const n=1+rnd(m);const g:Genome=[];for(let i=0;i<n;i++)g.push(randGene(pal));return g;}
function mutate(g:Genome,pal:number[],m:number):Genome{const c=g.map(x=>[x[0],{...x[1]}] as Gene);const r=Math.random();if(r<0.4&&c.length)c[rnd(c.length)]=randGene(pal);else if(r<0.7&&c.length<m)c.splice(rnd(c.length+1),0,randGene(pal));else if(r<0.85&&c.length>1)c.splice(rnd(c.length),1);else if(c.length){const i=rnd(c.length),j=rnd(c.length);[c[i],c[j]]=[c[j],c[i]];}return c;}
function crossover(a:Genome,b:Genome):Genome{const i=rnd(a.length+1),j=rnd(b.length+1);return[...a.slice(0,i),...b.slice(j)].slice(0,8);}
function evolve(train:any[]):{prog:((g:Grid)=>Grid|null)|null;genome:Genome|null}{
  if(train.length<2||train.some((p:any)=>p.input.length*p.input[0].length>460))return{prog:null,genome:null};
  const pal=taskPalette(train),outs=train.map((p:any)=>p.output);
  let P:Genome[]=Array.from({length:60},()=>randGenome(pal,5));
  const fit=(g:Genome)=>score(train.map((p:any)=>buildFn(g)(p.input)),outs);
  for(let gen=0;gen<40;gen++){ const sc=P.map(g=>({g,s:fit(g)})).sort((a,b)=>b.s-a.s); const bt=sc[0];
    if(bt.s>=1){const f=buildFn(bt.g); if(train.every((p:any)=>{const o=f(p.input);return o&&eqG(o,p.output);})&&!(bt.g.length===1&&bt.g[0][0]==="identity"))return{prog:f,genome:bt.g};}
    const el=sc.slice(0,Math.max(2,7)).map(x=>x.g); const nx:Genome[]=[...el];
    while(nx.length<60){const a=el[rnd(el.length)],b=el[rnd(el.length)];let ch=Math.random()<0.5?crossover(a,b):a.map(x=>[x[0],{...x[1]}] as Gene);if(Math.random()<0.8)ch=mutate(ch,pal,7);if(!ch.length)ch=[randGene(pal)];nx.push(ch);}
    P=nx; }
  return{prog:null,genome:null}; }

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/[\s]+/).flatMap(s=>s.match(/.{1,8}/g)||[])); // also splits the concatenated ids
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
let recs:{id:string;dsLen:number;survived:boolean;codons:string}[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));recs=s.recs;RESUME=s.next;}
const rep=()=>{ const ds=recs.filter(r=>r.dsLen>=1), ss=recs.filter(r=>r.dsLen===0);
  const sv=(a:any[])=>a.filter(r=>r.survived).length;
  console.log("\n=== §19.6 DNA SUFFIX-COMPLEMENT (semi-conservative) EVAL ["+START+","+END+") ===");
  console.log("phase-locked genomes: "+recs.length);
  console.log("DOUBLE-STRANDED (dsLen>=1): "+ds.length+"   test-survived: "+sv(ds)+"/"+ds.length+(ds.length?"  ("+(sv(ds)/ds.length*100).toFixed(0)+"%)":""));
  console.log("SINGLE-STRANDED (dsLen=0): "+ss.length+"   test-survived: "+sv(ss)+"/"+ss.length+(ss.length?"  ("+(sv(ss)/ss.length*100).toFixed(0)+"%)":""));
  const net=recs.filter(r=>r.survived&&!verified.has(r.id));
  console.log("NET-NEW: "+net.length+"   "+net.map(r=>r.id+"(dsLen="+r.dsLen+":"+r.codons+")").join(" ")); };
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,recs}));console.log("PAUSED at "+i+" solves="+recs.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let r:any={prog:null,genome:null}; try{r=evolve(t.train);}catch{}
  if(!r.prog||!r.genome)continue;
  const survived=t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);});
  const dsLen=dsSuffixLen(r.genome,t.train);
  recs.push({id:t.id,dsLen,survived,codons:genomeCodons(r.genome)}); rec("dna",t.id,survived?"solved":"overfit",r.genome!.map((x:any)=>x[0]).join(">"));
  if((i+1)%10===0)process.stderr.write("["+(i+1)+"] solves="+recs.length+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),recs}));
rep();
