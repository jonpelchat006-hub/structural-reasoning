// ops-fractal.ts — self-similar tiling (the classic ARC fractal pattern).
import { Grid, dims } from "./grid";
import { blank } from "./objects";

// output is r×c blocks (each the r×c input); block (by,bx) = input where
// input[by][bx] != bg, else blank. r×c -> r²×c². (e.g. 3×3 -> 9×9)
export function fractalTile(g: Grid, bg: number, invert: number): Grid | null {
  const [r, c] = dims(g);
  if (r * r * c * c > 2500) return null;
  const out = blank(r * r, c * c, bg);
  for (let by = 0; by < r; by++) for (let bx = 0; bx < c; bx++) {
    const present = invert ? (g[by][bx] === bg) : (g[by][bx] !== bg);
    if (!present) continue;
    for (let i = 0; i < r; i++) for (let j = 0; j < c; j++) out[by * r + i][bx * c + j] = g[i][j];
  }
  return out;
}

// mirror-concatenate the grid with its reflection (h = beside, v = below)
export function mirrorConcat(g: Grid, dir: number): Grid | null {
  const [r, c] = dims(g);
  if (dir === 0) { // right: g | flipH(g)
    if (c * 2 > 60) return null;
    return g.map(row => [...row, ...row.slice().reverse()]);
  }
  if (r * 2 > 60) return null; // down: g over flipV(g)
  return [...g.map(x=>x.slice()), ...g.slice().reverse().map(x=>x.slice())];
}
