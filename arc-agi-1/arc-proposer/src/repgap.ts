// repgap.ts — representation-gap diagnostic. For each task classify WHAT its
// input->output actually CHANGES. Over the UNSOLVED set, the dominant change-types
// are the dimensions we don't yet represent/operate on — what to add next.
import { Pair } from "../../arc-slice/src/loader";
import { background } from "../../arc-slice/src/grid";
import { components } from "../../arc-slice/src/objects";

const palette = (g: number[][]) => new Set(g.flat());
const nonbg = (g: number[][], bg: number) => g.reduce((s,r)=>s+r.filter(v=>v!==bg).length,0);

export function changeTypes(train: Pair[]): string[] {
  const tags = new Set<string>();
  for (const { input, output } of train) {
    const bi = background(input), bo = background(output);
    const dimSame = input.length===output.length && input[0].length===output[0].length;
    if (!dimSame) { tags.add("DIM_CHANGE"); 
      tags.add(output.length*output[0].length > input.length*input[0].length ? "GROW" : "SHRINK"); }
    const oi = components(input, bi, "color"), oo = components(output, bo, "color");
    if (oo.length !== oi.length) tags.add("COUNT_CHANGE");
    // palette change
    const pi=[...palette(input)].sort().join(), po=[...palette(output)].sort().join();
    if (pi!==po) tags.add("PALETTE_CHANGE");
    if (dimSame) {
      // ink added / removed
      const ni=nonbg(input,bi), no=nonbg(output,bo);
      if (no>ni*1.1) tags.add("INK_ADDED"); if (no<ni*0.9) tags.add("INK_REMOVED");
      // recolor-only? same non-bg mask, different colours
      let sameMask=true, colorDiff=false;
      for (let y=0;y<input.length&&sameMask;y++) for (let x=0;x<input[0].length;x++){
        const a=input[y][x]!==bi, b=output[y][x]!==bo;
        if (a!==b){sameMask=false;break;} if (a&&b&&input[y][x]!==output[y][x]) colorDiff=true;
      }
      if (sameMask && colorDiff) tags.add("RECOLOR_ONLY");
      if (!sameMask) tags.add("MASK_CHANGE");
      // moved: same multiset of object shapes, different positions
      const sig=(os:any[])=>os.map(o=>`${o.size}:${o.color}`).sort().join("|");
      if (sig(oi)===sig(oo)) { const pos=(os:any[])=>os.map(o=>`${o.y0},${o.x0}`).sort().join("|"); if (pos(oi)!==pos(oo)) tags.add("MOVED"); }
      else tags.add("SHAPE_OR_SET_CHANGE");
    }
  }
  return [...tags];
}
