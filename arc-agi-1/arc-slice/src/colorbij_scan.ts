// colorbij_scan.ts — §47: THE BIJECTION ATOM (Jonathan). A colour map that is a BIJECTION carries its own
// inverse — the map and its reverse are tan's TWO BRANCHES (the "2 answers"). When the generator rotates
// onto its tan line, the inverse recolour is BORN WITH IT (not searched). So the second lake's richest
// atom: at the interface M, LEARN the colour map M_i[y][x] -> output_i[y][x]; if it is a consistent
// FUNCTION across every pair and cell (a well-defined map, bijection when onto), mint it as a cmap and
// finish. The forward sheet reaches M up to colour; the learned bijection fixes the colours. This is the
// invertible-generative reduction the §43/§45/§46 mechanisms were all waiting on.
import * as path from "path"; import * as fs from "fs";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { loadTasks } from "./loader";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildW=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
const knots:{id:string;word:Genome}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","knots.json"),"utf8"));
const dustRaw=(fs.existsSync(path.join(__dirname,"..","dust.json"))?JSON.parse(fs.readFileSync(path.join(__dirname,"..","dust.json"),"utf8")).__cnt:{})||{};
const dimsEq=(a:Grid,b:Grid)=>a.length===b.length&&a[0].length===b[0].length;

// learn a consistent colour MAP M->out across all pairs (same-dims required); return cmap params or null
function learnCmap(Ms:Grid[],outs:Grid[]):Record<string,number>|null{
  const map:Record<number,number>={};
  for(let i=0;i<Ms.length;i++){const M=Ms[i],o=outs[i];if(!dimsEq(M,o))return null;
    for(let y=0;y<M.length;y++)for(let x=0;x<M[0].length;x++){const s=M[y][x],t=o[y][x];
      if(map[s]!==undefined){if(map[s]!==t)return null;}else map[s]=t;}}
  // must be non-identity (else the meet already closed) and a real recolour
  let nonId=false;const p:Record<string,number>={};for(const[s,t]of Object.entries(map)){p[s]=t;if(+s!==t)nonId=true;}
  return nonId?p:null;
}
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
// forward frontier returning (word, M per pair) entries — we scan them for a learnable bijection finisher
function frontier(inputs:Grid[],outs:Grid[],pal:number[],depth=2,beamW=22):{word:Genome;M:Grid[]}[]{
  const mv=fwdMoves(pal);const out:{word:Genome;M:Grid[]}[]=[];
  type St={M:Grid[];word:Genome;s:number;hasK:boolean};let beam:St[]=[{M:inputs.slice(),word:[],s:score(inputs,outs),hasK:false}];
  const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];for(const st of beam)for(const m of mv){let g2:Grid[]=[],bad=false;
    for(const g of st.M){let c:Grid|null=g;for(const[o,p]of m.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
    if(bad)continue;const word=[...st.word,...m.frag],hasK=st.hasK||m.isK,k=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
    if(seen.has(k))continue;seen.add(k);out.push({word,M:g2});next.push({M:g2,word,s:score(g2,outs),hasK});}
    next.sort((a,b)=>b.s-a.s);const wk=next.filter(x=>x.hasK).slice(0,Math.ceil(beamW/2));beam=[...wk,...next.filter(x=>!x.hasK).slice(0,beamW-wk.length)];if(!beam.length)break;}
  return out;}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §47 BIJECTION ATOM (forward frontier + learned colour-map finisher) EVAL ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>340))continue;
  const inputs=t.train.map((p:any)=>p.input),outs=t.train.map((p:any)=>p.output),pal=taskPalette(t.train);
  let fr:{word:Genome;M:Grid[]}[]=[];try{fr=frontier(inputs,outs,pal);}catch{}
  let found:Genome|null=null,cm:Record<string,number>|null=null;
  for(const e of fr){if(found)break;if(!e.M.every((g,i)=>dimsEq(g,outs[i])))continue;
    const cmap=learnCmap(e.M,outs);if(!cmap)continue;
    const full:Genome=[...e.word,["cmap",cmap]];
    if(inputs.every((g,i)=>{const o=buildW(full)(g);return o&&eqG(o,outs[i]);})){found=full;cm=cmap;}}
  if(!found)continue;const fn=buildW(found);
  if(t.test.every((te:any)=>{const o=fn(te.input);return o&&eqG(o,te.output);})){closed++;net.push(t.id);hows.push(t.id+" = "+found.slice(0,-1).map(g=>g[0]).join("*")+" * cmap"+JSON.stringify(cm));rec("colorbij",t.id,"solved");}
  else{trainOnly++;hows.push("OVERFIT "+t.id);rec("colorbij",t.id,"overfit");}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
