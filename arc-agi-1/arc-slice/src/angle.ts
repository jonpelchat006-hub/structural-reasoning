// angle.ts — test the ANGULAR matter/antimatter decomposition.
// Task = target vector T (the change it demands). Action effect = E.
// matter = E·T̂ (along task), antimatter = |E_perp| (orthogonal "isn't"), tanθ = am/m.
// Hypothesis: solving actions sit at small θ; a near-miss's antimatter residual points
// at what the NEXT op must supply -> a principled 2-step coupling selector.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES as _ALL, applyOp } from "./dsl";
const _HEAVY=new Set(["mapObjects","mapTopK","fractal","nested","colorByShape","periodicFill","overlayPanels","combinePanels","connectObjects","completeDiag","stamp"]);
const OP_NAMES=_ALL.filter(n=>!_HEAVY.has(n));
import { taskPalette } from "./transfer";
import { equal } from "./grid";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data"));
const combined=new Set(fs.readFileSync(path.join(__dirname,"..","combined_solved.txt"),"utf8").trim().split(/\s+/));

// 12-d feature delta: 10 colour-count deltas + size-ratio + object-count delta
function counts(g:Grid){const c=new Array(10).fill(0);for(const r of g)for(const v of r)if(v<10)c[v]++;return c;}
function objFeat(g:Grid):number[]{
  const r=g.length,c=g[0].length; const seen=Array.from({length:r},()=>Array(c).fill(false));
  let nObj=0, largest=0, total=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==0)total++;
    if(g[y][x]!==0&&!seen[y][x]){ nObj++; let sz=0; const st:[number,number][]=[[y,x]]; seen[y][x]=true; const col=g[y][x];
      while(st.length){ const [cy,cx]=st.pop()!; sz++; for(const [dy,dx] of [[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=cy+dy,nx=cx+dx;
        if(ny<0||ny>=r||nx<0||nx>=c||seen[ny][nx]||g[ny][nx]!==col)continue; seen[ny][nx]=true; st.push([ny,nx]); } }
      largest=Math.max(largest,sz); } }
  return [nObj/8, total?largest/total:0];   // object count (normalized) + largest-object fraction
}
function spatial(g:Grid):number[]{
  const r=g.length,c=g[0].length; let sy=0,sx=0,m=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==0){ sy+=y/(r-1||1); sx+=x/(c-1||1); m++; } }
  const cy=m?sy/m:0.5, cx=m?sx/m:0.5;
  // symmetry-defect fractions (geometry-sensitive: flips/transpose change these)
  let dh=0,dv=0,dt=0,tot=0; for(let y=0;y<r;y++)for(let x=0;x<c;x++){ tot++;
    if(g[y][x]!==g[y][c-1-x]) dh++; if(g[y][x]!==g[r-1-y][x]) dv++; if(r===c && g[y][x]!==g[x][y]) dt++; }
  return [cy,cx, dh/tot, dv/tot, r===c?dt/tot:0];
}
function feat(inp:Grid,out:Grid):number[]{
  const n=inp.length*inp[0].length||1; const ci=counts(inp),co=counts(out);
  const v=co.map((x,k)=>(x-ci[k])/n);
  v.push((out.length*out[0].length - n)/n);            // size axis
  // ── LIFTED spatial dimension (z+1): geometry the colour/size vector is blind to ──
  const si=spatial(inp), so=spatial(out);
  for(let k=0;k<si.length;k++) v.push((so[k]-si[k]));
  // ── OBJECT axis (5th macro-axis): which-object / count selection ──
  const oi=objFeat(inp), oo=objFeat(out);
  for(let k=0;k<oi.length;k++) v.push((oo[k]-oi[k]));
  return v;                                             // 11(colour+size)+5(spatial)+2(object)=18-d
}
function addv(a:number[],b:number[]){return a.map((x,i)=>x+b[i]);}
function dot(a:number[],b:number[]){let s=0;for(let i=0;i<a.length;i++)s+=a[i]*b[i];return s;}
function norm(a:number[]){return Math.sqrt(dot(a,a));}
function angleCos(a:number[],b:number[]){const na=norm(a),nb=norm(b);if(na<1e-9||nb<1e-9)return 0;return dot(a,b)/(na*nb);}

