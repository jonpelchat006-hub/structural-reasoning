// trust_audit.ts — a TRUST SYSTEM for the inner shell (Jonathan's trust-economy applied to
// primitives). Like audit.ts, but instead of finding ONE rebuild recipe, it COUNTS how many
// base-atom recipes reproduce each op = REDUNDANCY = trust. An op rebuilt many ways is
// verified from many angles (high trust, load-bearing core); rebuilt one way = provisional;
// rebuilt zero ways = a GAP (untrusted, an atom we still owe). Continuous: re-run as the
// library grows to keep the core certified. Self-contained (mirrors audit.ts's basis).
import { OPS, OP_NAMES } from "./dsl";
import { Grid } from "./grid";
const eq=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

// native atom basis (the trusted seed)
const A_id=(g:Grid)=>g;
const A_rot90=(g:Grid)=>{const r=g.length,c=g[0].length;const o=Array.from({length:c},()=>Array(r).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)o[x][r-1-y]=g[y][x];return o;};
const A_flipH=(g:Grid)=>g.map(r=>r.slice().reverse());
const A_recolor=(a:number,b:number)=>(g:Grid)=>g.map(r=>r.map(v=>v===a?b:v));
const A_tile=(ny:number,nx:number)=>(g:Grid)=>{const r=g.length,c=g[0].length;if(r*ny*c*nx>2500)return null;const o=Array.from({length:r*ny},()=>Array(c*nx).fill(0));for(let Y=0;Y<r*ny;Y++)for(let X=0;X<c*nx;X++)o[Y][X]=g[Y%r][X%c];return o;};
const A_scale=(fy:number,fx:number)=>(g:Grid)=>{const r=g.length,c=g[0].length;if(r*fy*c*fx>2500)return null;const o=Array.from({length:r*fy},()=>Array(c*fx).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)for(let dy=0;dy<fy;dy++)for(let dx=0;dx<fx;dx++)o[y*fy+dy][x*fx+dx]=g[y][x];return o;};
const A_crop=(bg:number)=>(g:Grid)=>{let y0=1e9,y1=-1,x0=1e9,x1=-1;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]!==bg){y0=Math.min(y0,y);y1=Math.max(y1,y);x0=Math.min(x0,x);x1=Math.max(x1,x);}if(y1<0)return null;const o=[];for(let y=y0;y<=y1;y++)o.push(g[y].slice(x0,x1+1));return o;};
const A_transpose=(g:Grid)=>{const r=g.length,c=g[0].length;const o=Array.from({length:c},()=>Array(r).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)o[x][y]=g[y][x];return o;};

type Atom={name:string, fn:(g:Grid)=>Grid|null};
const atoms:Atom[]=[{name:"id",fn:A_id},{name:"rot90",fn:A_rot90},{name:"flipH",fn:A_flipH},{name:"transpose",fn:A_transpose}];
for(let a=0;a<4;a++)for(let b=0;b<4;b++) if(a!==b) atoms.push({name:`recolor(${a},${b})`,fn:A_recolor(a,b)});
for(const[ny,nx] of [[1,2],[2,1],[2,2],[3,3],[1,3],[3,1]]) atoms.push({name:`tile(${ny},${nx})`,fn:A_tile(ny,nx)});
for(const[fy,fx] of [[1,2],[2,1],[2,2],[3,3]]) atoms.push({name:`scale(${fy},${fx})`,fn:A_scale(fy,fx)});
atoms.push({name:"crop(0)",fn:A_crop(0)});
// ── SELECT base-atom family (the biggest gap cluster): keep objects/colours by a predicate ──
function compMap(g:Grid,bg:number){ const R=g.length,C=g[0].length; const id=Array.from({length:R},()=>Array(C).fill(-1)); const sizes:number[]=[]; let n=0;
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]===bg||id[y][x]>=0)continue; const col=g[y][x]; let sz=0; const st:[number,number][]=[[y,x]]; id[y][x]=n;
    while(st.length){ const [cy,cx]=st.pop()!; sz++; for(const [dy,dx] of [[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=cy+dy,nx=cx+dx; if(ny>=0&&ny<R&&nx>=0&&nx<C&&id[ny][nx]<0&&g[ny][nx]===col){ id[ny][nx]=n; st.push([ny,nx]); } } }
    sizes.push(sz); n++; } return {id,sizes,n}; }
