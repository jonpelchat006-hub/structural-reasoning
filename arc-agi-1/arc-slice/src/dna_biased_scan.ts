// dna_biased_scan.ts — §30: THE PAYOFF TEST. Does seeding the solver from the §29 middle-shell reaction
// network (follow affinity edges = the reachable/returnable domain) beat uniform random search? Controlled:
// the SAME GA runs in mode "base" (uniform op sampling) vs "bias" (ops chosen by affinity to the previous op
// = walk the reaction network; genomes seeded as affine walks). Only the op-choice differs. argv: START END MODE.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildFn=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
function score(gs:(Grid|null)[],outs:Grid[]):number{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;}
// affinity from atom_cards (the §29 reaction network)
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(__dirname,"..",f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,Set<string>>={};
for(const c of CARDS) VAL[c.op]=new Set(c.valence||[]);
const aff=(a:string,b:string)=>a===b?0:[...(VAL[a]||[])].filter(x=>(VAL[b]||new Set()).has(x)).length;
const rnd=(n:number)=>Math.floor(Math.random()*n);
let BIAS=false;
function pickOp(prev?:string):string{
  if(!BIAS||!prev) return OP_NAMES[rnd(OP_NAMES.length)];
  // weight each op by affinity(prev,op)+0.3 — follow the reaction network (middle shell)
  const w=OP_NAMES.map(o=>aff(prev,o)+0.3); const tot=w.reduce((s,x)=>s+x,0); let r=Math.random()*tot;
  for(let i=0;i<OP_NAMES.length;i++){ r-=w[i]; if(r<=0) return OP_NAMES[i]; } return OP_NAMES[OP_NAMES.length-1];
}
function geneFor(op:string,pal:number[]):Gene{ let ps:any[]; try{ps=(OPS as any)[op].enumerate(pal);}catch{ps=[{}];} if(!ps||!ps.length)ps=[{}]; return[op,ps[rnd(ps.length)]]; }
function randGenome(pal:number[],m:number):Genome{ const n=1+rnd(m); const g:Genome=[]; let prev:string|undefined;
  for(let i=0;i<n;i++){ const op=pickOp(prev); g.push(geneFor(op,pal)); prev=op; } return g; }
function mutate(g:Genome,pal:number[],m:number):Genome{ const c=g.map(x=>[x[0],{...x[1]}] as Gene); const r=Math.random();
  if(r<0.4&&c.length){ const i=rnd(c.length); c[i]=geneFor(pickOp(i>0?c[i-1][0]:undefined),pal); }
  else if(r<0.7&&c.length<m){ const i=rnd(c.length+1); c.splice(i,0,geneFor(pickOp(i>0?c[i-1][0]:undefined),pal)); }
  else if(r<0.85&&c.length>1){ c.splice(rnd(c.length),1); }
  else if(c.length){ const i=rnd(c.length),j=rnd(c.length); [c[i],c[j]]=[c[j],c[i]]; } return c; }
function crossover(a:Genome,b:Genome):Genome{ const i=rnd(a.length+1),j=rnd(b.length+1); return[...a.slice(0,i),...b.slice(j)].slice(0,8); }
function evolve(train:any[]):Genome|null{
  if(train.length<2||train.some((p:any)=>p.input.length*p.input[0].length>460))return null;
  const pal=taskPalette(train),outs=train.map((p:any)=>p.output);
  let P:Genome[]=Array.from({length:60},()=>randGenome(pal,5));
  const fit=(g:Genome)=>score(train.map((p:any)=>buildFn(g)(p.input)),outs);
  for(let gen=0;gen<40;gen++){ const sc=P.map(g=>({g,s:fit(g)})).sort((a,b)=>b.s-a.s); const bt=sc[0];
    if(bt.s>=1){const f=buildFn(bt.g);if(train.every((p:any)=>{const o=f(p.input);return o&&eqG(o,p.output);})&&!(bt.g.length===1&&bt.g[0][0]==="identity"))return bt.g;}
    const el=sc.slice(0,7).map(x=>x.g); const nx:Genome[]=[...el];
    while(nx.length<60){const a=el[rnd(el.length)],b=el[rnd(el.length)];let ch=Math.random()<0.5?crossover(a,b):a.map(x=>[x[0],{...x[1]}] as Gene);if(Math.random()<0.8)ch=mutate(ch,pal,7);if(!ch.length)ch=[geneFor(pickOp(),pal)];nx.push(ch);}
    P=nx; }
  return null; }

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length), MODE=(process.argv[4]||"base");
BIAS = MODE==="bias";
let solved=0; const ids:string[]=[];
for(let i=START;i<Math.min(END,ev.length);i++){ const t=ev[i]; if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let g:Genome|null=null; try{g=evolve(t.train);}catch{}
  if(g){ solved++; ids.push(t.id); } }
console.log("MODE="+MODE+"  ["+START+","+END+")  phase-locked solves: "+solved+"   "+ids.join(","));
