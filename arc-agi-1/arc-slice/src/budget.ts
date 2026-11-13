// budget.ts — §28: CONSERVATION OF DUST. Searches produce a FINITE amount of each ingredient; you cannot
// cycle an ingredient forever (fixes §27's clique collapse). Bonding LOCKS free dust into a compound
// (Fe+O -> rust: not separable back into free atoms) — reuse needs a DECOMPOSITION step at a cost. And a
// foundation "vein" pumps out product only while its problems remain; once solved, the product FAILS and
// production stops; eventually the dust runs out. Grounded in Jonathan's conservation cascade.
import * as path from "path"; import * as fs from "fs";
const ROOT=path.join(__dirname,"..");
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(ROOT,f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,Set<string>>={};
for(const c of CARDS){ VAL[c.op]=new Set(c.valence||[]); }
const affinity=(a:string,b:string)=>a===b?0:[...(VAL[a]||[])].filter(x=>(VAL[b]||new Set()).has(x)).length;

// INVENTORY = dust produced by searches: count each op's appearances across logged solving paths.
const LOG=path.join(ROOT,"scan_events.jsonl"); const produced:Record<string,number>={};
if(fs.existsSync(LOG)) for(const line of fs.readFileSync(LOG,"utf8").split("\n")){ if(!line.trim())continue;
  let ev:any; try{ev=JSON.parse(line);}catch{continue;}
  if(ev.kind==="solved" && ev.path && /[a-zA-Z]/.test(ev.path)) for(const o of String(ev.path).split(/[>+]/)) if(VAL[o]!==undefined) produced[o]=(produced[o]||0)+1; }
const free:Record<string,number>={...produced}; const bonded:Record<string,number>={};
const totalDust=Object.values(free).reduce((s,x)=>s+x,0);

console.log("=== §28 CONSERVATION OF DUST (finite inventory from searches) ===");
console.log("dust produced by searches (free inventory): "+Object.keys(produced).length+" element types, "+totalDust+" units");
console.log("   "+Object.entries(produced).sort((a,b)=>b[1]-a[1]).map(([o,n])=>o+":"+n).join("  "));

// BUDGETED CYCLE: channel most-reactive AVAILABLE (free>0) dark matter; consume it; when depleted, SWITCH.
console.log("\n[budgeted cycle] conservation forces diversity (contrast §27's infinite keepLargest clique):");
const avail=()=>Object.keys(free).filter(o=>free[o]>0);
let cur=avail().sort((a,b)=>free[b]-free[a])[0]; const chain:string[]=[]; let switches=0, mined=0;
if(cur){ chain.push(cur); free[cur]--; }
for(let step=0; step<20 && cur; step++){
  // next = most-reactive ingredient we still HAVE in stock
  const cands=avail().filter(o=>o!==cur && affinity(cur,o)>0).sort((a,b)=>affinity(cur,b)-affinity(cur,a)||free[b]-free[a]);
  let next=cands[0];
  if(!next){ // no reactive ingredient left in stock -> must mine dark matter from ANOTHER search
    mined++; const any=avail().filter(o=>o!==cur); if(!any.length){ console.log("   (all dust consumed — supply exhausted, must run a NEW search to produce more)"); break; }
    next=any.sort((a,b)=>free[b]-free[a])[0]; console.log("   * ingredient ran out near "+cur+" -> mine another search's dark matter -> "+next);
  }
  // BOND: lock one unit of each endpoint into the compound (rust) — no longer free
  free[next]--; bonded[cur]=(bonded[cur]||0)+1; bonded[next]=(bonded[next]||0)+1;
  if(cands[0]!==next) switches++;
  chain.push(next); cur=next;
}
console.log("   grown compound: "+chain.join(">"));
console.log("   length "+chain.length+" (finite — stops when reactive stock runs out; "+mined+" cross-search mines)");

// CONSERVATION LEDGER: free + bonded is conserved (nothing created except by new searches)
const freeLeft=Object.values(free).reduce((s,x)=>s+x,0), bondedTot=Object.values(bonded).reduce((s,x)=>s+x,0);
console.log("\n[ledger] conservation:  produced="+totalDust+"   free-left="+freeLeft+"   bonded(locked in compounds)="+bondedTot+"   (free+bonded includes double-count of bonds)");

// Fe+O -> RUST: a bonded pair cannot be reused as free atoms; recovery needs DECOMPOSITION at a cost
console.log("\n[rust] bonded matter is LOCKED (can't reuse the free atom). Recover only by decomposition (a cost):");
for(const [o,n] of Object.entries(bonded).sort((a,b)=>b[1]-a[1]).slice(0,6)) console.log("   "+o+": "+n+" units bonded  -> free again only if a search DECOMPOSES the compound it sits in");

// DEPLETION: a foundation vein pumps product only while demand (unsolved tasks) remains
const map=readJSON("scan_map.json"); const inner=map&&map.entries?Object.values(map.entries).filter((e:any)=>e.shell==="inner"):[];
console.log("\n[vein] foundation points ("+inner.length+") pump product while their problems are open; once solved, the product FAILS and production stops:");
console.log("   each solved task removes its demand; when a vein's tasks are all solved, its iron stops selling -> stop mining it -> that dust frees for other veins (or runs out).");