const keepBySize=(pickMax:boolean)=>(g:Grid):Grid|null=>{ const {id,sizes,n}=compMap(g,0); if(!n)return null; const t=pickMax?Math.max(...sizes):Math.min(...sizes); const o=g.map(r=>r.slice()); for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++){ const k=id[y][x]; if(k<0||sizes[k]!==t)o[y][x]=0; } return o; };
const keepByFreq=(pickRare:boolean)=>(g:Grid):Grid|null=>{ const cnt=new Map<number,number>(); for(const r of g)for(const v of r)if(v!==0)cnt.set(v,(cnt.get(v)||0)+1); if(!cnt.size)return null; let tgt=-1,best=pickRare?1e9:-1; for(const [c,k] of cnt){ if(pickRare?k<best:k>best){best=k;tgt=c;} } return g.map(r=>r.map(v=>v===tgt?v:0)); };
atoms.push({name:"keepLargest",fn:keepBySize(true)});
atoms.push({name:"keepSmallest",fn:keepBySize(false)});
atoms.push({name:"keepCommonColor",fn:keepByFreq(false)});
atoms.push({name:"keepRareColor",fn:keepByFreq(true)});
// ── MOVE family: gravity (cells fall) in 4 directions ──
const gravAtom=(dir:number)=>(g:Grid):Grid=>{ const r=g.length,c=g[0].length; const o=Array.from({length:r},()=>Array(c).fill(0));
  if(dir<2){ for(let x=0;x<c;x++){ const col:number[]=[]; for(let y=0;y<r;y++)if(g[y][x]!==0)col.push(g[y][x]); for(let k=0;k<col.length;k++){ const y=dir===0?r-1-k:k; o[y][x]=col[dir===0?col.length-1-k:k]; } } }
  else { for(let y=0;y<r;y++){ const row:number[]=[]; for(let x=0;x<c;x++)if(g[y][x]!==0)row.push(g[y][x]); for(let k=0;k<row.length;k++){ const x=dir===2?c-1-k:k; o[y][x]=row[dir===2?row.length-1-k:k]; } } }
  return o; };
for(const d of [0,1,2,3]) atoms.push({name:`gravity(${d})`,fn:gravAtom(d)});
// ── SELECT by OBJECT SHAPE-class (the precise predicate the colour atoms missed) ──
function shapeKey(cells:[number,number][]):string{ let y0=1e9,x0=1e9; for(const [y,x] of cells){y0=Math.min(y0,y);x0=Math.min(x0,x);} return cells.map(([y,x])=>(y-y0)*64+(x-x0)).sort((a,b)=>a-b).join(","); }
function objList(g:Grid){ const {id,n}=compMap(g,0); const R=g.length,C=g[0].length; const cells:[number,number][][]=Array.from({length:n},()=>[]); for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(id[y][x]>=0) cells[id[y][x]].push([y,x]); } return cells.map(cs=>({cells:cs,key:shapeKey(cs)})); }
const keepShapeBy=(mode:"unique"|"rare"|"common")=>(g:Grid):Grid|null=>{ const objs=objList(g); if(!objs.length)return null; const freq=new Map<string,number>(); for(const o of objs)freq.set(o.key,(freq.get(o.key)||0)+1);
  let target=""; if(mode==="unique"){ for(const [k,c] of freq) if(c===1){target=k;break;} } else { let best=mode==="rare"?1e9:-1; for(const [k,c] of freq){ if(mode==="rare"?c<best:c>best){best=c;target=k;} } }
  if(!target)return null; const o=g.map(r=>r.map(()=>0)); for(const ob of objs) if(ob.key===target) for(const [y,x] of ob.cells) o[y][x]=g[y][x]; return o; };
atoms.push({name:"keepUniqueShape",fn:keepShapeBy("unique")});
atoms.push({name:"keepRareShape",fn:keepShapeBy("rare")});
atoms.push({name:"keepCommonShape",fn:keepShapeBy("common")});
// ── STRUCTURE / DRAW atoms (finishing the kitchen) ──
const symH=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++) if(o[y][x]===0&&g[y][C-1-x]!==0)o[y][x]=g[y][C-1-x]; return o; };
const symV=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++) if(o[y][x]===0&&g[R-1-y][x]!==0)o[y][x]=g[R-1-y][x]; return o; };
const grow=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++) if(g[y][x]!==0)for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=y+dy,nx=x+dx; if(ny>=0&&ny<R&&nx>=0&&nx<C&&g[ny][nx]===0)o[ny][nx]=g[y][x]; } return o; };
const denoise=(g:Grid):Grid=>{ const {id,sizes}=compMap(g,0); const o=g.map(r=>r.slice()); for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++){ const k=id[y][x]; if(k>=0&&sizes[k]===1)o[y][x]=0; } return o; };
const fillHolesSurround=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice()); const seen=Array.from({length:R},()=>Array(C).fill(false));
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]!==0||seen[y][x])continue; const cells:[number,number][]=[]; const st:[number,number][]=[[y,x]]; seen[y][x]=true; let edge=false; const bord=new Set<number>();
    while(st.length){ const[cy,cx]=st.pop()!; cells.push([cy,cx]); if(cy===0||cx===0||cy===R-1||cx===C-1)edge=true; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=cy+dy,nx=cx+dx; if(ny<0||ny>=R||nx<0||nx>=C)continue; if(g[ny][nx]===0){if(!seen[ny][nx]){seen[ny][nx]=true;st.push([ny,nx]);}}else bord.add(g[ny][nx]); } }
    if(!edge&&bord.size===1){ const c=[...bord][0]; for(const[cy,cx]of cells)o[cy][cx]=c; } } return o; };
