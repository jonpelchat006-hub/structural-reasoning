// tank2_scan.ts — §44: FILLING THE SECOND LAKE (Jonathan). The descending sheet's atoms carry a VOID
// SLOT — an unbound param induced (void-line-adjusted) from the data at the tan-flip handoff, not
// enumerated. A generalized reduction on the OUTPUT yields the interface M, and its forward inverse is
// MINTED with the void-adjusted param: an invertible-GENERATIVE backward atom, the thing §43 lacked.
//   downscaleAuto(output)=M      -> inverse scale(fy,fx)   (fy,fx = output.dims / M.dims, induced)
//   stripUniformBorder(output)=M -> inverse addBorder(c)   (c = the ring colour, induced)
//   takeTile(output)=M           -> inverse tile(ny,nx)    (ny,nx = output.dims / tile.dims, induced)
//   crop-uniform-pad(output)=M   -> inverse pad(dy,dx,c)   (offset+colour induced)
// The imported generalized atom ("part of the web we need") + void adjustment = the exact inverse for
// THIS game. Meet: forward(input_i)=M_i=backward-reduce(output_i) on all pairs; program = fwd * inverse.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildW=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
const knots:{id:string;word:Genome}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","knots.json"),"utf8"));
const dustRaw=(fs.existsSync(path.join(__dirname,"..","dust.json"))?JSON.parse(fs.readFileSync(path.join(__dirname,"..","dust.json"),"utf8")).__cnt:{})||{};
const keyOf=(g:Grid)=>g.length+"x"+g[0].length+":"+g.flat().join("");
const keyAll=(gs:Grid[])=>gs.map(keyOf).join("|");

// ── the void-adjusted backward atoms: (reduce output -> M, mint the induced forward inverse) ──
type Back={label:string;reduce:(o:Grid)=>Grid|null;inverse:(o:Grid,M:Grid)=>Gene|null};
const uniform=(vals:number[])=>vals.every(v=>v===vals[0]);
function ring(g:Grid):number|null{const r=g.length,c=g[0].length;if(r<3||c<3)return null;
  const vs:number[]=[];for(let x=0;x<c;x++){vs.push(g[0][x]);vs.push(g[r-1][x]);}for(let y=1;y<r-1;y++){vs.push(g[y][0]);vs.push(g[y][c-1]);}
  return uniform(vs)?vs[0]:null;}
const BACKS:Back[]=[
  {label:"id",reduce:o=>o,inverse:()=>null}, // pure forward (meet at output itself)
  {label:"downscale",reduce:o=>{try{return (OPS as any).downscale.fn(o,{});}catch{return null;}},
    inverse:(o,M)=>{if(!M||M.length===0)return null;const fy=o.length/M.length,fx=o[0].length/M[0].length;
      return Number.isInteger(fy)&&Number.isInteger(fx)&&fy>=1&&fx>=1&&(fy>1||fx>1)?["scale",{fy,fx}]:null;}},
  {label:"stripBorder",reduce:o=>{const c=ring(o);if(c===null)return null;return o.slice(1,-1).map(r=>r.slice(1,-1));},
    inverse:(o)=>{const c=ring(o);return c===null?null:["addBorder",{col:c}];}},
  {label:"takeTile",reduce:o=>{ // if output is n copies of a tile, return the tile (try halves/thirds)
      for(const ny of [1,2,3])for(const nx of [1,2,3]){if(ny===1&&nx===1)continue;
        if(o.length%ny||o[0].length%nx)continue;const th=o.length/ny,tw=o[0].length/nx;
        const t=o.slice(0,th).map(r=>r.slice(0,tw));let ok=true;
        for(let a=0;a<ny&&ok;a++)for(let b=0;b<nx&&ok;b++)for(let y=0;y<th&&ok;y++)for(let x=0;x<tw;x++)if(o[a*th+y][b*tw+x]!==t[y][x]){ok=false;break;}
        if(ok)return t;}return null;},
    inverse:(o,M)=>{if(!M||M.length===0)return null;const ny=o.length/M.length,nx=o[0].length/M[0].length;
      return Number.isInteger(ny)&&Number.isInteger(nx)&&(ny>1||nx>1)?["tile",{ny,nx,mirror:0}]:null;}},
];

