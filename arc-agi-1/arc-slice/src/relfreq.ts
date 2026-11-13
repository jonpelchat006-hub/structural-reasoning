import * as path from "path";
import { loadTasks } from "./loader";
import { detect } from "./relations";
const tasks = loadTasks(path.join(__dirname,"..","data"));
const freq = new Map<string,number>(); let i=0, anyTag=0;
for (const t of tasks) {
  if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
  const tags = detect(t.train);
  if (tags.length) anyTag++;
  for (const tag of tags) freq.set(tag,(freq.get(tag)??0)+1);
}
console.log(`\n=== RELATION FREQUENCY over ${tasks.length} ARC-1 tasks ===`);
console.log(`tasks with >=1 detected relation: ${anyTag}/${tasks.length}`);
[...freq.entries()].sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log(`  ${String(v).padStart(3)}  ${k}`));