atoms.push({name:"symH",fn:symH}); atoms.push({name:"symV",fn:symV}); atoms.push({name:"grow",fn:grow}); atoms.push({name:"denoise",fn:denoise}); atoms.push({name:"fillHolesSurround",fn:fillHolesSurround});
// ── MORE KITCHEN TOOLS: trim / border / shift / mirror-concat / bbox ──
const trim=(g:Grid):Grid|null=>{ if(g.length<3||g[0].length<3)return null; return g.slice(1,-1).map(r=>r.slice(1,-1)); };
const addBorder=(c:number)=>(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=Array.from({length:R+2},()=>Array(C+2).fill(c)); for(let y=0;y<R;y++)for(let x=0;x<C;x++)o[y+1][x+1]=g[y][x]; return o; };
const shiftAtom=(dy:number,dx:number)=>(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length; const o=Array.from({length:R},()=>Array(C).fill(0)); for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]!==0){ const ny=y+dy,nx=x+dx; if(ny<0||ny>=R||nx<0||nx>=C)return null; o[ny][nx]=g[y][x]; } } return o; };
const fH=(g:Grid)=>g.map(r=>r.slice().reverse()); const fV=(g:Grid)=>g.slice().reverse().map(r=>r.slice());
const hcat=(a:Grid,b:Grid)=>a.map((r,i)=>r.concat(b[i])); const vcat=(a:Grid,b:Grid)=>a.concat(b);
const bboxFill=(g:Grid):Grid=>{ const {id,n}=compMap(g,0); const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  const bb=new Map<number,[number,number,number,number,number]>();
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ const k=id[y][x]; if(k<0)continue; const e=bb.get(k); if(!e)bb.set(k,[y,y,x,x,g[y][x]]); else { e[0]=Math.min(e[0],y);e[1]=Math.max(e[1],y);e[2]=Math.min(e[2],x);e[3]=Math.max(e[3],x); } }
  for(const [,e] of bb){ for(let y=e[0];y<=e[1];y++)for(let x=e[2];x<=e[3];x++)o[y][x]=e[4]; } return o; };
atoms.push({name:"trim",fn:trim}); atoms.push({name:"addBorder1",fn:addBorder(1)}); atoms.push({name:"addBorder2",fn:addBorder(2)});
for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]) atoms.push({name:`shift(${dy},${dx})`,fn:shiftAtom(dy,dx)});
atoms.push({name:"mirH|",fn:(g:Grid)=>hcat(g,fH(g))}); atoms.push({name:"|mirH",fn:(g:Grid)=>hcat(fH(g),g)});
atoms.push({name:"mirV",fn:(g:Grid)=>vcat(g,fV(g))}); atoms.push({name:"quadMir",fn:(g:Grid)=>vcat(hcat(g,fH(g)),hcat(fV(g),fV(fH(g))))});
atoms.push({name:"bboxFill",fn:bboxFill});
// ── BOND / RELATIONAL atoms: object-pairs sharing a void-line (adjacency / alignment) ──
const connectObjAtom=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  for(let y=0;y<R;y++){ let pv=-1,pc=-1; for(let x=0;x<C;x++){ const v=g[y][x]; if(v!==0){ if(pv>=0&&pc===v&&x-pv>1)for(let k=pv+1;k<x;k++)o[y][k]=v; pv=x;pc=v; } } }
  for(let x=0;x<C;x++){ let pv=-1,pc=-1; for(let y=0;y<R;y++){ const v=g[y][x]; if(v!==0){ if(pv>=0&&pc===v&&y-pv>1)for(let k=pv+1;k<y;k++)o[k][x]=v; pv=y;pc=v; } } }
  return o; };
const keepTouchingLargest=(g:Grid):Grid|null=>{ const {id,sizes,n}=compMap(g,0); if(!n)return null; const big=sizes.indexOf(Math.max(...sizes)); const R=g.length,C=g[0].length; const touch=new Set<number>([big]);
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(id[y][x]===big)for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=y+dy,nx=x+dx; if(ny>=0&&ny<R&&nx>=0&&nx<C&&id[ny][nx]>=0)touch.add(id[ny][nx]); } }
  const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++){ const k=id[y][x]; if(k>=0&&!touch.has(k))o[y][x]=0; } return o; };
