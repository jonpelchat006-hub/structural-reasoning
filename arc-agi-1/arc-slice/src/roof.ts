// roof.ts — the FIRST ROOF tool (per-task synthesizer, the dream/imagination layer).
// Realizes the bridge architecture (SPARSE_VESICA section 12): two panels (sections of the one
// sheet) are overlaid; the right COMBINE rule is found by trying each and keeping the one that
// LOCKS across all train pairs (memory = the grooves record which rule fit); B is registered by
// trying its dihedral orientations until features mesh (non-smoothness = the registration key).
// New capability: output is HALF the input (panel-sized) — no existing same-dim residual covers it.
import { Grid } from "./grid";

type Split = { A: Grid; B: Grid };

function pickSplit(g: Grid): Split | null {
  const R = g.length, C = g[0].length;
  for (let x = 0; x < C; x++) { const col = g.map(r => r[x]); const c = col[0];
    if (c !== 0 && col.every(v => v === c)) { const A = g.map(r => r.slice(0, x)), B = g.map(r => r.slice(x + 1));
      if (A[0] && B[0] && A[0].length > 0 && A[0].length === B[0].length) return { A, B }; } }
  for (let y = 0; y < R; y++) { const row = g[y]; const c = row[0];
    if (c !== 0 && row.every(v => v === c)) { const A = g.slice(0, y), B = g.slice(y + 1);
      if (A.length && B.length && A.length === B.length) return { A, B }; } }
  if (C % 2 === 0) return { A: g.map(r => r.slice(0, C / 2)), B: g.map(r => r.slice(C / 2)) };
  if (R % 2 === 0) return { A: g.slice(0, R / 2), B: g.slice(R / 2) };
  return null;
}

const Tx: [string, (g: Grid) => Grid][] = [
  ["id", g => g],
  ["fH", g => g.map(r => r.slice().reverse())],
  ["fV", g => g.slice().reverse()],
  ["r2", g => g.slice().reverse().map(r => r.slice().reverse())],
];

export function induceRegisterCombine(nt: { input: Grid; output: Grid }[]): ((g: Grid) => Grid | null) | null {
  const ocols = new Set<number>(); for (const p of nt) for (const r of p.output) for (const v of r) if (v !== 0) ocols.add(v);
  if (ocols.size !== 1) return null; const ON = [...ocols][0];
  for (const [, tf] of Tx) {
    const T: (number | null)[] = [null, null, null, null]; let ok = true;
    for (const p of nt) {
      const s = pickSplit(p.input);
      if (!s || s.A.length !== p.output.length || s.A[0].length !== p.output[0].length
            || s.B.length !== p.output.length || s.B[0].length !== p.output[0].length) { ok = false; break; }
      const B = tf(s.B);
      for (let y = 0; y < p.output.length && ok; y++) for (let x = 0; x < p.output[0].length; x++) {
        const av = s.A[y][x] !== 0 ? 1 : 0, bv = B[y][x] !== 0 ? 1 : 0, idx = av * 2 + bv;
        const ov = p.output[y][x] !== 0 ? 1 : 0;
        if (T[idx] === null) T[idx] = ov; else if (T[idx] !== ov) { ok = false; break; }
      }
      if (!ok) break;
    }
    if (!ok || T.some(v => v === null)) continue;
    const dependsB = T[0] !== T[1] || T[2] !== T[3];
    const dependsA = T[0] !== T[2] || T[1] !== T[3];
    if (!dependsB || !dependsA) continue;
    const TT = T as number[];
    return (g: Grid) => {
      const s = pickSplit(g); if (!s) return null; const B = tf(s.B);
      if (s.A.length !== B.length || s.A[0].length !== B[0].length) return null;
      return s.A.map((r, y) => r.map((_, x) => {
        const av = s.A[y][x] !== 0 ? 1 : 0, bv = B[y][x] !== 0 ? 1 : 0; return TT[av * 2 + bv] ? ON : 0;
      }));
    };
  }
  return null;
}
