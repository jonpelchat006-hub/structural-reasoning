// solvent_scan.ts — §46: THE SOLVENT QUATERNION (Jonathan + Double_Bounce). Water is two things = the two
// pools; a SOLVENT redefines what is EMPTY (medium) vs SOLUTE (object). Atoms tuned to bg=0 only dissolve
// in the "water" solvent; run the whole two-lake meet under each of 4 solvents and an atom that was
// insoluble (needed a non-zero background) becomes reactive. This is NEW REACH (candidates the bg=0 frame
// never generated), not a re-rank — the winning criterion (§42.2). Solvent s is applied by swapping s<->0
// (a bijection), running the bg=0 pipeline, and wrapping back: P_real = swap(s,0) ∘ P ∘ swap(s,0).
// Solvents = {0 water, most-common, border-ring, 2nd-most-common} — the solvent quaternion.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildW=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
const swapC=(g:Grid,a:number,b:number):Grid=>g.map(r=>r.map(v=>v===a?b:v===b?a:v));
const knots:{id:string;word:Genome}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","knots.json"),"utf8"));
const dustRaw=(fs.existsSync(path.join(__dirname,"..","dust.json"))?JSON.parse(fs.readFileSync(path.join(__dirname,"..","dust.json"),"utf8")).__cnt:{})||{};
const keyAll=(gs:Grid[])=>gs.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
const uniform=(v:number[])=>v.every(x=>x===v[0]);
function ring(g:Grid):number|null{const r=g.length,c=g[0].length;if(r<3||c<3)return null;const vs:number[]=[];
  for(let x=0;x<c;x++){vs.push(g[0][x]);vs.push(g[r-1][x]);}for(let y=1;y<r-1;y++){vs.push(g[y][0]);vs.push(g[y][c-1]);}return uniform(vs)?vs[0]:null;}
function commonColors(g:Grid):number[]{const m:Record<number,number>={};for(const r of g)for(const v of r)m[v]=(m[v]||0)+1;
  return Object.entries(m).sort((a,b)=>b[1]-a[1]).map(x=>+x[0]);}

// backward void-adjusted atoms (as §44)
type Back={label:string;reduce:(o:Grid)=>Grid|null;inverse:(o:Grid,M:Grid)=>Gene|null};
const BACKS:Back[]=[
  {label:"id",reduce:o=>o,inverse:()=>null},
  {label:"downscale",reduce:o=>{try{return (OPS as any).downscale.fn(o,{});}catch{return null;}},inverse:(o,M)=>{if(!M||!M.length)return null;const fy=o.length/M.length,fx=o[0].length/M[0].length;return Number.isInteger(fy)&&Number.isInteger(fx)&&(fy>1||fx>1)?["scale",{fy,fx}]:null;}},
  {label:"stripBorder",reduce:o=>{const c=ring(o);return c===null?null:o.slice(1,-1).map(r=>r.slice(1,-1));},inverse:o=>{const c=ring(o);return c===null?null:["addBorder",{col:c}];}},
  {label:"takeTile",reduce:o=>{for(const ny of[1,2,3])for(const nx of[1,2,3]){if(ny===1&&nx===1)continue;if(o.length%ny||o[0].length%nx)continue;const th=o.length/ny,tw=o[0].length/nx;const t=o.slice(0,th).map(r=>r.slice(0,tw));let ok=true;for(let a=0;a<ny&&ok;a++)for(let b=0;b<nx&&ok;b++)for(let y=0;y<th&&ok;y++)for(let x=0;x<tw;x++)if(o[a*th+y][b*tw+x]!==t[y][x]){ok=false;break;}if(ok)return t;}return null;},inverse:(o,M)=>{if(!M||!M.length)return null;const ny=o.length/M.length,nx=o[0].length/M[0].length;return Number.isInteger(ny)&&Number.isInteger(nx)&&(ny>1||nx>1)?["tile",{ny,nx,mirror:0}]:null;}},
];
function fwdMoves(pal:number[]){const mv:{frag:Genome;isK:boolean}[]=[];
  for(const k of knots)mv.push({frag:k.word,isK:true});
  const byOp:Record<string,Record<string,number>[]>={};
  for(const[key,n]of Object.entries(dustRaw as Record<string,number>)){if(n<2)continue;const op=key.slice(0,key.indexOf("|"));try{(byOp[op]=byOp[op]||[]).push(JSON.parse(key.slice(key.indexOf("|")+1)));}catch{}}
  for(const op of OP_NAMES){let ps:Record<string,number>[];try{ps=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ps=[{}];}
    if(byOp[op])for(const d of byOp[op])if(!ps.some(q=>JSON.stringify(q)===JSON.stringify(d)))ps.push(d);
    for(const p of ps)mv.push({frag:[[op,p]],isK:false});}return mv;}