atoms.push({name:"connectObj",fn:connectObjAtom}); atoms.push({name:"keepTouchingLargest",fn:keepTouchingLargest});
// ── DRAW LINE-RUNG: connect-the-dots between an object's anchors (corners/boundary) ──
const drawBoxAtom=(g:Grid):Grid=>{ const {id}=compMap(g,0); const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  const bb=new Map<number,[number,number,number,number,number]>();
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ const k=id[y][x]; if(k<0)continue; const e=bb.get(k); if(!e)bb.set(k,[y,y,x,x,g[y][x]]); else{e[0]=Math.min(e[0],y);e[1]=Math.max(e[1],y);e[2]=Math.min(e[2],x);e[3]=Math.max(e[3],x);} }
  for(const[,e]of bb){ for(let x=e[2];x<=e[3];x++){o[e[0]][x]=e[4];o[e[1]][x]=e[4];} for(let y=e[0];y<=e[1];y++){o[y][e[2]]=e[4];o[y][e[3]]=e[4];} } return o; };
const outlineAtom=(c:number)=>(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]===0){ let adj=false; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]] as [number,number][]){const ny=y+dy,nx=x+dx; if(ny>=0&&ny<R&&nx>=0&&nx<C&&g[ny][nx]!==0){adj=true;break;}} if(adj)o[y][x]=c; } } return o; };
const crossAtom=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]!==0){ const c=g[y][x]; for(let k=0;k<C;k++)if(o[y][k]===0)o[y][k]=c; for(let k=0;k<R;k++)if(o[k][x]===0)o[k][x]=c; } } return o; };
atoms.push({name:"drawBox",fn:drawBoxAtom}); atoms.push({name:"outline1",fn:outlineAtom(1)}); atoms.push({name:"outline2",fn:outlineAtom(2)}); atoms.push({name:"cross",fn:crossAtom});
// ── FLOW / SPRAY family: one waterwheel, matter sprayed different ways ──
const floodBorderAtom=(c:number)=>(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice()); const seen=Array.from({length:R},()=>Array(C).fill(false)); const st:[number,number][]=[];
  for(let y=0;y<R;y++){ if(g[y][0]===0&&!seen[y][0]){st.push([y,0]);seen[y][0]=true;} if(g[y][C-1]===0&&!seen[y][C-1]){st.push([y,C-1]);seen[y][C-1]=true;} }
  for(let x=0;x<C;x++){ if(g[0][x]===0&&!seen[0][x]){st.push([0,x]);seen[0][x]=true;} if(g[R-1][x]===0&&!seen[R-1][x]){st.push([R-1,x]);seen[R-1][x]=true;} }
  while(st.length){ const[cy,cx]=st.pop()!; o[cy][cx]=c; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=cy+dy,nx=cx+dx; if(ny>=0&&ny<R&&nx>=0&&nx<C&&!seen[ny][nx]&&g[ny][nx]===0){seen[ny][nx]=true;st.push([ny,nx]);}} } return o; };
const drawRaysAtom=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]!==0){ const c=g[y][x]; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ let ny=y+dy,nx=x+dx; while(ny>=0&&ny<R&&nx>=0&&nx<C&&g[ny][nx]===0){o[ny][nx]=c;ny+=dy;nx+=dx;} } } } return o; };
const periodicFillAtom=(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length;
  for(let py=1;py<=R;py++)for(let px=1;px<=C;px++){ if(py===R&&px===C)continue; const tile=new Map<string,number>(); let ok=true;
    for(let y=0;y<R&&ok;y++)for(let x=0;x<C;x++){ if(g[y][x]===0)continue; const k=(y%py)+","+(x%px); if(tile.has(k)&&tile.get(k)!==g[y][x]){ok=false;break;} tile.set(k,g[y][x]); }
    if(!ok||tile.size===0)continue; const o=g.map(r=>r.slice()); let filled=false;
    for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(o[y][x]===0){ const v=tile.get((y%py)+","+(x%px)); if(v!=null){o[y][x]=v;filled=true;} } }
    if(filled)return o; } return null; };
