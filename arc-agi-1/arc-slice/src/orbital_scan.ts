// orbital_scan.ts — §34/§35: the ORBITAL / CONTINUOUS-PARAMETER closer (the quantum state).
// The residual is a QUANTUM STATE: *which orbital* (discrete — the anchor op-word we already have) PLUS
// *the phase within it* (continuous — the parameter value, induced from train). Four discrete attacks
// (§16b deepen, §17 bond, §18.7 lateral, §33 contract) gave +0 because they moved BETWEEN quantized
// levels (changed the op word). This closer stays IN the orbital: keep the anchor word, FREE the numbers
// inside it (bounce only ever tried enumerate().slice(0,4); shift only dy,dx∈[-2..2]), and fit them as:
//   CONST mode  — a constant the tiny enumeration missed (re-fit within the full domain), or
//   PHASE mode  — a LINEAR FUNCTION of an input feature (h,w,area,nonBg,nColors,nObj,maxObj), the §28
//                 derivative/function-not-table move, now applied INSIDE the orbital word.
// Quantization gate (de Broglie, §35.2): the wave must close — θ=1 on every train pair by construction,
// and the predicted test parameter must land on an INTEGER in the domain (non-integer = the wave doesn't
// close = abstain). CONST preferred over PHASE (minimal excess, θ→1 from above).
// Resumable: argv = START END [stateFile] [budgetSec]
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
import { taskPalette } from "./transfer";
import { components } from "./objects";
import { rec } from "./scan_recorder";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const build=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
const exact=(g:Genome,pairs:any[])=>{const f=build(g);return pairs.every((p:any)=>{const o=f(p.input);return o&&eqG(o,p.output);});};

// ── input features (observable on the test input) — the axis the phase can be a function of ──
const FEATS:[string,(g:Grid)=>number][]=[
  ["h",g=>g.length],["w",g=>g[0].length],["area",g=>g.length*g[0].length],
  ["nonBg",g=>g.flat().filter(v=>v!==0).length],
  ["nColors",g=>new Set(g.flat().filter(v=>v!==0)).size],
  ["nObj",g=>{try{return components(g,0,"blob").length;}catch{return 0;}}],
  ["maxObj",g=>{try{const cs=components(g,0,"blob");return cs.length?Math.max(...cs.map((c:any)=>c.cells.length)):0;}catch{return 0;}}],
];

// ── the FULL domain for one op's params (the orbital's continuous extent, vs the enumeration cap) ──
const KEY_RANGE:Record<string,(pal:number[],maxDim:number)=>number[]>={
  dy:(_,m)=>range(-Math.min(m-1,14),Math.min(m-1,14)), dx:(_,m)=>range(-Math.min(m-1,14),Math.min(m-1,14)),
  fy:()=>range(1,6), fx:()=>range(1,6), ny:()=>range(1,6), nx:()=>range(1,6),
  k:()=>range(1,6), min:()=>range(1,5), mask:()=>range(1,15),
  dir:()=>range(0,3), axis:()=>range(0,2), mode:()=>range(0,3), which:()=>range(0,3),
  by:()=>range(0,2), inner:()=>range(0,2), crit:()=>range(0,1),
  mirror:()=>range(0,1), inv:()=>range(0,1), crop:()=>range(0,1), vertical:()=>range(0,1),
};
const COLOR_KEYS=new Set(["from","to","c","bg","a","b","col","fill","out","marker"]);
function range(a:number,b:number){const o:number[]=[];for(let i=a;i<=b;i++)o.push(i);return o;}
function domainFor(op:string,anchorParams:Record<string,number>,pal:number[],maxDim:number):Record<string,number>[]{
  const keys=Object.keys(anchorParams); if(!keys.length)return[];
  const per:number[][]=keys.map(k=>{
    if(COLOR_KEYS.has(k))return pal.slice();
    if(KEY_RANGE[k])return KEY_RANGE[k](pal,maxDim);
    // fallback: distinct values this key takes in the op's own enumeration
    try{const vs=new Set<number>((OPS as any)[op].enumerate(pal).map((p:any)=>p[k]).filter((v:any)=>v!==undefined));return vs.size?[...vs]:[anchorParams[k]];}catch{return[anchorParams[k]];}
  });
  // cartesian product, capped
  let out:Record<string,number>[]=[{}];
  for(let i=0;i<keys.length;i++){const nx:Record<string,number>[]=[];
    for(const o of out)for(const v of per[i]){nx.push({...o,[keys[i]]:v});if(nx.length>2500)return nx;}
    out=nx;}
  return out;
}

// per-pair SOLUTION SET at position j: which param vectors make the WHOLE word close that pair exactly
function solutionSet(word:Genome,j:number,dom:Record<string,number>[],pair:any):Record<string,number>[]{
  const out:Record<string,number>[]=[];
  for(const v of dom){const g=word.slice();g[j]=[word[j][0],v];const f=build(g);const o=f(pair.input);
    if(o&&eqG(o,pair.output))out.push(v);}
  return out;
}
const vecEq=(a:Record<string,number>,b:Record<string,number>,keys:string[])=>keys.every(k=>a[k]===b[k]);

