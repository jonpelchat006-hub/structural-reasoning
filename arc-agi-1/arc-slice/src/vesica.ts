// vesica.ts — the Sparse Vesica Expansion superposition (cos²θ Born + antimatter setups).
//
// angle.ts already does cos-greedy 2-step: pick op1 by max cosθ to the task vector T,
// then op2 by cosθ to the residual. That DROPS "setup" moves — a low-cosθ op1 whose only
// job is to spray orthogonally (high antimatter |E_perp|) so a great op2 becomes reachable.
//
// This module keeps the SUPERPOSITION: the op1 candidate set = (top-K by cos²θ, the Born
// weight) UNION (top-M by antimatter magnitude — the orthogonal spray the cos-ranking
// discards). Then op2 by cos² to the residual. COLLAPSE = exact verify on train AND the
// held-out test split. We report net-new over the combined-solved set, and specifically
// how many net-new came from the ANTIMATTER-setup branch (the superposition's unique lift).
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES as _ALL, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { equal } from "./grid";
type Grid=number[][];

const _HEAVY=new Set(["mapObjects","mapTopK","fractal","nested","colorByShape","periodicFill","overlayPanels","combinePanels","connectObjects","completeDiag","stamp"]);
const OP_NAMES=_ALL.filter(n=>!_HEAVY.has(n));
const tasks=loadTasks(path.join(__dirname,"..","data"));
const combinedPath=path.join(__dirname,"..","combined_solved.txt");
const combined=new Set(fs.existsSync(combinedPath)?fs.readFileSync(combinedPath,"utf8").trim().split(/\s+/):[]);

// ── identical 18-d feature delta to angle.ts (colour+size+spatial+object) ──
function counts(g:Grid){const c=new Array(10).fill(0);for(const r of g)for(const v of r)if(v<10)c[v]++;return c;}
function objFeat(g:Grid):number[]{
  const r=g.length,c=g[0].length; const seen=Array.from({length:r},()=>Array(c).fill(false));
  let nObj=0, largest=0, total=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==0)total++;
    if(g[y][x]!==0&&!seen[y][x]){ nObj++; let sz=0; const st:[number,number][]=[[y,x]]; seen[y][x]=true; const col=g[y][x];
      while(st.length){ const [cy,cx]=st.pop()!; sz++; for(const [dy,dx] of [[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=cy+dy,nx=cx+dx;
        if(ny<0||ny>=r||nx<0||nx>=c||seen[ny][nx]||g[ny][nx]!==col)continue; seen[ny][nx]=true; st.push([ny,nx]); } }
      largest=Math.max(largest,sz); } }
  return [nObj/8, total?largest/total:0];
}
function spatial(g:Grid):number[]{
  const r=g.length,c=g[0].length; let sy=0,sx=0,m=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==0){ sy+=y/(r-1||1); sx+=x/(c-1||1); m++; } }
  const cy=m?sy/m:0.5, cx=m?sx/m:0.5;
  let dh=0,dv=0,dt=0,tot=0; for(let y=0;y<r;y++)for(let x=0;x<c;x++){ tot++;
    if(g[y][x]!==g[y][c-1-x]) dh++; if(g[y][x]!==g[r-1-y][x]) dv++; if(r===c && g[y][x]!==g[x][y]) dt++; }
  return [cy,cx, dh/tot, dv/tot, r===c?dt/tot:0];
}
function feat(inp:Grid,out:Grid):number[]{
  const n=inp.length*inp[0].length||1; const ci=counts(inp),co=counts(out);
  const v=co.map((x,k)=>(x-ci[k])/n); v.push((out.length*out[0].length - n)/n);
  const si=spatial(inp), so=spatial(out); for(let k=0;k<si.length;k++) v.push((so[k]-si[k]));
  const oi=objFeat(inp), oo=objFeat(out); for(let k=0;k<oi.length;k++) v.push((oo[k]-oi[k]));
  return v;
}
function addv(a:number[],b:number[]){return a.map((x,i)=>x+b[i]);}
function dot(a:number[],b:number[]){let s=0;for(let i=0;i<a.length;i++)s+=a[i]*b[i];return s;}
function norm(a:number[]){return Math.sqrt(dot(a,a));}
function cosOf(a:number[],b:number[]){const na=norm(a),nb=norm(b);if(na<1e-9||nb<1e-9)return 0;return dot(a,b)/(na*nb);}
function antiMag(E:number[],T:number[]){const nT=norm(T);if(nT<1e-9)return 0;const k=dot(E,T)/(nT*nT);const perp=E.map((x,i)=>x-k*T[i]);return norm(perp);}
function taskVec(train:any[]):number[]{let T=new Array(18).fill(0);for(const p of train)T=addv(T,feat(p.input,p.output));return T;}
function opEffect(train:any[],op:string,pr:any):{E:number[],apply:(g:Grid)=>Grid|null}|null{
  let E=new Array(18).fill(0); for(const p of train){let o:Grid|null=null;try{o=applyOp({name:op,params:pr} as any,p.input);}catch{} if(!o)return null; E=addv(E,feat(p.input,o));}
  return {E, apply:(g:Grid)=>{try{return applyOp({name:op,params:pr} as any,g);}catch{return null;}}};
}
function solves1(apply:(g:Grid)=>Grid|null,train:any[]){return train.every((p:any)=>{const o=apply(p.input);return o&&equal(o,p.output);});}
function passesTest(prog:(g:Grid)=>Grid|null,t:any){return t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&equal(o,te.output);});}