atoms.push({name:"floodBorder1",fn:floodBorderAtom(1)}); atoms.push({name:"floodBorder2",fn:floodBorderAtom(2)}); atoms.push({name:"drawRays",fn:drawRaysAtom}); atoms.push({name:"periodicFill",fn:periodicFillAtom});
// ── PANEL (hardened borders, sprays mix) + FRACTAL (partial/fractional-dimension lift) ──
const halfAtom=(w:string)=>(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length;
  if(w==="L")return C>=2?g.map(r=>r.slice(0,Math.floor(C/2))):null; if(w==="R")return C>=2?g.map(r=>r.slice(Math.ceil(C/2))):null;
  if(w==="T")return R>=2?g.slice(0,Math.floor(R/2)):null; return R>=2?g.slice(Math.ceil(R/2)):null; };
const overlayHalves=(mode:string)=>(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length;
  if(C%2===0){ const h=C/2; const a=g.map(r=>r.slice(0,h)),b=g.map(r=>r.slice(h)); return a.map((row,y)=>row.map((v,x)=>{ const w=b[y][x]; return mode==="or"?(v||w):(v&&w?v:0); })); }
  if(R%2===0){ const h=R/2; const a=g.slice(0,h),b=g.slice(h); return a.map((row,y)=>row.map((v,x)=>{ const w=b[y][x]; return mode==="or"?(v||w):(v&&w?v:0); })); }
  return null; };
const fractalAtom=(inv:boolean)=>(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length; if(R*R*C*C>2500)return null; const o=Array.from({length:R*R},()=>Array(C*C).fill(0));
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ const on=(g[y][x]!==0)!==inv; if(on)for(let yy=0;yy<R;yy++)for(let xx=0;xx<C;xx++)o[y*R+yy][x*C+xx]=g[yy][xx]; } return o; };
const smoothNeighbor=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(r=>r.slice());
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ const cnt=new Map<number,number>(); for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=y+dy,nx=x+dx; if(ny>=0&&ny<R&&nx>=0&&nx<C)cnt.set(g[ny][nx],(cnt.get(g[ny][nx])||0)+1);} let best=-1,bc=g[y][x]; for(const[c,k]of cnt)if(k>best){best=k;bc=c;} if(best>=3)o[y][x]=bc; } return o; };
const completeDiag=(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length; if(R!==C)return null; const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++) if(o[y][x]===0&&g[x][y]!==0)o[y][x]=g[x][y]; return o; };
atoms.push({name:"halfL",fn:halfAtom("L")}); atoms.push({name:"halfR",fn:halfAtom("R")}); atoms.push({name:"halfT",fn:halfAtom("T")}); atoms.push({name:"halfB",fn:halfAtom("B")});
atoms.push({name:"overlayOr",fn:overlayHalves("or")}); atoms.push({name:"overlayAnd",fn:overlayHalves("and")});
atoms.push({name:"fractal",fn:fractalAtom(false)}); atoms.push({name:"fractalInv",fn:fractalAtom(true)});
atoms.push({name:"smoothNeighbor",fn:smoothNeighbor}); atoms.push({name:"completeDiag",fn:completeDiag});
// ── FIELD / MAGNETISM (forces between pieces): attractor spot, rigid pull, spectrum rank ──
const cropToLargest=(g:Grid):Grid|null=>{ const {id,sizes,n}=compMap(g,0); if(!n)return null; let k=0; for(let i=1;i<n;i++)if(sizes[i]>sizes[k])k=i;
  let y0=1e9,y1=-1,x0=1e9,x1=-1; for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(id[y][x]===k){y0=Math.min(y0,y);y1=Math.max(y1,y);x0=Math.min(x0,x);x1=Math.max(x1,x);}
  const o:Grid=[]; for(let y=y0;y<=y1;y++){const row:number[]=[]; for(let x=x0;x<=x1;x++)row.push(id[y][x]===k?g[y][x]:0); o.push(row);} return o; };
const gravityObjAtom=(dir:number)=>(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length; const {id,n}=compMap(g,0); if(!n)return null;
  const objs:[number,number,number][][]=Array.from({length:n},()=>[]); for(let y=0;y<R;y++)for(let x=0;x<C;x++){const k=id[y][x]; if(k>=0)objs[k].push([y,x,g[y][x]]);}
  const D:[number,number][]=[[1,0],[-1,0],[0,1],[0,-1]]; const [dy,dx]=D[dir];
  const lead=(o:[number,number,number][])=>Math.max(...o.map(([y,x])=>dir===0?y:dir===1?-y:dir===2?x:-x));
  const order=objs.map((_,i)=>i).sort((a,b)=>lead(objs[b])-lead(objs[a]));
  const o=Array.from({length:R},()=>Array(C).fill(0));
  for(const i of order){ let shift=0; while(true){ const ns=shift+1; let ok=true; for(const [y,x] of objs[i]){ const ny=y+dy*ns,nx=x+dx*ns; if(ny<0||ny>=R||nx<0||nx>=C||o[ny][nx]!==0){ok=false;break;} } if(!ok)break; shift=ns; }
    for(const [y,x,c] of objs[i]) o[y+dy*shift][x+dx*shift]=c; } return o; };
