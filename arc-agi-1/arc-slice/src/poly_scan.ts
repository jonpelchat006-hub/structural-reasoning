// poly_scan.ts — §39: the POLYNOMIAL LADDER (Jonathan). Floor number = polynomial order (the §1 expansion
// made literal: exponents ARE derivative orders). Inner-shell atoms stay SINGLE and WARM (param-less
// constants — D4 has nothing to lift) and merge at the next level; middle-shell atoms arrive PAIRED and
// FROZEN, and it is their params that get lifted to FUNCTIONS. Level 2 = a 1st-order polynomial with
// constants (param = a*f + b, exactly §36's phase); level 3 = 2nd order (quadratic in the feature).
// Gates scale with order (§36.4): order 1 needs >=3 distinct feature values on train, order 2 needs >=4 —
// the coefficients must be OVER-constrained, not merely fit. Anchor = the KNOT-beam near-miss (the §37
// mixed beam with mass), flattened to one genome before lifting.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { components } from "./objects";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const build=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};

const FEATS:[string,(g:Grid)=>number][]=[
  ["h",g=>g.length],["w",g=>g[0].length],["area",g=>g.length*g[0].length],
  ["nonBg",g=>g.flat().filter(v=>v!==0).length],
  ["nColors",g=>new Set(g.flat().filter(v=>v!==0)).size],
  ["nObj",g=>{try{return components(g,0,"blob").length;}catch{return 0;}}],
  ["maxObj",g=>{try{const cs=components(g,0,"blob");return cs.length?Math.max(...cs.map((c:any)=>c.cells.length)):0;}catch{return 0;}}],
  // �39b PARTIAL TERMS (Jonathan): sqrt-features = half-order terms; ratios/products = interactions
  ["sqrtArea",g=>Math.sqrt(g.length*g[0].length)],
  ["aspect",g=>g.length/g[0].length],
  ["meanObj",g=>{try{const cs=components(g,0,"blob");return cs.length?g.flat().filter(v=>v!==0).length/cs.length:0;}catch{return 0;}}],
  ["objXcol",g=>{try{return components(g,0,"blob").length*new Set(g.flat().filter((v:number)=>v!==0)).size;}catch{return 0;}}],
];
const KEY_RANGE:Record<string,(pal:number[],m:number)=>number[]>={
  dy:(_,m)=>rng(-Math.min(m-1,14),Math.min(m-1,14)),dx:(_,m)=>rng(-Math.min(m-1,14),Math.min(m-1,14)),
  fy:()=>rng(1,6),fx:()=>rng(1,6),ny:()=>rng(1,6),nx:()=>rng(1,6),k:()=>rng(1,6),min:()=>rng(1,5),mask:()=>rng(1,15),
  dir:()=>rng(0,3),axis:()=>rng(0,2),mode:()=>rng(0,3),which:()=>rng(0,3),by:()=>rng(0,2),inner:()=>rng(0,2),
  crit:()=>rng(0,1),mirror:()=>rng(0,1),inv:()=>rng(0,1),crop:()=>rng(0,1),vertical:()=>rng(0,1),
};
const COLOR_KEYS=new Set(["from","to","c","bg","a","b","col","fill","out","marker"]);
function rng(a:number,b:number){const o:number[]=[];for(let i=a;i<=b;i++)o.push(i);return o;}
function domainFor(op:string,p0:Record<string,number>,pal:number[],m:number):Record<string,number>[]{
  const keys=Object.keys(p0);if(!keys.length)return[];
  const per=keys.map(k=>COLOR_KEYS.has(k)?pal.slice():KEY_RANGE[k]?KEY_RANGE[k](pal,m):(()=>{try{const vs=new Set<number>((OPS as any)[op].enumerate(pal).map((q:any)=>q[k]).filter((v:any)=>v!==undefined));return vs.size?[...vs]:[p0[k]];}catch{return[p0[k]];}})());
  let out:Record<string,number>[]=[{}];
  for(let i=0;i<keys.length;i++){const nx:Record<string,number>[]=[];
    for(const o of out)for(const v of per[i]){nx.push({...o,[keys[i]]:v});if(nx.length>2500)return nx;}out=nx;}
  return out;
}
const vecEq=(a:Record<string,number>,b:Record<string,number>,ks:string[])=>ks.every(k=>a[k]===b[k]);

