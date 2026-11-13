// isotope_scan.ts — §18.19: the VOID PERIODIC TABLE. Every train-closing closure map is a SYNTHESIZED
// ISOTOPE; whether it also closes test = whether it survives the flight path to the detector. This pass
// records EVERY isotope (all pre × mode × ray-pair configs that close train, not just the first) with its
// configuration features, then aggregates survival (half-life) per FAMILY. Families with short half-lives
// need stricter acceptance; a config that re-synthesizes identically across tasks marks an island of
// stability (a missing floor atom). Output: isotope_table.json + summary.
// Resumable: argv = START END [stateFile] [budgetSec].
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const build=(prog:[string,any][])=>(g:Grid)=>{let c:Grid|null=g;for(const[o,p]of prog){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
const DIRS:[number,number][]=[[-1,0],[1,0],[0,1],[0,-1],[-1,1],[-1,-1],[1,1],[1,-1]];
const adjAt=(g:Grid,y:number,x:number,d:number)=>{const[dy,dx]=DIRS[d],ny=y+dy,nx=x+dx;return(ny<0||ny>=g.length||nx<0||nx>=g[0].length)?-1:g[ny][nx];};
const rayAt=(g:Grid,y:number,x:number,d:number)=>{const[dy,dx]=DIRS[d];let ny=y+dy,nx=x+dx;while(ny>=0&&ny<g.length&&nx>=0&&nx<g[0].length){if(g[ny][nx]!==0)return g[ny][nx];ny+=dy;nx+=dx;}return 0;};
function learnClosure(aligned:Grid[],outs:Grid[],d1:number,d2:number,nb:(g:Grid,y:number,x:number,d:number)=>number):Map<string,number>|null{
  const M=new Map<string,number>();
  for(let i=0;i<aligned.length;i++){const a=aligned[i],o=outs[i];
    for(let y=0;y<a.length;y++)for(let x=0;x<a[0].length;x++){ if(a[y][x]===o[y][x])continue;
      const k=a[y][x]+"|"+nb(a,y,x,d1)+"|"+nb(a,y,x,d2); const p=M.get(k); if(p!==undefined&&p!==o[y][x])return null; M.set(k,o[y][x]); }}
  if(!M.size)return null;
  for(let i=0;i<aligned.length;i++){const a=aligned[i],o=outs[i];
    for(let y=0;y<a.length;y++)for(let x=0;x<a[0].length;x++){ if(a[y][x]!==o[y][x])continue;
      const k=a[y][x]+"|"+nb(a,y,x,d1)+"|"+nb(a,y,x,d2); const v=M.get(k); if(v!==undefined&&v!==o[y][x])return null; }}
  const byCell=new Map<string,Set<number>>();
  for(const[k,v]of M){const c=k.split("|")[0];if(!byCell.has(c))byCell.set(c,new Set());byCell.get(c)!.add(v);}
  if(![...byCell.values()].some(s=>s.size>1))return null;
  return M;
}
const applyClosure=(M:Map<string,number>,d1:number,d2:number,nb:(g:Grid,y:number,x:number,d:number)=>number)=>(g:Grid):Grid=>{
  const o=g.map(r=>r.slice());
  for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++){const v=M.get(g[y][x]+"|"+nb(g,y,x,d1)+"|"+nb(g,y,x,d2));if(v!==undefined)o[y][x]=v;}
  return o;
};
// ray-pair GEOMETRY = the family's block: single / opposed / orthogonal / oblique
const geom=(d1:number,d2:number)=>{ if(d1===d2)return "single";
  const[a,b]=DIRS[d1],[c,d]=DIRS[d2]; if(a===-c&&b===-d)return "opposed"; if(a*c+b*d===0)return "orthogonal"; return "oblique"; };

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
const OUT=path.join(__dirname,"..","isotope_table.json");
const NBMODES:[string,(g:Grid,y:number,x:number,d:number)=>number][]=[["adj",adjAt],["ray",rayAt]];
type Iso={task:string;pre:string;anchorOps:string[];anchorScore:number;mode:string;d1:number;d2:number;geom:string;mapSize:number;residualCells:number;mapSig:string;survived:boolean};
let isotopes:Iso[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));isotopes=s.isotopes;RESUME=s.next;}
const save=(next:number)=>{if(STATE)fs.writeFileSync(STATE,JSON.stringify({next,isotopes}));};
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){save(i);console.log("PAUSED at "+i+" isotopes="+isotopes.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r)continue;
  if(r.prog&&t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);}))continue; // base-solved: not an isotope
  const pres:[string,(g:Grid)=>Grid|null,string[]][]=[["id",(g:Grid)=>g,[]]];
  if(r.bestProg)pres.unshift(["anchor",build(r.bestProg as [string,any][]),(r.bestProg as [string,any][]).map(p=>p[0])]);
  for(const[pnm,pre,ops]of pres){
    const aligned:Grid[]=[]; let ok=true;
    for(const p of t.train){const a=pre(p.input);if(!a||a.length!==p.output.length||a[0].length!==p.output[0].length){ok=false;break;}aligned.push(a);}
    if(!ok)continue;
    const outs=t.train.map((p:any)=>p.output);
    if(aligned.every((a,j)=>eqG(a,outs[j])))continue;
    let residual=0; for(let j=0;j<aligned.length;j++){const a=aligned[j],o=outs[j];for(let y=0;y<a.length;y++)for(let x=0;x<a[0].length;x++)if(a[y][x]!==o[y][x])residual++;}
    for(const[mnm,nb]of NBMODES)for(let d1=0;d1<8;d1++)for(let d2=d1;d2<8;d2++){
      const M=learnClosure(aligned,outs,d1,d2,nb); if(!M)continue;
      const C=applyClosure(M,d1,d2,nb);
      const cand=(g:Grid)=>{const a=pre(g);return a?C(a):null;};
      if(!t.train.every((p:any)=>{const o=cand(p.input);return o&&eqG(o,p.output);}))continue; // must close train = synthesized
      const survived=t.test.every((te:any)=>{const o=cand(te.input);return o&&eqG(o,te.output);});
      const mapSig=[...M.entries()].sort().map(([k,v])=>k+">"+v).join(",");
      isotopes.push({task:t.id,pre:pnm,anchorOps:ops,anchorScore:+r.bestScore.toFixed(4),mode:mnm,d1,d2,geom:geom(d1,d2),mapSize:M.size,residualCells:residual,mapSig,survived});
    }}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] isotopes="+isotopes.length+"\n");
}
save(Math.min(END,ev.length));
// ── aggregate: the periodic table ──
const fam=new Map<string,{n:number;surv:number;tasks:Set<string>}>();
for(const iso of isotopes){ const f=iso.pre+"/"+iso.mode+"/"+iso.geom;
  if(!fam.has(f))fam.set(f,{n:0,surv:0,tasks:new Set()}); const e=fam.get(f)!; e.n++; if(iso.survived)e.surv++; e.tasks.add(iso.task); }
