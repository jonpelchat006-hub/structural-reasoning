// induce.ts — operator INDUCTION. Don't enumerate the move; READ it from the
// task's own examples. "Translate" is a known slot; the VECTOR is induced per
// task (per-colour displacement that maps input objects to output positions).
import { Pair } from "../../arc-slice/src/loader";
import { Grid } from "../../arc-slice/src/grid";
import { components, blank, Obj } from "../../arc-slice/src/objects";
import { background, equal } from "../../arc-slice/src/grid";

type GridFn = (g: Grid) => Grid | null;
function shapeKey(o: Obj): string { const w = o.x1-o.x0+1; return o.cells.map(([y,x])=>(y-o.y0)*w+(x-o.x0)).sort((a,b)=>a-b).join(","); }

// induce a per-colour displacement vector from the examples; apply it.
export function induceMove(train: Pair[]): GridFn | null {
  // require dims preserved
  for (const p of train) if (p.input.length!==p.output.length || p.input[0].length!==p.output[0].length) return null;
  // collect, per colour, the displacement that maps an input object to the matching output object
  const vecByColor = new Map<number, [number, number]>();
  let any = false;
  for (const { input, output } of train) {
    const bg = background(input);
    const ins = components(input, bg, "color"), outs = components(output, bg, "color");
    for (const oi of ins) {
      // match by shape+colour+size to an output object
      const m = outs.find(oo => oo.color===oi.color && oo.size===oi.size && shapeKey(oo)===shapeKey(oi));
      if (!m) return null;                    // unmatched -> not a pure move task
      const dy = m.y0 - oi.y0, dx = m.x0 - oi.x0;
      const prev = vecByColor.get(oi.color);
      if (prev && (prev[0]!==dy || prev[1]!==dx)) return null;  // inconsistent for this colour
      vecByColor.set(oi.color, [dy, dx]); any = true;
    }
  }
  if (!any) return null;
  const fn: GridFn = (g) => {
    const bg = background(g); const objs = components(g, bg, "color");
    const out = blank(g.length, g[0].length, bg);
    for (const o of objs) {
      const v = vecByColor.get(o.color) ?? [0,0];
      for (const [y,x] of o.cells) { const ny=y+v[0], nx=x+v[1]; if (ny>=0&&ny<g.length&&nx>=0&&nx<g[0].length) out[ny][nx]=g[y][x]; }
    }
    return out;
  };
  // verify on all train pairs
  for (const { input, output } of train) { const got = fn(input); if (!got || !equal(got, output)) return null; }
  return fn;
}
