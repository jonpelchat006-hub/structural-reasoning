// cycles.ts — §29: the CLOSED-CYCLE MAP EXPANDER. Not a solver — a REACHABILITY explorer. Jonathan: before
// committing a reaction (making rust), force finding the RETURN PATH too — a complete cycle back to start.
// That forces exploring more than needed, which WIDENS the map. The answers aren't ON these void lines; the
// job is to expand the domain so target points fall in reach, then the real solvers work from better starts.
// Economic/evolutionary: cycles fight for the finite dust (§28), and we gamble the budget on the best EV.
import * as path from "path"; import * as fs from "fs";
const ROOT=path.join(__dirname,"..");
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(ROOT,f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,Set<string>>={};
for(const c of CARDS) VAL[c.op]=new Set(c.valence||[]);
const ops=Object.keys(VAL);
const aff=(a:string,b:string)=>a===b?0:[...(VAL[a]||[])].filter(x=>(VAL[b]||new Set()).has(x)).length;
const THRESH=2; // a reaction happens if affinity >= THRESH
const nbr:Record<string,string[]>={}; for(const a of ops) nbr[a]=ops.filter(b=>aff(a,b)>=THRESH);

// dust inventory (§28): scarcity = 1/(units produced). Unproduced ops are "dark matter" (must be mined).
const LOG=path.join(ROOT,"scan_events.jsonl"); const inv:Record<string,number>={};
if(fs.existsSync(LOG)) for(const line of fs.readFileSync(LOG,"utf8").split("\n")){ if(!line.trim())continue;
  let ev:any; try{ev=JSON.parse(line);}catch{continue;} if(ev.kind==="solved"&&ev.path) for(const o of String(ev.path).split(/[>+]/)) if(VAL[o]!==undefined) inv[o]=(inv[o]||0)+1; }
const scarcity=(o:string)=>1/((inv[o]||0)+1);

// seeds = the produced ops we actually have dust for (our current territory)
const seeds=ops.filter(o=>inv[o]>0);
console.log("=== §29 CLOSED-CYCLE MAP EXPANDER (reachability, not solving) ===");
console.log("seeds (ops we have dust for): "+seeds.length+" -> "+seeds.join(", "));

// ONE-WAY reachability (BFS) — where a forward-only search can wander
const oneway=new Set(seeds); { const q=[...seeds]; while(q.length){ const x=q.shift()!; for(const y of nbr[x]) if(!oneway.has(y)){oneway.add(y);q.push(y);} } }

// CLOSED-CYCLE reachability: an op is COMMITTABLE only if it lies on a cycle that RETURNS to a seed.
// DFS up to length L, requiring the path to close back to its seed. Count ops visited during return search.
const L=6; const committable=new Set<string>(); let visited=new Set<string>(), pathsTried=0;
function dfs(seed:string, cur:string, depth:number, onpath:Set<string>){
  if(pathsTried>200000) return; pathsTried++;
  for(const nx of nbr[cur]){ visited.add(nx);
    if(nx===seed && depth>=2){ for(const o of onpath) committable.add(o); continue; } // cycle closed -> whole loop committable
    if(depth<L && !onpath.has(nx)){ onpath.add(nx); dfs(seed,nx,depth+1,onpath); onpath.delete(nx); }
  }
}
for(const s of seeds){ committable.add(s); dfs(s,s,1,new Set([s])); }

console.log("\n[coverage] map expansion:");
console.log("   one-way reachable domain: "+oneway.size+"/"+ops.length+" ops ("+(100*oneway.size/ops.length).toFixed(0)+"%)");
console.log("   CLOSED-CYCLE committable (returnable, safe territory): "+committable.size+"/"+ops.length+" ("+(100*committable.size/ops.length).toFixed(0)+"%)");
console.log("   ops touched while forced to find return paths (widened map): "+visited.size+"  <- over-exploration beyond the "+seeds.length+" seeds");

// EVOLUTION / BUDGET: enumerate short closed cycles from seeds, cost = sum scarcity, EV = reactivity/cost.
type Cyc={loop:string[]; react:number; cost:number; ev:number};
const cycles:Cyc[]=[]; const seen=new Set<string>();
function findC(seed:string,cur:string,depth:number,onpath:string[]){
  if(cycles.length>4000) return;
  for(const nx of nbr[cur]){
    if(nx===seed && depth>=2){ const loop=[...onpath]; const key=[...loop].sort().join(","); if(!seen.has(key)){ seen.add(key);
      let react=0; for(let i=0;i<loop.length;i++)react+=aff(loop[i],loop[(i+1)%loop.length]);
      const cost=loop.reduce((s,o)=>s+scarcity(o),0); cycles.push({loop,react,cost,ev:react/cost}); } continue; }
    if(depth<5 && !onpath.includes(nx)){ onpath.push(nx); findC(seed,nx,depth+1,onpath); onpath.pop(); }
  }
}
for(const s of seeds) findC(s,s,1,[s]);
cycles.sort((a,b)=>b.ev-a.ev);
console.log("\n[evolution/budget] closed cycles compete for finite dust — best EV (reactivity/cost) win the budget:");
for(const c of cycles.slice(0,6)) console.log("   "+c.loop.join(">")+">"+c.loop[0]+"   react="+c.react+" cost="+c.cost.toFixed(2)+" EV="+c.ev.toFixed(2));
console.log("   total viable closed cycles found: "+cycles.length+" (the reversible reaction network = the expanded map)");

console.log("\n[framing] this finds WHERE solves could be (reachable/returnable territory), not the solves");
console.log("   themselves — the answers aren't on these void lines. It hands the real solvers better starts:");
console.log("   launch closer2/dna from the "+committable.size+"-op returnable domain instead of the "+seeds.length+" raw seeds.");