// island-of-stability detector: identical mapSig re-synthesized across DIFFERENT tasks
const sig=new Map<string,Set<string>>();
for(const iso of isotopes){ if(!sig.has(iso.mapSig))sig.set(iso.mapSig,new Set()); sig.get(iso.mapSig)!.add(iso.task); }
const stable=[...sig.entries()].filter(([,s])=>s.size>1).map(([k,s])=>({tasks:[...s],mapSig:k.slice(0,120)}));
fs.writeFileSync(OUT,JSON.stringify({generated:new Date().toISOString(),range:[START,END],isotopes,families:[...fam.entries()].map(([f,e])=>({family:f,synthesized:e.n,survived:e.surv,halfLife:+(e.surv/e.n).toFixed(3),tasks:e.tasks.size})),islandsOfStability:stable},null,1));
console.log("\n=== §18.19 ISOTOPE TABLE ["+START+","+END+") — "+isotopes.length+" isotopes, "+new Set(isotopes.map(i=>i.task)).size+" tasks ===");
for(const[f,e]of [...fam.entries()].sort((a,b)=>b[1].n-a[1].n)) console.log(f.padEnd(24)+" synthesized="+String(e.n).padStart(4)+"  survived="+String(e.surv).padStart(3)+"  survival="+(e.surv/e.n).toFixed(3)+"  tasks="+e.tasks.size);
console.log("islands of stability (same map, different tasks): "+stable.length);
console.log("wrote isotope_table.json");
