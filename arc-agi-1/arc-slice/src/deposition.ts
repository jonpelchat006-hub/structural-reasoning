// deposition.ts — §25: AFFINITY-SORTED LAYERING on the memory's lines (grounded in Vesica Physics).
// Any compatible element layers on a branch it can bond to, sorted by affinity + weight (Jonathan). From
// atom_cards.json: reactivity=|valence| (bond sites = the reactive TAIL), weight=|knot| (inert NUCLEUS mass,
// the rigid line-core). affinity(a,b)=|valence(a) ∩ valence(b)| (they bond on a shared property).
// knot_tail_reactivity.py: the line's core is inert (won't bond); one step out is MAX reactive (templated
// deposition); far out reactivity fades -> "random dust that happens to work" (void). isotopes_chnops: the
// LIFE/organic path (light, reactive) fills the WEBBING between the heavy inert metal lines.
import * as path from "path"; import * as fs from "fs";
const ROOT=path.join(__dirname,"..");
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(ROOT,f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[];
type El={op:string; val:Set<string>; knot:Set<string>; reactivity:number; weight:number};
const EL:Record<string,El>={};
for(const c of CARDS){ EL[c.op]={op:c.op,val:new Set(c.valence||[]),knot:new Set(c.knot||[]),reactivity:(c.valence||[]).length,weight:(c.knot||[]).length}; }
const ops=Object.keys(EL);
const inter=(a:Set<string>,b:Set<string>)=>[...a].filter(x=>b.has(x)).length;
const affinity=(a:string,b:string)=>a===b?0:inter(EL[a].val,EL[b].val);            // bond on a shared reactive property
const organicScore=(o:string)=>EL[o].reactivity-EL[o].weight;                       // light + reactive = CHNOPS-like

// the copper skeleton: ops that appear on live wires (op-transition edges) in scan_map.json
const map=readJSON("scan_map.json"); const wireOps=new Set<string>(); const wireEdges=new Set<string>();
if(map&&map.wires) for(const w of Object.values(map.wires) as any[]){ const [a,b]=w.edge.split(">"); wireOps.add(a); wireOps.add(b); wireEdges.add(w.edge); }

console.log("=== §25 DEPOSITION — affinity-sorted layering ("+ops.length+" elements) ===");

// 1. reactivity ladder: inert METAL LINES (weight-heavy, valence-0) vs reactive ORGANIC (light, valence-high)
const lines=ops.filter(o=>EL[o].reactivity===0).sort((a,b)=>EL[b].weight-EL[a].weight);
const organic=ops.filter(o=>organicScore(o)>=2).sort((a,b)=>organicScore(b)-organicScore(a));
console.log("\n[1] REACTIVITY LADDER");
console.log("  INERT METAL LINES (valence 0, heavy knot = rigid structural core, won't bond):");
console.log("    "+lines.map(o=>o+"(w"+EL[o].weight+")").join(", "));
console.log("  REACTIVE ORGANIC (light + high valence = fills the webbing, CHNOPS-like):");
console.log("    "+organic.slice(0,12).map(o=>o+"(v"+EL[o].reactivity+",w"+EL[o].weight+")").join(", "));

// 2. what LAYERS ON the copper wires (near-line, templated, ordered) — dist-1 deposition
console.log("\n[2] DEPOSITION on the copper wires (what layers on each, by affinity then weight):");
if(!wireOps.size) console.log("    (no live wires yet — run solvers to lay copper first)");
for(const w of [...wireOps].slice(0,6)){
  const cands=ops.filter(o=>affinity(w,o)>0).sort((a,b)=>affinity(w,b)-affinity(w,a)||EL[b].weight-EL[a].weight).slice(0,4);
  console.log("    "+w+" (v"+EL[w].reactivity+") <- "+cands.map(o=>o+"[aff"+affinity(w,o)+"]").join(", "));
}

// 3. layered nucleation: copper -> attracts elements -> which attract others (dist-1 -> dist-2)
console.log("\n[3] LAYERED NUCLEATION (a wire op -> what bonds -> what bonds to THAT):");
const seed=[...wireOps][0]||"recolor";
const l1=ops.filter(o=>affinity(seed,o)>0).sort((a,b)=>affinity(seed,b)-affinity(seed,a)).slice(0,3);
const l2=new Set<string>(); for(const m of l1) for(const o of ops) if(o!==seed&&!l1.includes(o)&&affinity(m,o)>=2) l2.add(o);
console.log("    "+seed+"  ->L1["+l1.join(",")+"]  ->L2["+[...l2].slice(0,8).join(",")+"]");

// 4. the ORGANIC WEBBING between lines: high-affinity light-reactive PAIRS not already a wire edge
console.log("\n[4] ORGANIC WEBBING (light+reactive pairs bridging the lines, not yet a wire = candidates):");
const web:[string,string,number,number][]=[];
for(let i=0;i<organic.length;i++)for(let j=i+1;j<organic.length;j++){ const a=organic[i],b=organic[j];
  const aff=affinity(a,b); if(aff>=2 && !wireEdges.has(a+">"+b) && !wireEdges.has(b+">"+a)) web.push([a,b,aff,EL[a].weight+EL[b].weight]); }
web.sort((x,y)=>y[2]-x[2]||x[3]-y[3]); // strong affinity, then lightest (most organic) first
for(const [a,b,aff,wt] of web.slice(0,8)) console.log("    "+a+" ~ "+b+"   affinity="+aff+"  weight="+wt);

// 5. the gradient: near line = templated (max affinity), far = random dust that happens to work
const affs:number[]=[]; for(let i=0;i<ops.length;i++)for(let j=i+1;j<ops.length;j++)affs.push(affinity(ops[i],ops[j]));
const maxA=Math.max(...affs), meanA=(affs.reduce((s,x)=>s+x,0)/affs.length);
console.log("\n[5] ATTRACTION GRADIENT: max affinity="+maxA+" (near line: templated, ordered) -> mean="+meanA.toFixed(2)+
  " -> tail of aff<=1 pairs = "+affs.filter(a=>a<=1).length+"/"+affs.length+" = the far field where the line stops attracting and it's random dust that happens to work (void/roof).");
