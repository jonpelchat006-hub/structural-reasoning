// grid.ts — the data type the whole slice operates on.
// An ARC grid is a 2D array of integer colors 0..9.
export type Grid = number[][];

export const dims = (g: Grid): [number, number] => [g.length, g[0]?.length ?? 0];
export const clone = (g: Grid): Grid => g.map((r) => r.slice());
export const cells = (g: Grid): number => g.length * (g[0]?.length ?? 0);

export function equal(a: Grid, b: Grid): boolean {
  if (a.length !== b.length) return false;
  for (let r = 0; r < a.length; r++) {
    if (a[r].length !== b[r].length) return false;
    for (let c = 0; c < a[r].length; c++) if (a[r][c] !== b[r][c]) return false;
  }
  return true;
}

/** Fraction of cells that match, only meaningful when dims are equal. */
export function cellMatch(a: Grid, b: Grid): number {
  const [ar, ac] = dims(a), [br, bc] = dims(b);
  if (ar !== br || ac !== bc || ar === 0) return 0;
  let hit = 0;
  for (let r = 0; r < ar; r++) for (let c = 0; c < ac; c++) if (a[r][c] === b[r][c]) hit++;
  return hit / (ar * ac);
}

/** Colors actually used in a grid (the task's palette feeds operator params). */
export function palette(g: Grid): number[] {
  const s = new Set<number>();
  for (const row of g) for (const v of row) s.add(v);
  return [...s].sort((x, y) => x - y);
}

/** Most common color = presumed background. */
export function background(g: Grid): number {
  const count = new Map<number, number>();
  for (const row of g) for (const v of row) count.set(v, (count.get(v) ?? 0) + 1);
  let best = 0, bestN = -1;
  for (const [v, n] of count) if (n > bestN) { best = v; bestN = n; }
  return best;
}
