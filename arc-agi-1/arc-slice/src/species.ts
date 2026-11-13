// species.ts — §26: SPECIES = solving genomes (§19 DNA); do they reflect the "planet composition"?
// Jonathan: different species = starting on different branches and wandering the webbing with certain dusts
// layered on; they should reflect the planet's element composition — as life is ~96% CHNOPS (light+reactive),
// not heavy inert metals. Test from the live event log (genomes) + atom_cards (element types).
// Also classifies each genome's transitions as ELECTRON-ONLY (reuse an existing wire = conduct, cheap) vs
// NUCLEUS-MOVE (a new edge = restructure, costly) — idea #7: electron-only paths are the "free" ones.
import * as path from "path"; import * as fs from "fs";
const ROOT=path.join(__dirname,"..");
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(ROOT,f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,number>={}, KNOT:Record<string,number>={};
for(const c of CARDS){ VAL[c.op]=(c.valence||[]).length; KNOT[c.op]=(c.knot||[]).length; }
const kind=(o:string)=> (VAL[o]??2)===0 ? "metal" : (VAL[o]??2)>=3 ? "organic" : "mid";  // inert vs reactive

// genomes (species) from the log
const LOG=path.join(ROOT,"scan_events.jsonl"); const genomes:string[][]=[];
if(fs.existsSync(LOG)) for(const line of fs.readFileSync(LOG,"utf8").split("\n")){ if(!line.trim())continue;
  let ev:any; try{ev=JSON.parse(line);}catch{continue;}
  if(ev.kind==="solved" && ev.path && /^[a-zA-Z]+(>[a-zA-Z]+)+$/.test(ev.path)) genomes.push(ev.path.split(">")); }
const uniq=[...new Set(genomes.map(g=>g.join(">")))].map(s=>s.split(">"));

console.log("=== §26 SPECIES & PLANET COMPOSITION ("+uniq.length+" distinct genomes) ===");

// 1. PLANET COMPOSITION — element usage across all genomes vs the DSL baseline
const usage:Record<string,number>={}; let total=0;
for(const g of uniq) for(const o of g){ usage[o]=(usage[o]||0)+1; total++; }
const cnt={metal:0,mid:0,organic:0}; for(const o in usage) (cnt as any)[kind(o)]+=usage[o];
const dsl={metal:0,mid:0,organic:0}; for(const o of Object.keys(VAL)) (dsl as any)[kind(o)]++;
const dslN=Object.keys(VAL).length;
console.log("\n[1] COMPOSITION of solutions vs the DSL 'crust':");
for(const k of ["organic","mid","metal"]){ const sol=(cnt as any)[k]/total, base=(dsl as any)[k]/dslN;
  console.log("   "+k.padEnd(8)+" solutions="+(sol*100).toFixed(0)+"%   DSL baseline="+(base*100).toFixed(0)+"%   enrichment="+(sol/base).toFixed(2)+"x"); }
console.log("   -> life-like if ORGANIC is enriched over baseline (solutions built from light reactive ops, like CHNOPS).");

// 2. SPECIES by starting branch (first op) — different lineages
console.log("\n[2] SPECIES by starting branch (first op = the branch a lineage began on):");
const byStart:Record<string,string[]>={}; for(const g of uniq){ (byStart[g[0]]=byStart[g[0]]||[]).push(g.join(">")); }
for(const [s,gs] of Object.entries(byStart)) console.log("   from "+s+" ["+kind(s)+"]: "+gs.length+" species -> "+gs.slice(0,3).join(" | "));

// 3. ELECTRON-ONLY vs NUCLEUS-MOVE transitions (idea #7): reuse a laid wire = conduct; new edge = restructure
const map=readJSON("scan_map.json"); const wires=new Set<string>(); if(map&&map.wires) for(const w of Object.values(map.wires) as any[]) wires.add(w.edge);
let eOnly=0, nMove=0;
for(const g of uniq) for(let i=0;i+1<g.length;i++){ (wires.has(g[i]+">"+g[i+1]) ? eOnly++ : nMove++); }
console.log("\n[3] TRANSITIONS: electron-only (reuse a wire, cheap conduct)="+eOnly+"   nucleus-move (new edge, restructure)="+nMove);
console.log("   -> as wires accumulate, more transitions become electron-only = decoupled from the nucleus = 'free' (conductive).");

// 4. most-used elements (the abundant ones that build most species)
console.log("\n[4] MOST-USED ELEMENTS (the abundant building blocks):");
for(const [o,n] of Object.entries(usage).sort((a,b)=>b[1]-a[1]).slice(0,10)) console.log("   "+o.padEnd(14)+" x"+n+"  ["+kind(o)+" v"+(VAL[o]??2)+" w"+(KNOT[o]??3)+"]");