const paintRankAtom=(g:Grid):Grid|null=>{ const objs=objList(g); if(objs.length<2)return null;
  const sized=objs.map(o=>({o,sz:o.cells.length})).sort((a,b)=>b.sz-a.sz); const palette=[1,2,3,4,5,6,7,8,9];
  const out=g.map(r=>r.map(()=>0)); sized.forEach((s,i)=>{ const c=palette[Math.min(i,palette.length-1)]; for(const [y,x] of s.o.cells) out[y][x]=c; }); return out; };
atoms.push({name:"cropToLargest",fn:cropToLargest});
for(const d of [0,1,2,3]) atoms.push({name:`gravityObj(${d})`,fn:gravityObjAtom(d)});
atoms.push({name:"paintRank",fn:paintRankAtom});
// ── SCULPT / CASCADE (cut away what is not the object) + border-metric largest ──
const cropToColorAtom=(pickRare:boolean)=>(g:Grid):Grid|null=>{ const cnt=new Map<number,number>(); for(const r of g)for(const v of r)if(v!==0)cnt.set(v,(cnt.get(v)||0)+1); if(!cnt.size)return null;
  let tgt=-1,best=pickRare?1e9:-1; for(const[c,k]of cnt){if(pickRare?k<best:k>best){best=k;tgt=c;}}
  let y0=1e9,y1=-1,x0=1e9,x1=-1; for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===tgt){y0=Math.min(y0,y);y1=Math.max(y1,y);x0=Math.min(x0,x);x1=Math.max(x1,x);}
  if(y1<0)return null; const o:Grid=[]; for(let y=y0;y<=y1;y++){const row:number[]=[];for(let x=x0;x<=x1;x++)row.push(g[y][x]===tgt?tgt:0);o.push(row);} return o; };
const selectMajorityAtom=(g:Grid):Grid|null=>{ const cnt=new Map<number,number>(); for(const r of g)for(const v of r)if(v!==0)cnt.set(v,(cnt.get(v)||0)+1); if(!cnt.size)return null;
  let tgt=-1,best=-1; for(const[c,k]of cnt){if(k>best){best=k;tgt=c;}} return g.map(r=>r.map(v=>v!==0?tgt:0)); };
const keepLongestBorder=(g:Grid):Grid|null=>{ const {id,n}=compMap(g,0); if(!n)return null; const R=g.length,C=g[0].length; const perim=Array(n).fill(0);
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){const k=id[y][x]; if(k<0)continue; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=y+dy,nx=x+dx; if(ny<0||ny>=R||nx<0||nx>=C||id[ny][nx]!==k)perim[k]++;}}
  let k=0; for(let i=1;i<n;i++)if(perim[i]>perim[k])k=i; const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++)if(id[y][x]!==k)o[y][x]=0; return o; };
atoms.push({name:"cropColorRare",fn:cropToColorAtom(true)}); atoms.push({name:"cropColorCommon",fn:cropToColorAtom(false)});
atoms.push({name:"selectMajority",fn:selectMajorityAtom}); atoms.push({name:"keepLongestBorder",fn:keepLongestBorder});
// ── ROOF op with a fixed form: rotate each object 90 in place (which-rotation is the per-task choice) ──
const rotateObjectsAtom=(cw:boolean)=>(g:Grid):Grid|null=>{ const {id,n}=compMap(g,0); if(!n)return null; const R=g.length,C=g[0].length;
  const o=g.map(r=>r.slice()); const objs:[number,number,number][][]=Array.from({length:n},()=>[]);
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){const k=id[y][x]; if(k>=0){objs[k].push([y,x,g[y][x]]); o[y][x]=0;}}
  for(const obj of objs){ let y0=1e9,x0=1e9,y1=-1,x1=-1; for(const[y,x]of obj){y0=Math.min(y0,y);x0=Math.min(x0,x);y1=Math.max(y1,y);x1=Math.max(x1,x);}
    const h=y1-y0+1,w=x1-x0+1; const cy=(y0+y1)/2, cx=(x0+x1)/2;
    for(const[y,x,c]of obj){ const ry=y-y0,rx=x-x0; let ny:number,nx:number; if(cw){ny=rx;nx=h-1-ry;}else{ny=w-1-rx;nx=ry;}
      // recenter rotated (w x h) box on the object centroid
      const ty=Math.round(cy-(w-1)/2)+ny, tx=Math.round(cx-(h-1)/2)+nx; if(ty>=0&&ty<R&&tx>=0&&tx<C) o[ty][tx]=c; } }
  return o; };