// ── knot-beam near-miss anchor (mass-retaining mixed beam), states carry FLATTENED genomes ──
const knots:{id:string;word:Genome;level?:number}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","knots.json"),"utf8"));
type Move={label:string;isKnot:boolean;frag:Genome};
function knotDiag(train:any[],pal:number[],depth=3,beamW=30):{bestGenome:Genome|null;bestScore:number;exact:boolean}{
  const outs=train.map((p:any)=>p.output);
  const moves:Move[]=[];
  for(const k of knots)moves.push({label:"K:"+k.id,isKnot:true,frag:k.word});
  for(const op of OP_NAMES){let ps:Record<string,number>[];try{ps=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ps=[{}];}
    for(const p of ps)moves.push({label:op,isKnot:false,frag:[[op,p]]});}
  const sc=(gs:Grid[])=>{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];
    if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
    let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;};
  type St={grids:Grid[];gen:Genome;s:number;hasK:boolean};
  let beam:St[]=[{grids:train.map((p:any)=>p.input),gen:[],s:sc(train.map((p:any)=>p.input)),hasK:false}];
  let best:Genome|null=null,bestS=-1,exact=false;const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];
    for(const st of beam)for(const mv of moves){
      let g2:Grid[]=[],bad=false;
      for(const g of st.grids){let c:Grid|null=g;for(const[o,p]of mv.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
      if(bad)continue;
      const gen=[...st.gen,...mv.frag],s=sc(g2),hasK=st.hasK||mv.isKnot;
      if(s>bestS){bestS=s;best=gen;}
      if(g2.every((g,i)=>eqG(g,outs[i]))){exact=true;return{bestGenome:gen,bestScore:1,exact:true};}
      const key=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
      if(seen.has(key))continue;seen.add(key);
      next.push({grids:g2,gen,s,hasK});
    }
    next.sort((a,b)=>b.s-a.s);
    const wk=next.filter(x=>x.hasK).slice(0,Math.ceil(beamW/2));
    beam=[...wk,...next.filter(x=>!x.hasK).slice(0,beamW-wk.length)];
    if(!beam.length)break;
  }
  return{bestGenome:best,bestScore:bestS,exact};
}

