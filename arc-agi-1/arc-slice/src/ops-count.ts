// ops-count.ts — count / shape-class / flood primitives (inner-shell muscle).
import { Grid, dims, clone } from "./grid";
import { components, blank, Obj } from "./objects";
const inb = (g: Grid, y: number, x: number) => y>=0&&y<g.length&&x>=0&&x<g[0].length;

// count objects -> a small grid of `color` (row / col / square). mode 0,1,2.
export function countEmit(g: Grid, bg: number, color: number, mode: number): Grid | null {
  const n = components(g, bg, "blob").length;
  if (n < 1 || n > 30) return null;
  if (mode === 0) return [Array(n).fill(color)];
  if (mode === 1) return Array.from({length:n},()=>[color]);
  if (n*n > 900) return null;
  return Array.from({length:n},()=>Array(n).fill(color));
}

// shape-class recolour: same canonical shape -> same index colour (1,2,3...); cmap finishes.
function canon(o: Obj): string {
  // cheap translation-normalized shape key (exact shape; no rotation) + colour
  return o.color + "|" + o.cells.map(([y,x])=>(y-o.y0)*64+(x-o.x0)).sort((a,b)=>a-b).join(",");
}
export function colorByShape(g: Grid, bg: number): Grid | null {
  if (g.length*g[0].length > 600) return null;
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 40) return null;
  const order: string[] = []; const idx = new Map<string,number>();
  for (const o of objs) { const k=canon(o); if(!idx.has(k)){idx.set(k,order.length+1);order.push(k);} }
  if (order.length > 9) return null;
  const out = clone(g);
  for (const o of objs) for (const [y,x] of o.cells) out[y][x] = idx.get(canon(o))!;
  return out;
}

// fill the bg region connected to the border with `fill` (complement of fillHoles)
export function floodBorder(g: Grid, bg: number, fill: number): Grid | null {
  if (fill === bg) return null;
  const [r,c]=dims(g); const seen=Array.from({length:r},()=>Array(c).fill(false)); const st:[number,number][]=[];
  for(let y=0;y<r;y++)for(let x=0;x<c;x++) if((y===0||x===0||y===r-1||x===c-1)&&g[y][x]===bg&&!seen[y][x]){seen[y][x]=true;st.push([y,x]);}
  while(st.length){const[cy,cx]=st.pop()!; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]]){const ny=cy+dy,nx=cx+dx; if(inb(g,ny,nx)&&!seen[ny][nx]&&g[ny][nx]===bg){seen[ny][nx]=true;st.push([ny,nx]);}}}
  const out=clone(g); let any=false;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++) if(seen[y][x]){out[y][x]=fill;any=true;}
  return any?out:null;
}