atoms.push({name:"rotateObjectsCW",fn:rotateObjectsAtom(true)}); atoms.push({name:"rotateObjectsCCW",fn:rotateObjectsAtom(false)});
// ── VOID-ANCHOR SEPARATION (the field sorts by mass): attract to anchor, align, sort into bands ──
const moveToAnchorAtom=(g:Grid):Grid|null=>{ const {id,sizes,n}=compMap(g,0); if(n<2)return null; const R=g.length,C=g[0].length;
  let anc=0; for(let i=1;i<n;i++)if(sizes[i]>sizes[anc])anc=i;
  const objs:[number,number,number][][]=Array.from({length:n},()=>[]); for(let y=0;y<R;y++)for(let x=0;x<C;x++){const k=id[y][x]; if(k>=0)objs[k].push([y,x,g[y][x]]);}
  const cen=(o:[number,number,number][])=>{let sy=0,sx=0;for(const[y,x]of o){sy+=y;sx+=x;}return [sy/o.length,sx/o.length] as [number,number];};
  const [ay,ax]=cen(objs[anc]); const o=Array.from({length:R},()=>Array(C).fill(0)); for(const[y,x,c]of objs[anc])o[y][x]=c;
  for(let i=0;i<n;i++){ if(i===anc)continue; const [cy,cx]=cen(objs[i]); const dy=Math.sign(ay-cy),dx=Math.sign(ax-cx);
    let sh=0; while(dy||dx){ const ns=sh+1; let ok=true; for(const[y,x]of objs[i]){const ny=y+dy*ns,nx=x+dx*ns; if(ny<0||ny>=R||nx<0||nx>=C||o[ny][nx]!==0){ok=false;break;}} if(!ok)break; sh=ns; }
    for(const[y,x,c]of objs[i]){const ny=y+dy*sh,nx=x+dx*sh; if(ny>=0&&ny<R&&nx>=0&&nx<C)o[ny][nx]=c;} } return o; };
const alignLargestAtom=(g:Grid):Grid|null=>{ const {id,sizes,n}=compMap(g,0); if(n<2)return null; const R=g.length,C=g[0].length;
  let anc=0; for(let i=1;i<n;i++)if(sizes[i]>sizes[anc])anc=i;
  const objs:[number,number,number][][]=Array.from({length:n},()=>[]); for(let y=0;y<R;y++)for(let x=0;x<C;x++){const k=id[y][x]; if(k>=0)objs[k].push([y,x,g[y][x]]);}
  const crow=(o:[number,number,number][])=>{let s=0;for(const[y]of o)s+=y;return s/o.length;};
  const arow=crow(objs[anc]); const o=Array.from({length:R},()=>Array(C).fill(0));
  for(let i=0;i<n;i++){ const shift=i===anc?0:Math.round(arow-crow(objs[i]));
    for(const[y,x,c]of objs[i]){const ny=y+shift; if(ny<0||ny>=R)return null; o[ny][x]=c;} } return o; };
const sortBySizeRow=(desc:boolean)=>(g:Grid):Grid|null=>{ const objs=objList(g); if(objs.length<2)return null;
  const sp=objs.map(o=>{ let y0=1e9,x0=1e9,y1=-1,x1=-1; for(const[y,x]of o.cells){y0=Math.min(y0,y);x0=Math.min(x0,x);y1=Math.max(y1,y);x1=Math.max(x1,x);}
    const h=y1-y0+1,w=x1-x0+1; const s=Array.from({length:h},()=>Array(w).fill(0)); for(const[y,x]of o.cells)s[y-y0][x-x0]=g[y][x]; return {s,h,w,sz:o.cells.length}; });
  sp.sort((a,b)=>desc?b.sz-a.sz:a.sz-b.sz); const H=Math.max(...sp.map(z=>z.h)); const W=sp.reduce((a,z)=>a+z.w,0)+(sp.length-1); if(H*W>2500)return null;
  const o=Array.from({length:H},()=>Array(W).fill(0)); let cx=0; for(const z of sp){ for(let y=0;y<z.h;y++)for(let x=0;x<z.w;x++)o[y][cx+x]=z.s[y][x]; cx+=z.w+1; } return o; };
atoms.push({name:"moveContact",fn:moveToAnchorAtom}); atoms.push({name:"alignLargest",fn:alignLargestAtom});
atoms.push({name:"sortBySizeDesc",fn:sortBySizeRow(true)}); atoms.push({name:"sortBySizeAsc",fn:sortBySizeRow(false)});

