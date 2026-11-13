import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { encode, distance, Signature } from "./signature";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");

// family label = the kind of solution (primary op / codon), or null
function family(train: any): string | null {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return c.best[0].name;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return cand[0].name + "+cmap"; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return cand[0].name + "+size"; }
  const cd = solveCodon(train); if (cd) return cd.desc.split("(")[0];
  return null;
}

function main() {
  const tasks = loadTasks(DATA);
  const items: { id: string; sig: Signature; fam: string }[] = [];
  let i = 0;
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const fam = family(t.train); if (!fam) continue;
    items.push({ id: t.id, sig: encode(t.train), fam });
  }
  // for each solved task, nearest-signature OTHER solved task -> same family?
  let hit = 0, tot = 0;
  for (const a of items) {
    let best: typeof a | null = null, bd = Infinity;
    for (const b of items) { if (b === a) continue; const d = distance(a.sig, b.sig); if (d < bd) { bd = d; best = b; } }
    if (best) { tot++; if (best.fam === a.fam) hit++; }
  }
  // random baseline: chance two solved tasks share family
  const counts = new Map<string, number>(); for (const it of items) counts.set(it.fam, (counts.get(it.fam)??0)+1);
  let rand = 0; for (const n of counts.values()) rand += (n/items.length) * ((n-1)/(items.length-1));
  console.log(`\n=== RESONANCE TEST: do near signatures share solution family? ===`);
  console.log(`solved (labelled) tasks: ${items.length}   distinct families: ${counts.size}`);
  console.log(`nearest-signature-neighbour shares family: ${hit}/${tot} = ${(100*hit/tot).toFixed(1)}%`);
  console.log(`random baseline (chance two share family): ${(100*rand).toFixed(1)}%`);
  console.log(`-> resonance ${(hit/tot > rand*1.3) ? "BEATS" : "~= "} baseline (lift ${(hit/tot/rand).toFixed(2)}x)`);
}
main();
