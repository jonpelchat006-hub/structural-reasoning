// runmem.ts — leave-one-out recall: would the memory point us at the right
// solution family for a task it hasn't seen? Builds memory from all OTHER solved
// tasks, retrieves by resonance, checks if the true family is in the top-k.
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { encode, Signature } from "./signature";
import { Memory } from "./memory";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
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
  for (const t of tasks) { if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const fam = family(t.train); if (!fam) continue; items.push({ id: t.id, sig: encode(t.train), fam }); }

  let r1 = 0, r3 = 0;
  for (const a of items) {
    const mem = new Memory();
    for (const b of items) if (b !== a) mem.learn(b.sig, b.fam, b.id);
    const top = mem.retrieve(a.sig, 3).map(x => x.family);
    if (top[0] === a.fam) r1++;
    if (top.includes(a.fam)) r3++;
  }
  const counts = new Map<string, number>(); for (const it of items) counts.set(it.fam, (counts.get(it.fam)??0)+1);
  const topFam = [...counts.entries()].sort((x,y)=>y[1]-x[1])[0];
  console.log(`\n=== RESONANCE MEMORY — leave-one-out recall (${items.length} solved tasks, ${counts.size} families) ===`);
  console.log(`recall@1 (memory's top family is correct):  ${r1}/${items.length} = ${(100*r1/items.length).toFixed(1)}%`);
  console.log(`recall@3 (correct family in top 3):         ${r3}/${items.length} = ${(100*r3/items.length).toFixed(1)}%`);
  console.log(`baseline always-guess-"${topFam[0]}": ${(100*topFam[1]/items.length).toFixed(1)}%   uniform-random@3: ${(100*3/counts.size).toFixed(1)}%`);

  // write a real arc-learned store from ALL items (the proposer's persistent memory)
  const full = new Memory(); for (const it of items) full.learn(it.sig, it.fam, it.id);
  full.save(path.join(__dirname, "..", "arc-learned.json"));
  console.log(`\nwrote arc-learned.json (${full.learnings.length} learnings) + ${full.geoPayload().length} geo payloads ready for Mika.`);
}
main();
