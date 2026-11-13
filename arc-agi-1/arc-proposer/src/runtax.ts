// runtax.ts — muscle taxonomy. Which muscle groups do we HAVE (families in solved
// tasks)? Which are MISSING (clusters of unsolved tasks by signature)? The biggest
// unsolved clusters = the next muscle groups to build, ranked by tasks unlocked.
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { encode } from "./signature";
import { detect } from "../../arc-slice/src/relations";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
function familyUsed(train: any): string | null {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return c.best[0].name;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return cand[0].name; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return cand[0].name; }
  const cd = solveCodon(train); if (cd) return "codon:" + cd.desc.split(/[.( ]/)[0];
  return null;
}

function main() {
  const tasks = loadTasks(DATA);
  const haveFam = new Map<string, number>();          // muscle we HAVE (solved families)
  const unsolved: { id: string; lightKey: string; light: number[]; tags: string[] }[] = [];
  let solved = 0, i = 0;
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const fam = familyUsed(t.train);
    if (fam) { solved++; haveFam.set(fam, (haveFam.get(fam) ?? 0) + 1); continue; }
    const sig = encode(t.train);
    unsolved.push({ id: t.id, lightKey: sig.light.join(""), light: sig.light, tags: detect(t.train) });
  }
  // cluster unsolved by light signature key
  const clusters = new Map<string, { ids: string[]; tags: Map<string, number> }>();
  for (const u of unsolved) {
    if (!clusters.has(u.lightKey)) clusters.set(u.lightKey, { ids: [], tags: new Map() });
    const cl = clusters.get(u.lightKey)!; cl.ids.push(u.id);
    for (const tg of u.tags) cl.tags.set(tg, (cl.tags.get(tg) ?? 0) + 1);
  }
  const ranked = [...clusters.entries()].sort((a, b) => b[1].ids.length - a[1].ids.length);

  console.log(`\n=== MUSCLE TAXONOMY (${tasks.length} tasks) ===`);
  console.log(`solved: ${solved}   unsolved: ${unsolved.length}   distinct unsolved signature-clusters: ${clusters.size}`);
  console.log(`\nMUSCLE WE HAVE (top solved families):`);
  [...haveFam.entries()].sort((a,b)=>b[1]-a[1]).slice(0,12).forEach(([f,n])=>console.log(`  ${String(n).padStart(3)}  ${f}`));
  console.log(`\nMISSING MUSCLE (biggest unsolved clusters = next groups to build):`);
  ranked.slice(0, 12).forEach(([key, cl]) => {
    const topTags = [...cl.tags.entries()].sort((a,b)=>b[1]-a[1]).slice(0,3).map(([t])=>t).join(", ");
    console.log(`  ${String(cl.ids.length).padStart(3)} tasks  sig[${key}]  ~needs: ${topTags}`);
  });
  // coverage estimate
  const top10 = ranked.slice(0,10).reduce((s,[,c])=>s+c.ids.length,0);
  console.log(`\ntop-10 clusters cover ${top10}/${unsolved.length} unsolved (${(100*top10/unsolved.length).toFixed(0)}%) -> ~10 more muscle groups address most of the gap`);
}
main();