function rnd(seed:number){ let s=seed; return ()=> (s=(s*1103515245+12345)&0x7fffffff)/0x7fffffff; }
function makeGrids():Grid[]{ const R=rnd(7); const gs:Grid[]=[]; for(let k=0;k<5;k++){ const r=4+Math.floor(R()*3),c=4+Math.floor(R()*3); gs.push(Array.from({length:r},()=>Array.from({length:c},()=>Math.floor(R()*4)))); } return gs; }
const GRIDS=makeGrids();
function targets(opName:string):Grid[][]|null{
  const op=(OPS as any)[opName]; const params=op.enumerate([0,1,2,3]).slice(0,3); if(params.length===0) params.push({});
  const sets:Grid[][]=[];
  for(const pr of params){ const outs:Grid[]=[]; let any=false;
    for(const g of GRIDS){ let o:Grid|null=null; try{o=op.fn(g,pr);}catch{} if(o&&o.length){outs.push(o);any=true;} else outs.push([[-999]]); }
    const isId=outs.every((o,i)=> o.length>1 ? (o.length===GRIDS[i].length&&o[0].length===GRIDS[i][0].length&&o.every((r,y)=>r.every((v,x)=>v===GRIDS[i][y][x]))) : true);
    if(any&&!isId) sets.push(outs); }
  return sets.length?sets:null;
}
function matchAll(recipe:(g:Grid)=>Grid|null, outs:Grid[]):boolean{
  for(let i=0;i<GRIDS.length;i++){ if(outs[i].length===1&&outs[i][0][0]===-999) continue; let o:Grid|null=null; try{o=recipe(GRIDS[i]);}catch{} if(!o||!eq(o,outs[i])) return false; }
  return true;
}
// count DISTINCT recipes (single atoms + depth-2 pairs) that reproduce these outputs = redundancy
function redundancy(outs:Grid[]):number{
  let n=0;
  for(const a of atoms) if(matchAll(a.fn,outs)) n++;
  for(const a of atoms) for(const b of atoms){ const f=(g:Grid)=>{const m=a.fn(g);return m?b.fn(m):null;}; if(matchAll(f,outs)) n++; }
  return n;
}

const NATIVE=new Set(["identity","rotate","flipH","transpose","recolor","crop","scale","tile","keepLargest","keepSmallest","gravity","selectUnique","symmetrize","grow","denoise","fillHoles","trim","addBorder","shift","mirrorConcat","bboxFill","connect","connectObjects","keepTouching","drawBox","outline","cross","floodBorder","drawRays","periodicFill","half","overlayHalves","fractal","smoothNeighbor","completeDiag","largest","gravityObj","paintRank","cropToColor","selectMajority","rotateObjects","moveContact","alignLargest"]);
type Row={op:string, trust:number};
const rows:Row[]=[]; const gaps:string[]=[];
for(const name of OP_NAMES){
  if(NATIVE.has(name)){ rows.push({op:name, trust:999}); continue; } // basis atoms = core, trusted by definition
  const tsets=targets(name); if(!tsets) continue;
  // op's trust = the MIN redundancy across its param-instances (weakest link); 0 = a gap on some instance
  let minR=1e9; for(const outs of tsets){ const r=redundancy(outs); if(r<minR) minR=r; }
  if(minR===0) gaps.push(name); else rows.push({op:name, trust:minR});
}
const core=rows.filter(r=>r.trust===999), trusted=rows.filter(r=>r.trust>=2&&r.trust<999), prov=rows.filter(r=>r.trust===1);
console.log("\n=== INNER-SHELL TRUST AUDIT (redundancy = how many base recipes rebuild each op) ===");
console.log(`basis atoms (CORE, fully trusted): ${core.length}  ${core.map(r=>r.op).join(" ")}`);
console.log(`TRUSTED (rebuilt >=2 ways): ${trusted.length}`);
trusted.sort((a,b)=>b.trust-a.trust).forEach(r=>console.log(`   ${r.op}: ${r.trust} recipes`));
console.log(`PROVISIONAL (rebuilt exactly 1 way — single-source, lower trust): ${prov.length}  ${prov.map(r=>r.op).join(" ")}`);
console.log(`GAP (0 recipes — untrusted, atom we still owe): ${gaps.length}  ${gaps.join(" ")}`);
const expressible=core.length+trusted.length+prov.length, total=expressible+gaps.length;
console.log(`\nCOVERAGE: ${expressible}/${total} ops self-express in the basis (${(100*expressible/total).toFixed(0)}%).`);
console.log(`MEAN TRUST of the derivable (non-core) ops: ${(rows.filter(r=>r.trust<999).reduce((s,r)=>s+r.trust,0)/Math.max(1,trusted.length+prov.length)).toFixed(1)} recipes each.`);
