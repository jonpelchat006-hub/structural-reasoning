import { loadTasks } from "../../arc-slice/src/loader";
import { encode } from "./signature";
import * as fs from "fs";
const tasks = loadTasks("../arc-slice/data");
const out = tasks.map(t => {
  try { const s = encode(t.train); return { id: t.id, light: s.light, dark: s.dark }; }
  catch(e){ return { id: t.id, light: null, dark: null }; }
});
fs.writeFileSync("sig_all.json", JSON.stringify(out));
console.log("encoded", out.length, "tasks ->", out.filter(o=>o.light).length, "ok");
