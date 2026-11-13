// complete.ts — the GENERATOR pole (sphere "tail"): the new content is FORCED by
// the existing structure (Test G: triangulation forces the completion). Induce a
// completion rule consistent across ALL train pairs (the joint constraint), close
// colours with cmap. Targets the INK_ADDED generative gap.
import { Pair } from "../../arc-slice/src/loader";
import { Grid, equal, background } from "../../arc-slice/src/grid";
import * as M from "../../arc-slice/src/ops-muscle";
import * as GEN from "../../arc-slice/src/ops-generate";

type GridFn = (g: Grid) => Grid | null;

// generative bases: each says "complete the structure this way"
function bases(): { name: string; fn: GridFn }[] {
  const out: { name: string; fn: GridFn }[] = [];
  out.push({ name: "completeSym", fn: (g) => M.completeSymmetry(g, background(g)) });
  out.push({ name: "periodicFill", fn: (g) => M.periodicFill(g, background(g)) });
  out.push({ name: "cross", fn: (g) => GEN.cross(g, background(g)) });
  out.push({ name: "grow", fn: (g) => GEN.grow(g, background(g)) });
  for (const m of [1,2,4,8,15]) out.push({ name: `rays${m}`, fn: (g) => GEN.drawRays(g, background(g), m) });
  return out;
}

// consistent colour map closer (the bug-finder, function form)
function close(base: GridFn, train: Pair[]): GridFn | null {
  if (train.every(p => { const got = base(p.input); return !!got && equal(got, p.output); })) return base;
  const map = new Map<number,number>();
  for (const p of train) {
    const got = base(p.input); if (!got) return null;
    if (got.length !== p.output.length || got[0].length !== p.output[0].length) return null;
    for (let y=0;y<got.length;y++) for (let x=0;x<got[0].length;x++){ const a=got[y][x],b=p.output[y][x]; if(map.has(a)&&map.get(a)!==b) return null; map.set(a,b); }
  }
  if (![...map].some(([a,b])=>a!==b)) return null;
  const fn: GridFn = (g)=>{ const got=base(g); return got? got.map(r=>r.map(v=>map.get(v)??v)) : null; };
  return train.every(p=>{ const got=fn(p.input); return !!got && equal(got,p.output); }) ? fn : null;
}

// induce the completion rule forced & consistent across ALL train pairs
export function induceComplete(train: Pair[]): { fn: GridFn; desc: string } | null {
  for (const b of bases()) {
    const c = close(b.fn, train);
    if (c) return { fn: c, desc: b.name };
  }
  return null;
}