function fwdMoves(pal:number[]){const mv:{frag:Genome;isK:boolean}[]=[];
  for(const k of knots)mv.push({frag:k.word,isK:true});
  const byOp:Record<string,Record<string,number>[]>={};
  for(const[key,n]of Object.entries(dustRaw as Record<string,number>)){if(n<2)continue;const op=key.slice(0,key.indexOf("|"));try{(byOp[op]=byOp[op]||[]).push(JSON.parse(key.slice(key.indexOf("|")+1)));}catch{}}
  for(const op of OP_NAMES){let ps:Record<string,number>[];try{ps=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ps=[{}];}
    if(byOp[op])for(const d of byOp[op])if(!ps.some(q=>JSON.stringify(q)===JSON.stringify(d)))ps.push(d);
    for(const p of ps)mv.push({frag:[[op,p]],isK:false});}
  return mv;}
const score=(gs:Grid[],os:Grid[])=>{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=os[i];
  if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
  let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;};

function forwardFrontier(inputs:Grid[],outs:Grid[],pal:number[],depth=2,beamW=24):Map<string,Genome>{
  const mv=fwdMoves(pal);const out=new Map<string,Genome>();
  type St={M:Grid[];word:Genome;s:number;hasK:boolean};
  let beam:St[]=[{M:inputs.slice(),word:[],s:score(inputs,outs),hasK:false}];out.set(keyAll(inputs),[]);
  const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];
    for(const st of beam)for(const m of mv){let g2:Grid[]=[],bad=false;
      for(const g of st.M){let c:Grid|null=g;for(const[o,p]of m.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
      if(bad)continue;const word=[...st.word,...m.frag],hasK=st.hasK||m.isK,k=keyAll(g2);
      if(seen.has(k))continue;seen.add(k);if(!out.has(k))out.set(k,word);
      next.push({M:g2,word,s:score(g2,outs),hasK});}
    next.sort((a,b)=>b.s-a.s);const wk=next.filter(x=>x.hasK).slice(0,Math.ceil(beamW/2));
    beam=[...wk,...next.filter(x=>!x.hasK).slice(0,beamW-wk.length)];if(!beam.length)break;}
  return out;}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §44 SECOND LAKE (void-adjusted invertible-generative backward atoms) EVAL ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>340))continue;
  const inputs=t.train.map((p:any)=>p.input),outs=t.train.map((p:any)=>p.output),pal=taskPalette(t.train);
  let ff:Map<string,Genome>;try{ff=forwardFrontier(inputs,outs,pal);}catch{continue;}
  let found:Genome|null=null;
  for(const b of BACKS){if(found)break;
    // reduce each output; the induced inverse must be CONSISTENT across all pairs (one gene)
    const Ms:Grid[]=[];let ok=true;const invGenes:Gene[]=[];
    for(let k=0;k<outs.length;k++){const M=b.reduce(outs[k]);if(!M){ok=false;break;}Ms.push(M);
      const iv=b.inverse(outs[k],M);invGenes.push(iv as any);}
    if(!ok)continue;
    // inverse gene must be identical across pairs (the void slot resolves to ONE value = the game's rule)
    const ig=invGenes[0];const invWord:Genome=ig?[ig]:[];
    if(ig&&!invGenes.every(x=>x&&JSON.stringify(x)===JSON.stringify(ig)))continue;
    const mkey=keyAll(Ms);const fwd=ff.get(mkey);
    if(fwd===undefined)continue;if(!fwd.length&&!invWord.length)continue;
    const full=[...fwd,...invWord];const fn=buildW(full);
    if(!t.train.every((p:any)=>{const o=fn(p.input);return o&&eqG(o,p.output);}))continue;
    found=full;hows.push(t.id+" = ["+fwd.map(g=>g[0]).join("*")+"] meet ["+b.label+"->"+(ig?ig[0]:"id")+"]");break;}
  if(!found)continue;
  const fn=buildW(found);
  if(t.test.every((te:any)=>{const o=fn(te.input);return o&&eqG(o,te.output);})){closed++;net.push(t.id);rec("tank2",t.id,"solved");}
  else{trainOnly++;hows[hows.length-1]="OVERFIT "+hows[hows.length-1];rec("tank2",t.id,"overfit");}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