// ── the polynomial lift: order 1 (line, >=3 distinct f) then order 2 (quadratic, >=4 distinct f) ──
function polyClose(gen:Genome,train:any[],pal:number[]):{prog:(g:Grid)=>Grid|null;how:string}|null{
  const m=Math.max(...train.flatMap((p:any)=>[p.input.length,p.input[0].length,p.output.length,p.output[0].length]));
  for(let j=0;j<gen.length;j++){
    const keys=Object.keys(gen[j][1]);if(!keys.length)continue; // inner atoms stay warm constants
    const dom=domainFor(gen[j][0],gen[j][1],pal,m);if(!dom.length)continue;
    const S:Record<string,number>[][]=[];let ok=true;
    for(const p of train){const s:Record<string,number>[]=[];
      for(const v of dom){const g=gen.slice();g[j]=[gen[j][0],v];const o=build(g)(p.input);if(o&&eqG(o,p.output))s.push(v);}
      if(!s.length){ok=false;break;}S.push(s);}
    if(!ok)continue;
    // order 0: const refit
    for(const v of S[0])if(S.every(s=>s.some(u=>vecEq(u,v,keys)))){
      const g=gen.slice();g[j]=[gen[j][0],v];
      return{prog:build(g),how:"const@"+j+":"+gen[j][0]};}
    for(const[fname,ff]of FEATS){
      const fv=train.map((p:any)=>ff(p.input));const distinct=new Set(fv).size;
      const mkProg=(coef:Record<string,number[]>,ord:number)=>{
        const pred=(f:number)=>{const v:Record<string,number>={};
          for(const k of keys){let x=0;for(let e=0;e<=ord;e++)x+=coef[k][e]*Math.pow(f,e);
            if(Math.abs(x-Math.round(x))>1e-6)return null;v[k]=Math.round(x);}return v;};
        for(let i=0;i<train.length;i++){const pv=pred(fv[i]);if(!pv||!S[i].some(u=>vecEq(u,pv,keys)))return null;}
        const jj=j,g0=gen,op=gen[j][0];
        return{prog:(g:Grid):Grid|null=>{const pv=pred(ff(g));if(!pv)return null;const gg=g0.slice();gg[jj]=[op,pv];return build(gg)(g);},
               how:"ord"+ord+"@"+j+":"+op+" f="+fname+" "+keys.map(k=>k+"=["+coef[k].map(c=>+c.toFixed(3)).join(",")+"]").join(" ")};};
      // ORDER 1 — needs >=3 distinct feature values
      if(distinct>=3){
        let p0=-1,p1=-1;for(let a2=0;a2<fv.length&&p0<0;a2++)for(let b2=a2+1;b2<fv.length;b2++)if(fv[a2]!==fv[b2]){p0=a2;p1=b2;break;}
        for(const va of S[p0].slice(0,12))for(const vb of S[p1].slice(0,12)){
          const coef:Record<string,number[]>={};let nc=false;
          for(const k of keys){const a2=(vb[k]-va[k])/(fv[p1]-fv[p0]);coef[k]=[va[k]-a2*fv[p0],a2];if(a2!==0)nc=true;}
          if(!nc)continue;const r=mkProg(coef,1);if(r)return r;}
      }
      // ORDER 2 — needs >=4 distinct feature values
      if(distinct>=4){
        const idx:number[]=[];const seenF=new Set<number>();
        for(let i2=0;i2<fv.length&&idx.length<3;i2++)if(!seenF.has(fv[i2])){seenF.add(fv[i2]);idx.push(i2);}
        const[i0,i1,i2]=idx,f0=fv[i0],f1=fv[i1],f2=fv[i2];
        for(const va of S[i0].slice(0,8))for(const vb of S[i1].slice(0,8))for(const vc of S[i2].slice(0,8)){
          const coef:Record<string,number[]>={};let q=false,bad=false;
          for(const k of keys){ // Lagrange -> a*f^2+b*f+c
            const y0=va[k],y1=vb[k],y2=vc[k];
            const den=(f0-f1)*(f0-f2)*(f1-f2);if(!den){bad=true;break;}
            const a2=(f2*(y1-y0)+f1*(y0-y2)+f0*(y2-y1))/den;
            const b2=(f2*f2*(y0-y1)+f1*f1*(y2-y0)+f0*f0*(y1-y2))/den;
            const c2=(f1*f2*(f1-f2)*y0+f2*f0*(f2-f0)*y1+f0*f1*(f0-f1)*y2)/den;
            coef[k]=[c2,b2,a2];if(Math.abs(a2)>1e-12)q=true;}
          if(bad||!q)continue;const r=mkProg(coef,2);if(r)return r;}
      }
    }
  }
  return null;
}

// ── runner ──
const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const START=+(process.argv[2]||0),END=+(process.argv[3]||ev.length),STATE=process.argv[4]||null,BUDGET=+(process.argv[5]||34)*1000,T0=Date.now();
let closed=0,trainOnly=0,net:string[]=[],hows:string[]=[],RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §39 POLYNOMIAL LADDER (order 0/1/2 over knot-beam anchors) EVAL ["+START+","+END+") ===");
  console.log("closed: "+closed+"   train-closed-but-test-failed: "+trainOnly);
  console.log("NET-NEW vs verified_eval: "+net.length+"   "+net.join(" "));
  for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED at "+i+" closed="+closed+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
  let r:any=null;try{r=knotDiag(t.train,taskPalette(t.train));}catch{}
  if(!r||!r.bestGenome||r.exact)continue; // exacts were already counted by §37/38
  let w:any=null;try{w=polyClose(r.bestGenome,t.train,taskPalette(t.train));}catch{}
  if(!w)continue;
  if(!t.train.every((p:any)=>{const o=w.prog(p.input);return o&&eqG(o,p.output);}))continue;
  if(t.test.every((te:any)=>{const o=w.prog(te.input);return o&&eqG(o,te.output);})){
    closed++;net.push(t.id);hows.push(t.id+" = "+w.how);rec("poly",t.id,"solved",w.how);
  }else{trainOnly++;hows.push(t.id+" OVERFIT "+w.how);rec("poly",t.id,"overfit",w.how);}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+" trainOnly="+trainOnly+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),closed,trainOnly,net,hows}));
rep();