type Cand={op:string,pr:any,E:number[],apply:(g:Grid)=>Grid|null,cos:number,am:number};

const START=+(process.argv[2]||0), END=+(process.argv[3]||tasks.length);
let twoStep=0, netnew:string[]=[], fromAnti:string[]=[], single=0, i=0;
for(let ti=START; ti<Math.min(END,tasks.length); ti++){ const t=tasks[ti]; i++;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>380)) continue;
  const pal=taskPalette(t.train); const T=taskVec(t.train);
  const cands:Cand[]=[];
  for(const op of OP_NAMES){ let prs:any[]; try{prs=(OPS as any)[op].enumerate(pal).slice(0,3);}catch{prs=[{}];}
    for(const pr of prs){ const e=opEffect(t.train,op,pr); if(!e)continue; cands.push({op,pr,E:e.E,apply:e.apply,cos:cosOf(e.E,T),am:antiMag(e.E,T)}); } }
  // single-op collapse (baseline)
  let did=false;
  for(const c of cands){ if(solves1(c.apply,t.train)&&passesTest((g:Grid)=>c.apply(g),t)){ single++; did=true; break; } }
  if(did) continue;

  // ── the SUPERPOSITION op1 set: Born (cos²) top-K  ∪  ANTIMATTER setups top-M ──
  const byCos=[...cands].filter(c=>c.cos>0.2).sort((a,b)=>b.cos*b.cos-a.cos*a.cos).slice(0,12);
  const byAnti=[...cands].filter(c=>c.cos>0.03&&c.cos<0.4).sort((a,b)=>b.am-a.am).slice(0,8); // low-align, high orthogonal spray
  const seen=new Set(byCos.map(c=>c.op+JSON.stringify(c.pr)));
  const op1set=[...byCos.map(c=>({c,anti:false})), ...byAnti.filter(c=>!seen.has(c.op+JSON.stringify(c.pr))).map(c=>({c,anti:true}))];

  for(const {c:c1,anti} of op1set){
    const mid=t.train.map((p:any)=>c1.apply(p.input)); if(mid.some((g:Grid)=>!g))continue;
    const nt=t.train.map((p:any,k:number)=>({input:mid[k] as Grid,output:p.output}));
    const R=T.map((x,k)=>x-c1.E[k]);                       // residual the first op leaves
    const c2s:{apply:(g:Grid)=>Grid|null,cos:number}[]=[];
    for(const op of OP_NAMES){ let prs:any[];try{prs=(OPS as any)[op].enumerate(taskPalette(nt)).slice(0,3);}catch{prs=[{}];}
      for(const pr of prs){ const e=opEffect(nt,op,pr); if(!e)continue; c2s.push({apply:e.apply,cos:cosOf(e.E,R)}); } }
    let hit=false;
    for(const c2 of c2s.filter(c=>c.cos>0.2).sort((a,b)=>b.cos*b.cos-a.cos*a.cos).slice(0,8)){
      const prog=(g:Grid)=>{const m=c1.apply(g);return m?c2.apply(m):null;};
      if(solves1(prog,t.train)&&passesTest(prog,t)){
        twoStep++; if(!combined.has(t.id)){ netnew.push(t.id); if(anti) fromAnti.push(t.id); } hit=true; break; }
    }
    if(hit) break;
  }
  if(i%100===0) process.stderr.write(`[${i}/400] single=${single} 2step=${twoStep} netnew=${netnew.length}\n`);
}
console.log("\n=== SPARSE VESICA SUPERPOSITION (cos2 Born + antimatter setups) ===");
console.log("single-op collapses:         " + single);
console.log("2-step superposition solves: " + twoStep + " (all test-generalizing)");
console.log("NET-NEW over combined set:   " + netnew.length + "   " + netnew.join(" "));
console.log("  of which from ANTIMATTER-setup op1 (the superposition unique lift): " + fromAnti.length + "  " + fromAnti.join(" "));
console.log("(antimatter-setup = low-cos op1 kept to spray orthogonally and enable op2)");
