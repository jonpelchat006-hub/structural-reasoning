// audit.ts — replicate every imported OP "in our own words".
// Native atom basis; search depth<=2 compositions that reproduce each op on
// random grids. DERIVABLE = basis covers it; IS-ATOM = it's a chosen atom;
// GAP = no native recipe found -> tells us which atom family we still owe.
import { OPS, OP_NAMES } from "./dsl";
import { Grid } from "./grid";
const eq=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

// ── native atoms (our minimal vocabulary) ──
const A_id=(g:Grid)=>g;
const A_rot90=(g:Grid)=>{const r=g.length,c=g[0].length;const o=Array.from({length:c},()=>Array(r).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)o[x][r-1-y]=g[y][x];return o;};
const A_flipH=(g:Grid)=>g.map(r=>r.slice().reverse());
const A_recolor=(a:number,b:number)=>(g:Grid)=>g.map(r=>r.map(v=>v===a?b:v));
const A_tile=(ny:number,nx:number)=>(g:Grid)=>{const r=g.length,c=g[0].length;if(r*ny*c*nx>2500)return null;const o=Array.from({length:r*ny},()=>Array(c*nx).fill(0));for(let Y=0;Y<r*ny;Y++)for(let X=0;X<c*nx;X++)o[Y][X]=g[Y%r][X%c];return o;};
const A_scale=(fy:number,fx:number)=>(g:Grid)=>{const r=g.length,c=g[0].length;if(r*fy*c*fx>2500)return null;const o=Array.from({length:r*fy},()=>Array(c*fx).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)for(let dy=0;dy<fy;dy++)for(let dx=0;dx<fx;dx++)o[y*fy+dy][x*fx+dx]=g[y][x];return o;};
const A_crop=(bg:number)=>(g:Grid)=>{let y0=1e9,y1=-1,x0=1e9,x1=-1;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]!==bg){y0=Math.min(y0,y);y1=Math.max(y1,y);x0=Math.min(x0,x);x1=Math.max(x1,x);}if(y1<0)return null;const o=[];for(let y=y0;y<=y1;y++)o.push(g[y].slice(x0,x1+1));return o;};

type Atom={name:string, fn:(g:Grid)=>Grid|null};
const atoms:Atom[]=[
  {name:"id",fn:A_id},{name:"rot90",fn:A_rot90},{name:"flipH",fn:A_flipH},
];
for(let a=0;a<4;a++)for(let b=0;b<4;b++) if(a!==b) atoms.push({name:`recolor(${a},${b})`,fn:A_recolor(a,b)});
for(const[ny,nx] of [[1,2],[2,1],[2,2],[3,3],[1,3],[3,1]]) atoms.push({name:`tile(${ny},${nx})`,fn:A_tile(ny,nx)});
for(const[fy,fx] of [[1,2],[2,1],[2,2],[3,3]]) atoms.push({name:`scale(${fy},${fx})`,fn:A_scale(fy,fx)});
atoms.push({name:"crop(0)",fn:A_crop(0)});

// ── random test grids ──
function rnd(seed:number){ let s=seed; return ()=> (s=(s*1103515245+12345)&0x7fffffff)/0x7fffffff; }
function makeGrids():Grid[]{ const R=rnd(7); const gs:Grid[]=[]; for(let k=0;k<5;k++){ const r=4+Math.floor(R()*3),c=4+Math.floor(R()*3); const g=Array.from({length:r},()=>Array.from({length:c},()=>Math.floor(R()*4))); gs.push(g);} return gs; }
const GRIDS=makeGrids();

function targets(opName:string):Grid[][]|null{
  const op=(OPS as any)[opName]; const params=op.enumerate([0,1,2,3]).slice(0,3);
  if(params.length===0) params.push({});
  const sets:Grid[][]=[];
  for(const pr of params){ const outs:Grid[]=[]; let any=false;
    for(const g of GRIDS){ let o:Grid|null=null; try{o=op.fn(g,pr);}catch{} if(o&&o.length){outs.push(o);any=true;} else {outs.push([[ -999 ]]);} }
    // drop param-instances that are identity on all grids (no-op coincidences)
    const isId = outs.every((o,i)=> o.length>1 ? (o.length===GRIDS[i].length&&o[0].length===GRIDS[i][0].length&&o.every((r,y)=>r.every((v,x)=>v===GRIDS[i][y][x]))) : true);
    if(any && !isId) sets.push(outs); }
  return sets.length?sets:null;
}
function matchAll(recipe:(g:Grid)=>Grid|null, outs:Grid[]):boolean{
  for(let i=0;i<GRIDS.length;i++){ if(outs[i].length===1&&outs[i][0][0]===-999) continue; let o:Grid|null=null; try{o=recipe(GRIDS[i]);}catch{} if(!o||!eq(o,outs[i])) return false; }
  return true;
}

const NATIVE=new Set(["identity","rotate","flipH","recolor","crop","scale","tile"]); // the basis ops themselves
const derivable:string[]=[], isatom:string[]=[], gap:string[]=[];
for(const name of OP_NAMES){
  const tsets=targets(name); if(!tsets){ continue; }
  // an op counts DERIVABLE if EVERY param-instance has a native recipe
  let allHave=true; let recipeEx="";
  for(const outs of tsets){
    let found=""; 
    for(const a of atoms){ if(matchAll(a.fn,outs)){found=a.name;break;} }
    if(!found){ for(const a of atoms){ for(const b of atoms){ const f=(g:Grid)=>{const m=a.fn(g);return m?b.fn(m):null;}; if(matchAll(f,outs)){found=`${a.name}∘${b.name}`;break;} } if(found)break; } }
    if(!found){ allHave=false; break; } else recipeEx=found;
  }
  if(NATIVE.has(name)) isatom.push(name);
  else if(allHave) derivable.push(`${name} = ${recipeEx}`);
  else gap.push(name);
}
console.log(`\n=== REPLICATION AUDIT (native basis: id, rot90, flipH, recolor, tile, scale, crop) ===`);
console.log(`IS-ATOM (${isatom.length}): ${isatom.join(" ")}`);
console.log(`\nDERIVABLE from atoms (${derivable.length}):`); derivable.forEach(d=>console.log("  "+d));
console.log(`\nGAP — no native recipe at depth<=2 (${gap.length}): ${gap.join(" ")}`);
