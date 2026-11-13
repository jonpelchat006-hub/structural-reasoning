// seam.ts — classify_seam_profile ported to grids. Read the SHAPE of the diff
// against the solid task, then route to a shape-specific repair. New capability
// over the old bug-finder: uniform_offset -> a TRANSLATION the diff reveals.
import { Pair } from "../../arc-slice/src/loader";
import { Program, run } from "../../arc-slice/src/program";
import { solves } from "../../arc-slice/src/verify";
import { components } from "../../arc-slice/src/objects";
import { background } from "../../arc-slice/src/grid";

export type Seam = "spike" | "bimodal" | "uniform_offset" | "uniform_close" | "distributed" | "none";

// classify the diff shape on one pair (dims must match)
function classifyOne(got: number[][], exp: number[][], bg: number): Seam {
  const r = got.length, c = got[0].length;
  const mask: number[][] = Array.from({ length: r }, () => Array(c).fill(0));
  let wrong = 0;
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (got[y][x] !== exp[y][x]) { mask[y][x] = 1; wrong++; }
  if (wrong === 0) return "none";
  const frac = wrong / (r * c);
  if (frac > 0.6) return "distributed";
  // connected error regions
  const regions = components(mask.map(row => row.map(v => v ? 1 : bg)), bg, "blob").filter(o => o.color === 1);
  if (regions.length === 1) return frac < 0.15 ? "spike" : "uniform_offset";
  if (regions.length === 2) return "bimodal";
  if (frac < 0.1) return "uniform_close";
  return "uniform_offset";
}

export function classifySeam(prog: Program, train: Pair[]): Seam {
  const labels = new Set<Seam>();
  for (const { input, output } of train) {
    const got = run(prog, input);
    if (!got || got.length !== output.length || got[0].length !== output[0].length) return "none";
    labels.add(classifyOne(got, output, background(output)));
  }
  labels.delete("none");
  if (labels.size === 0) return "none";
  return [...labels][0];   // dominant; consistent tasks have one label
}

// uniform_offset repair: find the single (dy,dx) translation that aligns
// got -> expected on EVERY pair, then append a shift op.
export function seamRepair(base: Program, train: Pair[]): Program | null {
  // gather got/exp; require dims match
  const pairs: { got: number[][]; exp: number[][]; bg: number }[] = [];
  for (const { input, output } of train) {
    const got = run(base, input);
    if (!got || got.length !== output.length || got[0].length !== output[0].length) return null;
    pairs.push({ got, exp: output, bg: background(output) });
  }
  // search a consistent translation
  for (let dy = -5; dy <= 5; dy++) for (let dx = -5; dx <= 5; dx++) {
    if (dy === 0 && dx === 0) continue;
    let ok = true;
    for (const { got, exp, bg } of pairs) {
      const r = got.length, c = got[0].length;
      for (let y = 0; y < r && ok; y++) for (let x = 0; x < c; x++) {
        const sy = y - dy, sx = x - dx;
        const v = (sy >= 0 && sy < r && sx >= 0 && sx < c) ? got[sy][sx] : bg;
        if (v !== exp[y][x]) { ok = false; break; }
      }
      if (!ok) break;
    }
    if (ok) {
      const bg = pairs[0].bg;
      const repaired: Program = [...base, { name: "shift", params: { dy, dx, bg } }];
      if (solves(repaired, train)) return repaired;
    }
  }
  return null;
}
