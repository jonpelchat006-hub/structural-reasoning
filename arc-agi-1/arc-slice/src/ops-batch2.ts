import { Grid, dims, clone } from "./grid";
import { components, blank, Obj } from "./objects";
import { panels } from "./ops-panel";
const inb=(g:Grid,y:number,x:number)=>y>=0&&y<g.length&&x>=0&&x<g[0].length;

// anti-diagonal transpose (the D4 element not directly named)
export function antiTranspose(g: Grid): Grid | null {
  const [r,c]=dims(g); const out=blank(c,r,0);
  for(let y=0;y<r;y++)for(let x=0;x<c;x++) out[c-1-x][r-1-y]=g[y][x];
  return out;
}
// pick a panel by position: 0=first,1=last,2=center
export function extractCell(g: Grid, bg: number, which: number): Grid | null {
  const ps=panels(g,bg); if(!ps||ps.length<2) return null;
  if(which===0) return ps[0]; if(which===1) return ps[ps.length-1];
  return ps[Math.floor(ps.length/2)];
}
// tile the whole input by the object count (n×1 / 1×n / n×n)
export function scaleByCount(g: Grid, bg: number, mode: number): Grid | null {
  const n=components(g,bg,"blob").length; if(n<2||n>6) return null;
  const [r,c]=dims(g); const ny=mode===1?1:n, nx=mode===0?1:n;
  if(r*ny*c*nx>2500) return null;
  const out=blank(r*ny,c*nx,bg);
  for(let by=0;by<ny;by++)for(let bx=0;bx<nx;bx++)for(let y=0;y<r;y++)for(let x=0;x<c;x++) out[by*r+y][bx*c+x]=g[y][x];
  return out;
}
// keep only objects touching the grid border (or only NOT touching, invert)
export function borderObjects(g: Grid, bg: number, invert: number): Grid | null {
  const [r,c]=dims(g); const objs=components(g,bg,"blob"); if(objs.length<2||objs.length>40) return null;
  const out=blank(r,c,bg); let kept=0;
  for(const o of objs){ const touches=o.y0===0||o.x0===0||o.y1===r-1||o.x1===c-1;
    if(touches!==!!invert){ for(const[y,x]of o.cells)out[y][x]=g[y][x]; kept++; } }
  return kept?out:null;
}
// majority-neighbour smoothing: each non-bg cell -> its most common 4-neighbour colour if it differs (denoise)
export function smoothNeighbor(g: Grid, bg: number): Grid | null {
  const [r,c]=dims(g); const out=clone(g); let ch=false;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){
    const cnt=new Map<number,number>();
    for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]]) if(inb(g,y+dy,x+dx)) cnt.set(g[y+dy][x+dx],(cnt.get(g[y+dy][x+dx])??0)+1);
    let mc=g[y][x],mn=-1; for(const[v,n]of cnt) if(n>mn){mn=n;mc=v;}
    if(mn>=3 && mc!==g[y][x]){out[y][x]=mc;ch=true;}
  }
  return ch?out:null;
}
// rotate each object 180 in place (square-agnostic; bbox preserved)
export function rotateObjects(g: Grid, bg: number): Grid | null {
  const objs=components(g,bg,"blob"); if(objs.length<1||objs.length>40) return null;
  const out=clone(g); let ch=false;
  for(const o of objs){ const h=o.y1-o.y0+1,w=o.x1-o.x0+1; const sub=blank(h,w,bg);
    for(const[y,x]of o.cells)sub[y-o.y0][x-o.x0]=g[y][x];
    for(const[y,x]of o.cells)out[y][x]=bg;
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){const v=sub[h-1-y][w-1-x]; if(v!==bg){out[o.y0+y][o.x0+x]=v;ch=true;}}
  }
  return ch?out:null;
}
