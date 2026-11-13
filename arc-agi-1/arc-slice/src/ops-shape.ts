// ops-shape.ts — shape-transform primitives (boundary / interior).
import { Grid, dims, clone } from "./grid";
import { components } from "./objects";
const inb = (g: Grid, y: number, x: number) => y>=0&&y<g.length&&x>=0&&x<g[0].length;

// keep only boundary cells of the non-bg shapes (erase interior cells)
export function outline(g: Grid, bg: number): Grid | null {
  const [r,c]=dims(g); const out=clone(g); let changed=false;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){
    if(g[y][x]===bg) continue;
    let interior=true;
    for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]]){const ny=y+dy,nx=x+dx; if(!inb(g,ny,nx)||g[ny][nx]===bg){interior=false;break;}}
    if(interior){out[y][x]=bg;changed=true;}
  }
  return changed?out:null;
}

// fill each object's internal holes (enclosed bg) with that object's own colour
export function fillObjectHoles(g: Grid, bg: number): Grid | null {
  const [r,c]=dims(g); const objs=components(g,bg,"color");
  if(!objs.length||objs.length>60) return null;
  const out=clone(g); let filled=false;
  for(const o of objs){
    // bg cells inside the object's bbox that are NOT reachable from the bbox border (within bbox) = holes
    const h=o.y1-o.y0+1,w=o.x1-o.x0+1;
    const inside=(yy:number,xx:number)=>g[o.y0+yy][o.x0+xx];
    const reach=Array.from({length:h},()=>Array(w).fill(false)); const st:[number,number][]=[];
    for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++) if((yy===0||xx===0||yy===h-1||xx===w-1)&&inside(yy,xx)!==o.color&&!reach[yy][xx]){reach[yy][xx]=true;st.push([yy,xx]);}
    while(st.length){const[cy,cx]=st.pop()!; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]]){const ny=cy+dy,nx=cx+dx; if(ny>=0&&ny<h&&nx>=0&&nx<w&&!reach[ny][nx]&&inside(ny,nx)!==o.color){reach[ny][nx]=true;st.push([ny,nx]);}}}
    for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++) if(inside(yy,xx)!==o.color&&!reach[yy][xx]){out[o.y0+yy][o.x0+xx]=o.color;filled=true;}
  }
  return filled?out:null;
}
