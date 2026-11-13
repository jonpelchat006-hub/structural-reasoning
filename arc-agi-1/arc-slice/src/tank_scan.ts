// tank_scan.ts — §43: TWO LAKES / TAN-FLIP MEET (Jonathan). The torus has two sheets: the ascending
// (forward, rich: knots+dust) and the descending (the outside atoms underneath, run from the OUTPUT via
// the invertible/tan-flip that turns the imaginary descent into a real frame). They meet at an interface
// grid M; the "waves must match" = forward(input_i)=M_i=backward(output_i) on EVERY train pair at the
// SAME split (tan's two verification points = the pairs pinning the interface). Water levels don't touch:
// each stage stays a distinct floor; we accept only a clean meet, never a mix.
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

// ── the TAN-FLIP: invertible atoms, and their real-frame inverse (descending -> ascending) ──
const INV:[Gene,Gene][]=[
  [["rotate",{k:1}],["rotate",{k:3}]],[["rotate",{k:2}],["rotate",{k:2}]],[["rotate",{k:3}],["rotate",{k:1}]],
  [["flipH",{}],["flipH",{}]],[["flipV",{}],["flipV",{}]],[["transpose",{}],["transpose",{}]],
];
function invSwaps(pal:number[]):[Gene,Gene][]{const o:[Gene,Gene][]=[];for(const a of pal)for(const b of pal)if(a<b){const g:Gene=["swap",{a,b}];o.push([g,g]);}return o;}

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

// forward frontier: reachable intermediate grids M per pair, keyed by a shared word
function forwardFrontier(inputs:Grid[],outs:Grid[],pal:number[],depth=2,beamW=24):{word:Genome;M:Grid[]}[]{
  const mv=fwdMoves(pal);
  type St={M:Grid[];word:Genome;s:number;hasK:boolean};
  let beam:St[]=[{M:inputs.map(g=>g),word:[],s:score(inputs,outs),hasK:false}];
  const out:{word:Genome;M:Grid[]}[]=[{word:[],M:inputs.map(g=>g)}];
  const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];
    for(const st of beam)for(const m of mv){
      let g2:Grid[]=[],bad=false;
      for(const g of st.M){let c:Grid|null=g;for(const[o,p]of m.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
      if(bad)continue;
      const word=[...st.word,...m.frag],hasK=st.hasK||m.isK;
      const key=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
      if(seen.has(key))continue;seen.add(key);
      const s=score(g2,outs);next.push({M:g2,word,s,hasK});out.push({word,M:g2});
    }
    next.sort((a,b)=>b.s-a.s);
    const wk=next.filter(x=>x.hasK).slice(0,Math.ceil(beamW/2));
    beam=[...wk,...next.filter(x=>!x.hasK).slice(0,beamW-wk.length)];if(!beam.length)break;
  }
  return out;
}
// backward: peel invertible atoms off the OUTPUT (the descending sheet), producing target M' per pair
function backwardFrontier(outs:Grid[],pal:number[],depth=2):{word:Genome;Mp:Grid[]}[]{
  const inv=[...INV,...invSwaps(pal)];
  let layer:{word:Genome;Mp:Grid[]}[]=[{word:[],Mp:outs.map(g=>g)}];
  const out=[...layer];const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:typeof layer=[];
    for(const st of layer)for(const[fwd,inv2]of inv){
      let g2:Grid[]=[],bad=false;
      for(const g of st.Mp){let c:Grid|null=null;try{c=applyOp({name:inv2[0],params:inv2[1]} as any,g);}catch{}if(!c){bad=true;break;}g2.push(c);}
      if(bad)continue;
      const word=[fwd,...st.word]; // prepend: the forward op that this inverse undoes
      const key=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
      if(seen.has(key))continue;seen.add(key);
      next.push({word,Mp:g2});out.push({word,Mp:g2});
    }
    layer=next;if(!layer.length)break;
  }
  return out;
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §43 TWO-LAKES / TAN-FLIP MEET (fwd knots+dust  meet  bwd invertible) EVAL ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>340))continue;
  const inputs=t.train.map((p:any)=>p.input),outs=t.train.map((p:any)=>p.output),pal=taskPalette(t.train);
  let ff:any[]=[],bf:any[]=[];try{ff=forwardFrontier(inputs,outs,pal);bf=backwardFrontier(outs,pal);}catch{}
  if(!ff.length||!bf.length)continue;
  // MEET: a forward M matches a backward M' on ALL pairs -> the two lakes' waves coincide
  let found:{fwd:Genome;bwd:Genome}|null=null;
  const bmap=new Map<string,Genome>();
  for(const b of bf){const key=b.Mp.map((g:Grid)=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");if(!bmap.has(key))bmap.set(key,b.word);}
  for(const f of ff){if(found)break;if(!f.word.length)continue;
    const key=f.M.map((g:Grid)=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
    const bw=bmap.get(key);if(bw!==undefined){found={fwd:f.word,bwd:bw};}}
  if(!found)continue;
  const full=[...found.fwd,...found.bwd];const fn=buildW(full);
  if(!t.train.every((p:any)=>{const o=fn(p.input);return o&&eqG(o,p.output);}))continue;
  if(t.test.every((te:any)=>{const o=fn(te.input);return o&&eqG(o,te.output);})){
    closed++;net.push(t.id);hows.push(t.id+" = "+full.map(g=>g[0]).join(" * ")+"  (meet)");rec("tank",t.id,"solved");
  }else{trainOnly++;rec("tank",t.id,"overfit");}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
