// ops-relate2.ts — object-level relations + diagonal symmetry completion.
import { Grid, dims, clone } from "./grid";
import { components } from "./objects";
const inb=(g:Grid,y:number,x:number)=>y>=0&&y<g.length&&x>=0&&x<g[0].length;

// connect aligned same-colour OBJECTS: fill the bg gap between two objects of the
// same colour that share a row-band or col-band, along the straight corridor.
export function connectObjects(g: Grid, bg: number): Grid | null {
  const objs=components(g,bg,"color"); if(objs.length<2||objs.length>40) return null;
  const out=clone(g); let drew=false;
  for(let i=0;i<objs.length;i++)for(let j=i+1;j<objs.length;j++){
    const a=objs[i],b=objs[j]; if(a.color!==b.color) continue;
    // horizontal corridor: overlapping rows
    const ry0=Math.max(a.y0,b.y0), ry1=Math.min(a.y1,b.y1);
    if(ry0<=ry1){ const [l,r]= a.x1<b.x0?[a,b]:[b,a]; if(l.x1<r.x0){ const y=Math.floor((ry0+ry1)/2);
      let clear=true; for(let x=l.x1+1;x<r.x0;x++) if(g[y][x]!==bg){clear=false;break;}
      if(clear) for(let x=l.x1+1;x<r.x0;x++){out[y][x]=a.color;drew=true;} } }
    // vertical corridor: overlapping cols
    const cx0=Math.max(a.x0,b.x0), cx1=Math.min(a.x1,b.x1);
    if(cx0<=cx1){ const [t,bm]= a.y1<b.y0?[a,b]:[b,a]; if(t.y1<bm.y0){ const x=Math.floor((cx0+cx1)/2);
      let clear=true; for(let y=t.y1+1;y<bm.y0;y++) if(g[y][x]!==bg){clear=false;break;}
      if(clear) for(let y=t.y1+1;y<bm.y0;y++){out[y][x]=a.color;drew=true;} } }
  }
  return drew?out:null;
}

// complete diagonal symmetry (transpose / anti-transpose) by overlay, square only
export function completeDiag(g: Grid, bg: number): Grid | null {
  const [r,c]=dims(g); if(r!==c) return null;
  const out=clone(g); let filled=false;
  for(const anti of [false,true]) for(let y=0;y<r;y++)for(let x=0;x<c;x++){
    const my= anti? c-1-x : x, mx= anti? r-1-y : y;
    if(out[y][x]===bg && g[my][mx]!==bg){out[y][x]=g[my][mx];filled=true;}
  }
  return filled?out:null;
}