// ── the closer: given the anchor word, fit the phase at ONE position ──
function orbitalClose(word:Genome,train:any[],pal:number[]):{prog:(g:Grid)=>Grid|null;how:string}|null{
  const maxDim=Math.max(...train.flatMap((p:any)=>[p.input.length,p.input[0].length,p.output.length,p.output[0].length]));
  for(let j=0;j<word.length;j++){
    const keys=Object.keys(word[j][1]); if(!keys.length)continue;
    const dom=domainFor(word[j][0],word[j][1],pal,maxDim); if(!dom.length)continue;
    const S:Record<string,number>[][]=[];
    let ok=true;
    for(const p of train){const s=solutionSet(word,j,dom,p);if(!s.length){ok=false;break;}S.push(s);}
    if(!ok)continue;
    // CONST mode — one vector closes every pair (the enumeration-cap miss). Minimal excess: prefer it.
    for(const v of S[0]){ if(S.every(s=>s.some(u=>vecEq(u,v,keys)))){
      const g=word.slice();g[j]=[word[j][0],v];
      return{prog:build(g),how:"const@"+j+":"+word[j][0]+" "+JSON.stringify(v)};}}
    // PHASE mode — the param is a linear function of an input feature (needs the value to VARY)
    for(const[fname,ff]of FEATS){
      const fv=train.map((p:any)=>ff(p.input));
      // need two pairs with distinct feature values to define the line
      let p0=-1,p1=-1; for(let a=0;a<fv.length&&p0<0;a++)for(let b=a+1;b<fv.length;b++)if(fv[a]!==fv[b]){p0=a;p1=b;break;}
      if(p0<0)continue;
      for(const va of S[p0].slice(0,30))for(const vb of S[p1].slice(0,30)){
        // line per key through (fv[p0],va[k]) and (fv[p1],vb[k])
        const line:Record<string,[number,number]>={};let nonConst=false;
        for(const k of keys){const a=(vb[k]-va[k])/(fv[p1]-fv[p0]),b=va[k]-a*fv[p0];line[k]=[a,b];if(a!==0)nonConst=true;}
        if(!nonConst)continue; // that's the const case, already tried
        // QUANTIZATION GATE on train: every pair must have a solution vector ON the line (integer by set-membership)
        let all=true;
        const predAt=(f:number)=>{const v:Record<string,number>={};for(const k of keys){const p=line[k][0]*f+line[k][1];if(Math.abs(p-Math.round(p))>1e-9)return null;v[k]=Math.round(p);}return v;};
        for(let i=0;i<train.length;i++){const pv=predAt(fv[i]);if(!pv||!S[i].some(u=>vecEq(u,pv,keys))){all=false;break;}}
        if(!all)continue;
        const jj=j,w0=word,ln=line,ks=keys,fn=ff,op=word[j][0];
        const prog=(g:Grid):Grid|null=>{const f=fn(g);const v:Record<string,number>={};
          for(const k of ks){const p=ln[k][0]*f+ln[k][1];if(Math.abs(p-Math.round(p))>1e-9)return null;v[k]=Math.round(p);}
          const gg=w0.slice();gg[jj]=[op,v];return build(gg)(g);};
        return{prog,how:"phase@"+j+":"+op+" "+ks.map(k=>k+"="+line[k][0].toFixed(3)+"*"+fname+"+"+line[k][1].toFixed(3)).join(",")};
      }
    }
  }
  return null;
}

// ── runner (resumable, budgeted, same shape as prior scans) ──
const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length), STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
let base=0, closed=0, trainOnly=0, net:string[]=[], hows:string[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));base=s.base;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows||[];RESUME=s.next;}
const rep=()=>{console.log("\n=== §34/§35 ORBITAL closer (discrete word + continuous phase) EVAL ["+START+","+END+") ===");
  console.log("base (bounce already solved): "+base);
  console.log("closed by orbital phase: "+closed+"   train-closed-but-test-failed: "+trainOnly);
  console.log("NET-NEW vs verified_eval: "+net.length+"   "+net.join(" "));
  for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,base,closed,trainOnly,net,hows}));console.log("PAUSED at "+i+" base="+base+" closed="+closed+" trainOnly="+trainOnly+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r||!r.bestProg)continue;
  const anchor=r.bestProg as Genome, pal=taskPalette(t.train);
  if(exact(anchor,t.train)){if(exact(anchor,t.test))base++;continue;}
  let win:any=null; try{win=orbitalClose(anchor,t.train,pal);}catch{}
  if(!win||!win.prog)continue;
  if(!t.train.every((p:any)=>{const o=win.prog(p.input);return o&&eqG(o,p.output);}))continue; // θ=1 guard
  if(t.test.every((te:any)=>{const o=win.prog(te.input);return o&&eqG(o,te.output);})){
    closed++; rec("orbital",t.id,"solved",win.how); hows.push(t.id+" "+win.how);
    if(!verified.has(t.id))net.push(t.id);
  } else { trainOnly++; rec("orbital",t.id,"overfit",win.how); hows.push(t.id+" OVERFIT "+win.how); }
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] base="+base+" closed="+closed+" trainOnly="+trainOnly+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),base,closed,trainOnly,net,hows}));
rep();