function taskVec(train:any[]):number[]{let T=new Array(18).fill(0);for(const p of train)T=addv(T,feat(p.input,p.output));return T;}
function opEffect(train:any[],op:string,pr:any):{E:number[],apply:(g:Grid)=>Grid|null}|null{
  let E=new Array(18).fill(0); for(const p of train){let o:Grid|null=null;try{o=applyOp({name:op,params:pr} as any,p.input);}catch{} if(!o)return null; E=addv(E,feat(p.input,o));}
  return {E, apply:(g:Grid)=>{try{return applyOp({name:op,params:pr} as any,g);}catch{return null;}}};
}
function solves1(apply:(g:Grid)=>Grid|null,train:any[]){return train.every((p:any)=>{const o=apply(p.input);return o&&equal(o,p.output);});}

// ── validate geometry: angle of the BEST-aligned op for solved single-op tasks ──
let solvedAngles:number[]=[], cnt=0;
// ── 2-step angular synth: op1 by max cosθ to T; op2 by max cosθ to residual ──
let twoStep=0, netnew:string[]=[]; let i=0;
for(const t of tasks){ i++;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>380)) continue;
  const pal=taskPalette(t.train); const T=taskVec(t.train);
  // gather op1 effects
  const cands:{op:string,pr:any,E:number[],apply:any,cos:number}[]=[];
  for(const op of OP_NAMES){ let prs:any[]; try{prs=(OPS as any)[op].enumerate(pal).slice(0,3);}catch{prs=[{}];}
    for(const pr of prs){ const e=opEffect(t.train,op,pr); if(!e)continue; cands.push({op,pr,E:e.E,apply:e.apply,cos:angleCos(e.E,T)}); } }
  // single-op solve angle (sanity)
  for(const c of cands){ if(solves1(c.apply,t.train)){ solvedAngles.push(c.cos); cnt++; break; } }
  // pick top op1 by alignment, build residual, match op2
  const top1=cands.filter(c=>c.cos>0.2).sort((a,b)=>b.cos-a.cos).slice(0,6);
  let done=false;
  for(const c1 of top1){
    // residual R = T - E1 (the antimatter the first op leaves)
    const R=T.map((x,k)=>x-c1.E[k]);
    // intermediate train after op1
    const mid=t.train.map((p:any)=>c1.apply(p.input)); if(mid.some((g:Grid)=>!g))continue;
    const nt=t.train.map((p:any,k:number)=>({input:mid[k],output:p.output}));
    // op2 candidates ranked by cos to R
    const c2s:{apply:any,cos:number}[]=[];
    for(const op of OP_NAMES){ let prs:any[];try{prs=(OPS as any)[op].enumerate(taskPalette(nt)).slice(0,3);}catch{prs=[{}];}
      for(const pr of prs){ const e=opEffect(nt,op,pr); if(!e)continue; c2s.push({apply:e.apply,cos:angleCos(e.E,R)}); } }
    for(const c2 of c2s.filter(c=>c.cos>0.2).sort((a,b)=>b.cos-a.cos).slice(0,6)){
      const prog=(g:Grid)=>{const m=c1.apply(g);return m?c2.apply(m):null;};
      if(solves1(prog,t.train)){ const tp=t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&equal(o,te.output);});
        if(tp){ twoStep++; if(!combined.has(t.id)) netnew.push(t.id); done=true; break; } } }
    if(done)break;
  }
  if(i%100===0) process.stderr.write(`[${i}/400] 2step=${twoStep}\n`);
}
const mean=(a:number[])=>a.reduce((s,x)=>s+x,0)/(a.length||1);
console.log(`\nGEOMETRY CHECK: single-op solves found ${cnt}; mean cosθ(best-aligned solving op, T) = ${mean(solvedAngles).toFixed(3)}`);
console.log(`(cosθ≈1 ⇒ solving action is matter-aligned with task, validating the angular model)`);
console.log(`\nANGULAR 2-STEP: solved ${twoStep}; NET-NEW over combined-79: ${netnew.length}  ${netnew.join(" ")}`);
