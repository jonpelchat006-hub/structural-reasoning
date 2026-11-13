// learn.ts — META-LEARN priors (ComponentLibrary style): which INDUCER solves which
// KIND of task. Feature bucket = distribution-level signature (dims/obj/colour/sym),
// so the learned prior transfers (it's "this type of task -> try this inducer first",
// not memorized task ids). Trained on TRAINING, applied to EVAL.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { solveDiscovery } from "./discover";
import { components } from "./objects";
type Grid=number[][];
const counts=(g:Grid)=>{const c=new Array(10).fill(0);for(const r of g)for(const v of r)if(v<10)c[v]++;return c;};
const nObj=(g:Grid)=>components(g,0,"blob").length;
const symDef=(g:Grid)=>{const r=g.length,c=g[0].length;let d=0,t=0;for(let y=0;y<r;y++)for(let x=0;x<c;x++){t++;if(g[y][x]!==g[y][c-1-x])d++;}return d/t;};
export function featureSig(train:any[]):string{
  let dims="same",obj="same",col="no",sym="no";
  const p=train[0]; const ai=p.input.length*p.input[0].length, ao=p.output.length*p.output[0].length;
  dims = ao>ai?"bigger":ao<ai?"smaller":"same";
  const no=nObj(p.output)-nObj(p.input); obj = no>0?"more":no<0?"fewer":"same";
  const ci=counts(p.input),co=counts(p.output); col = ci.some((v,k)=>v!==co[k])?"yes":"no";
  if(dims==="same"){ sym = Math.abs(symDef(p.input)-symDef(p.output))>0.01?"yes":"no"; }
  return `dims:${dims}|obj:${obj}|col:${col}|sym:${sym}`;
}

if (require.main === module) {
  const tasks=loadTasks(path.join(__dirname,"..","data"));
  const priors:Record<string,Record<string,number>>={}; const globalC:Record<string,number>={};
  let solved=0;
  for(const t of tasks){ const r=solveDiscovery(t.train); if(!r) continue;
    const inducer=r.kind.split("∘")[1]||r.kind; const sig=featureSig(t.train);
    (priors[sig]??={}); priors[sig][inducer]=(priors[sig][inducer]??0)+1; globalC[inducer]=(globalC[inducer]??0)+1; solved++; }
  // rank inducers per bucket
  const ranked:Record<string,string[]>={};
  for(const [sig,m] of Object.entries(priors)) ranked[sig]=Object.entries(m).sort((a,b)=>b[1]-a[1]).map(e=>e[0]);
  const globalOrder=Object.entries(globalC).sort((a,b)=>b[1]-a[1]).map(e=>e[0]);
  fs.writeFileSync(path.join(__dirname,"..","learned_priors.json"),JSON.stringify({ranked,globalOrder},null,1));
  console.log(`learned from ${solved} training discovery-solves over ${Object.keys(ranked).length} task-types:`);
  for(const [sig,order] of Object.entries(ranked)) console.log(`  ${sig.padEnd(40)} -> ${order.join(" > ")}`);
  console.log(`\nglobal inducer order: ${globalOrder.join(" > ")}`);
}