const score=(gs:Grid[],os:Grid[])=>{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=os[i];
  if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
  let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;};
function forwardFrontier(inputs:Grid[],outs:Grid[],pal:number[],depth=2,beamW=22):Map<string,Genome>{
  const mv=fwdMoves(pal);const out=new Map<string,Genome>();out.set(keyAll(inputs),[]);
  type St={M:Grid[];word:Genome;s:number;hasK:boolean};let beam:St[]=[{M:inputs.slice(),word:[],s:score(inputs,outs),hasK:false}];const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];for(const st of beam)for(const m of mv){let g2:Grid[]=[],bad=false;
    for(const g of st.M){let c:Grid|null=g;for(const[o,p]of m.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
    if(bad)continue;const word=[...st.word,...m.frag],hasK=st.hasK||m.isK,k=keyAll(g2);if(seen.has(k))continue;seen.add(k);if(!out.has(k))out.set(k,word);next.push({M:g2,word,s:score(g2,outs),hasK});}
    next.sort((a,b)=>b.s-a.s);const wk=next.filter(x=>x.hasK).slice(0,Math.ceil(beamW/2));beam=[...wk,...next.filter(x=>!x.hasK).slice(0,beamW-wk.length)];if(!beam.length)break;}
  return out;}
// one solvent pass: inputs/outs already swapped into this solvent frame
function meetInFrame(inputs:Grid[],outs:Grid[],pal:number[]):Genome|null{
  let ff:Map<string,Genome>;try{ff=forwardFrontier(inputs,outs,pal);}catch{return null;}
  for(const b of BACKS){const Ms:Grid[]=[],ig:(Gene|null)[]=[];let ok=true;
    for(const o of outs){const M=b.reduce(o);if(!M){ok=false;break;}Ms.push(M);ig.push(b.inverse(o,M));}
    if(!ok)continue;const g0=ig[0];if(g0&&!ig.every(x=>x&&JSON.stringify(x)===JSON.stringify(g0)))continue;
    const inv:Genome=g0?[g0]:[];const fwd=ff.get(keyAll(Ms));if(fwd===undefined)continue;const full=[...fwd,...inv];if(!full.length)continue;
    if(inputs.every((g,i)=>{const o=buildW(full)(g);return o&&eqG(o,outs[i]);}))return full;}
  return null;}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §46 SOLVENT QUATERNION (two-lake meet under 4 background solvents) EVAL ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>340))continue;
  const inputs=t.train.map((p:any)=>p.input),outs=t.train.map((p:any)=>p.output);
  // THE SOLVENT QUATERNION: 4 candidate media
  const cc=commonColors(inputs[0]);const solvents=[...new Set([0,cc[0],ring(inputs[0])??-1,cc[1]??-1].filter(s=>s>=0))];
  let found:Genome|null=null,sw=-1;
  for(const s of solvents){if(found)break;
    const inF=s===0?inputs:inputs.map(g=>swapC(g,s,0)),outF=s===0?outs:outs.map(g=>swapC(g,s,0));
    const pal=taskPalette(inF.map((input,i)=>({input,output:outF[i]})) as any);
    let prog:Genome|null=null;try{prog=meetInFrame(inF,outF,pal);}catch{}
    if(prog){found=prog;sw=s;}}
  if(!found)continue;
  const s=sw,prog=found;
  const real=(g:Grid):Grid|null=>{const gi=s===0?g:swapC(g,s,0);const o=buildW(prog)(gi);return o?(s===0?o:swapC(o,s,0)):null;};
  if(!t.train.every((p:any)=>{const o=real(p.input);return o&&eqG(o,p.output);}))continue;
  if(t.test.every((te:any)=>{const o=real(te.input);return o&&eqG(o,te.output);})){closed++;net.push(t.id);hows.push(t.id+" solvent="+s+" "+prog.map(g=>g[0]).join("*"));rec("solvent",t.id,"solved");}
  else{trainOnly++;hows.push("OVERFIT "+t.id+" solvent="+s);rec("solvent",t.id,"overfit");}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
