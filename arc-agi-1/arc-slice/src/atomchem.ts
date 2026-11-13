// atomchem.ts — "know what an atom IS": characterize each op like an element.
// KNOT = the macro-axes it NEVER changes (its inert, invariant core).
// TAIL/VALENCE = the macro-axes it DOES change (its reactive bonds).
// Atoms bond tail-to-tail: a composition covers a task when the union of the
// atoms' valences covers the task's required axes. (Chemical composition rule.)
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { loadTasks } from "./loader";
import { taskPalette } from "./transfer";
import * as path from "path";
type Grid=number[][];
// macro-axes over the 16-d feature: COLOR(0-9) SIZE(10) POS(cy,cx) SYM(dh,dv,dt)
function counts(g:Grid){const c=new Array(10).fill(0);for(const r of g)for(const v of r)if(v<10)c[v]++;return c;}
function spatial(g:Grid):number[]{ const r=g.length,c=g[0].length; let sy=0,sx=0,m=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){if(g[y][x]!==0){sy+=y/(r-1||1);sx+=x/(c-1||1);m++;}}
  const cy=m?sy/m:0.5,cx=m?sx/m:0.5; let dh=0,dv=0,dt=0,tot=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){tot++;if(g[y][x]!==g[y][c-1-x])dh++;if(g[y][x]!==g[r-1-y][x])dv++;if(r===c&&g[y][x]!==g[x][y])dt++;}
  return [cy,cx,dh/tot,dv/tot,r===c?dt/tot:0];
}
function objFeat(g:Grid):number[]{ const r=g.length,c=g[0].length; const seen=Array.from({length:r},()=>Array(c).fill(false));
  let nObj=0,largest=0,total=0;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==0)total++;
    if(g[y][x]!==0&&!seen[y][x]){ nObj++; let sz=0; const st:[number,number][]=[[y,x]];seen[y][x]=true;const col=g[y][x];
      while(st.length){const[cy,cx]=st.pop()!;sz++;for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=cy+dy,nx=cx+dx;if(ny<0||ny>=r||nx<0||nx>=c||seen[ny][nx]||g[ny][nx]!==col)continue;seen[ny][nx]=true;st.push([ny,nx]);}}
      largest=Math.max(largest,sz);}}
  return [nObj/8,total?largest/total:0]; }
function axisDelta(inp:Grid,out:Grid){
  const n=inp.length*inp[0].length||1; const ci=counts(inp),co=counts(out);
  let color=0; for(let k=0;k<10;k++) color+=Math.abs((co[k]-ci[k])/n);
  const size=Math.abs((out.length*out[0].length-n)/n);
  const si=spatial(inp),so=spatial(out);
  const pos=Math.abs(so[0]-si[0])+Math.abs(so[1]-si[1]);
  const sym=Math.abs(so[2]-si[2])+Math.abs(so[3]-si[3])+Math.abs(so[4]-si[4]);
  const oi=objFeat(inp),oo=objFeat(out); const obj=Math.abs(oo[0]-oi[0])+Math.abs(oo[1]-oi[1]);
  return {color,size,pos,sym,obj};
}
// random sample grids
function rnd(seed:number){let s=seed;return()=>(s=(s*1103515245+12345)&0x7fffffff)/0x7fffffff;}
function grids(){const R=rnd(11);const gs:Grid[]=[];for(let k=0;k<6;k++){const r=5+Math.floor(R()*3),c=5+Math.floor(R()*3);gs.push(Array.from({length:r},()=>Array.from({length:c},()=>Math.floor(R()*4))));}return gs;}
const G=grids(); const PAL=[0,1,2,3];
const TH=0.02;
type Card={op:string,valence:string[],knot:string[],noble:boolean};
const cards:Card[]=[];
for(const op of OP_NAMES){
  let prs:any[]; try{prs=(OPS as any)[op].enumerate(PAL).slice(0,4);}catch{prs=[{}];}
  const acc={color:0,size:0,pos:0,sym:0,obj:0}; let cnt=0;
  for(const pr of prs)for(const g of G){ let o:Grid|null=null; try{o=applyOp({name:op,params:pr} as any,g);}catch{} if(!o||!o.length)continue;
    const d=axisDelta(g,o); acc.color+=d.color;acc.size+=d.size;acc.pos+=d.pos;acc.sym+=d.sym;acc.obj+=d.obj;cnt++; }
  if(!cnt){ cards.push({op,valence:["?"],knot:[],noble:false}); continue; }
  const mean:any={color:acc.color/cnt,size:acc.size/cnt,pos:acc.pos/cnt,sym:acc.sym/cnt,obj:acc.obj/cnt};
  const valence=["color","size","pos","sym","obj"].filter(a=>mean[a]>TH);
  const knot=["color","size","pos","sym","obj"].filter(a=>mean[a]<=TH);
  cards.push({op,valence,knot,noble:valence.length===0});
}
// print the periodic table grouped by valence signature
const byVal:Record<string,string[]>={};
for(const c of cards){ const k=c.valence.join("+")||"NONE(noble/identity-like)"; (byVal[k]??=[]).push(c.op); }
console.log("=== PERIODIC TABLE OF ATOMS (valence = active macro-axes = reactive tail) ===");
for(const [v,ops] of Object.entries(byVal).sort((a,b)=>b[1].length-a[1].length))
  console.log(`  tail[${v}]  (${ops.length}): ${ops.join(" ")}`);
// export cards for the composer
import * as fs from "fs";
fs.writeFileSync(path.join(__dirname,"..","atom_cards.json"),JSON.stringify(cards));
console.log("\nwrote atom_cards.json ("+cards.length+" atoms)");
