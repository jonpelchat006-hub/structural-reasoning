// induce2.ts — more induction templates. Each induces its PARAMETER from the
// examples and is verifier-gated; the way one fails (no-op / wrong / inverted)
// routes to the next — Jonathan's paralysis/wrong-limb/bends-backward diagnostic.
import { Pair } from "../../arc-slice/src/loader";
import { Grid, background, equal } from "../../arc-slice/src/grid";
import { components, blank, Obj } from "../../arc-slice/src/objects";

type GridFn = (g: Grid) => Grid | null;
const inb = (g: Grid, y: number, x: number) => y>=0&&y<g.length&&x>=0&&x<g[0].length;
const verify = (fn: GridFn, train: Pair[]): GridFn | null => {
  for (const { input, output } of train) { const got = fn(input); if (!got || !equal(got, output)) return null; } return fn;
};

// TEMPLATE: induced gravity direction (objects pack toward an induced edge)
export function induceGravity(train: Pair[]): GridFn | null {
  for (const dir of [0,1,2,3]) {
    const [dy,dx] = dir===0?[1,0]:dir===1?[-1,0]:dir===2?[0,1]:[0,-1];
    const fn: GridFn = (g) => {
      const bg = background(g); const objs = components(g, bg, "blob");
      if (!objs.length || objs.length>40) return null;
      const front = (o:Obj)=> dir===0?-o.y1:dir===1?o.y0:dir===2?-o.x1:o.x0;
      const out = blank(g.length,g[0].length,bg);
      for (const o of [...objs].sort((a,b)=>front(a)-front(b))) {
        let s=0; while(true){const ns=s+1;let ok=true; for(const[y,x]of o.cells){const ny=y+dy*ns,nx=x+dx*ns; if(!inb(g,ny,nx)||out[ny][nx]!==bg){ok=false;break;}} if(!ok)break; s=ns;}
        for (const[y,x]of o.cells) out[y+dy*s][x+dx*s]=g[y][x];
      }
      return out;
    };
    const v = verify(fn, train); if (v) return v;
  }
  return null;
}

// TEMPLATE: induced reflection of object POSITIONS (point or axis) — induce which
export function induceReflect(train: Pair[]): GridFn | null {
  const modes = ["point","h","v"] as const;
  for (const mode of modes) {
    const fn: GridFn = (g) => {
      const bg = background(g); const r=g.length,c=g[0].length; const objs = components(g,bg,"blob");
      if (!objs.length || objs.length>40) return null;
      const out = blank(r,c,bg);
      for (const o of objs) {
        let dy=0,dx=0;
        if (mode==="point"){ dy=(r-1-o.y1)-o.y0; dx=(c-1-o.x1)-o.x0; }
        else if (mode==="h"){ dx=(c-1-o.x1)-o.x0; }
        else { dy=(r-1-o.y1)-o.y0; }
        for (const[y,x]of o.cells){const ny=y+dy,nx=x+dx; if(inb(g,ny,nx)) out[ny][nx]=g[y][x];}
      }
      return out;
    };
    const v = verify(fn, train); if (v) return v;
  }
  return null;
}

// TEMPLATE: induced move TOWARD a reference (the largest object) until contact
export function induceToward(train: Pair[]): GridFn | null {
  const fn: GridFn = (g) => {
    const bg = background(g); const objs = components(g,bg,"blob");
    if (objs.length<2 || objs.length>40) return null;
    const ref = objs.reduce((a,b)=>b.size>a.size?b:a);
    const rcy=(ref.y0+ref.y1)/2, rcx=(ref.x0+ref.x1)/2;
    const out = blank(g.length,g[0].length,bg);
    for (const[y,x]of ref.cells) out[y][x]=g[y][x];
    const order = objs.filter(o=>o!==ref);
    for (const o of order) {
      const cy=(o.y0+o.y1)/2, cx=(o.x0+o.x1)/2;
      const sy=Math.sign(rcy-cy), sx=Math.sign(rcx-cx);
      if (sy===0 && sx===0) { for (const[y,x]of o.cells) out[y][x]=g[y][x]; continue; }
      let s=0; while(true){const ns=s+1;let ok=true; for(const[y,x]of o.cells){const ny=y+sy*ns,nx=x+sx*ns; if(!inb(g,ny,nx)||out[ny][nx]!==bg){ok=false;break;}} if(!ok)break; s=ns;}
      for (const[y,x]of o.cells) out[y+sy*s][x+sx*s]=g[y][x];
    }
    return out;
  };
  return verify(fn, train);
}

export const TEMPLATES: ((t: Pair[]) => GridFn | null)[] = [induceGravity, induceReflect, induceToward];
export function induceAny(train: Pair[]): GridFn | null { for (const t of TEMPLATES) { const f = t(train); if (f) return f; } return null; }
