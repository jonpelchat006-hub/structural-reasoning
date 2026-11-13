// bugfinder.ts — the third engine: directed credit assignment.
// Instead of searching blindly, look at WHERE a candidate's output differs from
// the expected grid and propose a targeted fix. Two deterministic repairs cover
// the common near-misses: a consistent colour remap (right shape, wrong colours)
// and a size correction (right content, wrong scale).
import { Program, run } from "./program";
import { Op } from "./dsl";
import { Pair } from "./loader";
import { solves, score } from "./verify";
import { dims, equal } from "./grid";

/** If one consistent colour mapping makes every dims-matching pair exact,
 * return prog + a cmap op that applies it. Catches "shape right, colours wrong". */
export function colorMapRepair(prog: Program, train: Pair[]): Program | null {
  const map = new Map<number, number>();
  for (const { input, output } of train) {
    const got = run(prog, input);
    if (!got) return null;
    const [gr, gc] = dims(got), [er, ec] = dims(output);
    if (gr !== er || gc !== ec) return null;           // size mismatch -> not a colour bug
    for (let y = 0; y < gr; y++) for (let x = 0; x < gc; x++) {
      const g = got[y][x], e = output[y][x];
      if (map.has(g) && map.get(g) !== e) return null;  // inconsistent -> no single remap
      map.set(g, e);
    }
  }
  const params: Record<string, number> = {};
  for (const [g, e] of map) if (g !== e) params[String(g)] = e;
  if (Object.keys(params).length === 0) return null;     // nothing to fix
  const repaired: Program = [...prog, { name: "cmap", params }];
  return solves(repaired, train) ? repaired : null;
}

/** Try appending one size-fixing op when the shape is built but the scale is off. */
export function sizeRepair(prog: Program, train: Pair[], pal: number[]): Program | null {
  const candidates: Op[] = [
    { name: "downscale", params: {} },
    { name: "trim", params: {} },
    ...[2, 3].flatMap((f) => [{ name: "scale", params: { fy: f, fx: f } } as Op]),
    ...[2, 3].flatMap((ny) => [2, 3].map((nx) => ({ name: "tile", params: { ny, nx, mirror: 0 } } as Op))),
    ...pal.map((bg) => ({ name: "crop", params: { bg } } as Op)),
  ];
  for (const op of candidates) {
    const repaired = [...prog, op];
    // cheap dims pre-check: only proceed if this size op makes every pair's dims match
    let dimsOK = true;
    for (const { input, output } of train) {
      const got = run(repaired, input);
      if (!got || got.length !== output.length || got[0].length !== output[0].length) { dimsOK = false; break; }
    }
    if (!dimsOK) continue;
    if (solves(repaired, train)) return repaired;
    const r2 = colorMapRepair(repaired, train);          // size-fix then colour-fix
    if (r2) return r2;
  }
  return null;
}

/** full repair attempt on a near-miss program. */
export function repair(prog: Program, train: Pair[], pal: number[]): Program | null {
  return colorMapRepair(prog, train) ?? sizeRepair(prog, train, pal);
}

/** diagnosis hint for biasing the swarm (does the shape exist but size/colour is off?). */
export function diagnose(prog: Program, train: Pair[]): "size" | "color" | "none" {
  let sizeOff = false, colorOff = false;
  for (const { input, output } of train) {
    const got = run(prog, input);
    if (!got) return "none";
    const [gr, gc] = dims(got), [er, ec] = dims(output);
    if (gr !== er || gc !== ec) { sizeOff = true; continue; }
    if (!equal(got, output)) colorOff = true;
  }
  return sizeOff ? "size" : colorOff ? "color" : "none";
}
