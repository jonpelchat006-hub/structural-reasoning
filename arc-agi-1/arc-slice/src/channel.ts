// channel.ts — §27: the DARK-MATTER CHANNELING CYCLE. The memory layer is the OBSERVER/router that decides
// what to pass through. Grounded in Vesica Physics: dark_matter_iceberg.py (dark matter = the PARTIALS /
// incomplete pieces, the hidden bulk — here the unexplored affine op-combinations), dark_light_transport.py
// (actively MOVE the empty containers to an ATTRACTOR, not wait), erdos-incidence-geometry (channels = lines,
// webs = incidence points; maximize productive crossings). One turn of Jonathan's cycle:
//   pass dark matter near a WEB -> see what REACTS (affinity) -> channel more there -> the reaction DISPLACES
//   a product unique to that web -> send it down the dark channel -> feed the NEXT web -> repeat (combine+explore).
import * as path from "path"; import * as fs from "fs";
const ROOT=path.join(__dirname,"..");
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(ROOT,f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,Set<string>>={}, W:Record<string,number>={};
for(const c of CARDS){ VAL[c.op]=new Set(c.valence||[]); W[c.op]=(c.knot||[]).length; }
const ops=Object.keys(VAL);
const affinity=(a:string,b:string)=>a===b?0:[...(VAL[a]||[])].filter(x=>(VAL[b]||new Set()).has(x)).length;
const reactivity=(o:string)=>(VAL[o]||new Set()).size;

// WEBS = the copper wires already laid (reactive sites); if sparse, seed from the most reactive ops
const map=readJSON("scan_map.json"); const wireEdges=new Set<string>(); const webOps=new Set<string>();
if(map&&map.wires) for(const w of Object.values(map.wires) as any[]){ const[a,b]=w.edge.split(">"); wireEdges.add(w.edge); webOps.add(a); webOps.add(b); }
if(webOps.size<2) for(const o of ops.filter(o=>reactivity(o)>=3).slice(0,3)) webOps.add(o);

console.log("=== §27 DARK-MATTER CHANNELING CYCLE ===");
console.log("WEBS (reactive sites already laid): "+[...webOps].join(", "));

// DARK MATTER = the partials: affine op-pairs NOT yet a wire (unexplored compatible combinations, the iceberg bulk)
const darkPairs:[string,string,number][]=[];
for(let i=0;i<ops.length;i++)for(let j=i+1;j<ops.length;j++){ const a=ops[i],b=ops[j],aff=affinity(a,b);
  if(aff>=2 && !wireEdges.has(a+">"+b) && !wireEdges.has(b+">"+a)) darkPairs.push([a,b,aff]); }
console.log("DARK MATTER (unexplored affine op-pairs = partials/iceberg bulk): "+darkPairs.length+" pairs");

// ONE TURN: for each web op, channel the most-reactive dark matter onto it (transport to the attractor)
console.log("\n[channel] pass dark matter near each web -> what reacts most (affinity), channel it there:");
for(const web of [...webOps].slice(0,6)){
  const react=ops.filter(o=>o!==web && affinity(web,o)>=2 && !wireEdges.has(web+">"+o)).sort((a,b)=>affinity(web,b)-affinity(web,a)||reactivity(b)-reactivity(a));
  if(react.length) console.log("   web "+web+"  <=channel=  "+react.slice(0,3).map(o=>o+"[react "+affinity(web,o)+"]").join(", ")+"   => new wire "+web+">"+react[0]);
}

// THE CYCLE: start on a web, greedily channel the most-reactive dark matter, the product feeds the next web
console.log("\n[cycle] autocatalytic exploration — product of one web feeds the next (combine + explore):");
let cur=[...webOps][0]||ops.find(o=>reactivity(o)>=3)!; const chain=[cur]; const used=new Set([cur]);
for(let step=0; step<8; step++){
  const next=ops.filter(o=>!used.has(o)&&affinity(cur,o)>=2).sort((a,b)=>affinity(cur,b)-affinity(cur,a)||reactivity(b)-reactivity(a))[0];
  if(!next)break; chain.push(next); used.add(next);
  console.log("   web "+cur+"  --react(aff "+affinity(cur,next)+")-->  product "+next+"  --dark channel-->  feeds next web");
  cur=next; // the displaced product becomes the next reactive web
}
console.log("   grown compound (a new species built by cycling): "+chain.join(">"));

// ERDOS INCIDENCE: the channel network — how many productive crossings (webs sharing a reactive property = a line)
const propLines:Record<string,string[]>={}; for(const o of [...webOps]) for(const p of (VAL[o]||[])) (propLines[p]=propLines[p]||[]).push(o);
const incidences=Object.entries(propLines).filter(([,os])=>os.length>=2);
console.log("\n[erdos] channel incidences (webs sharing a reactive property = a line through them):");
for(const [p,os] of incidences) console.log("   property '"+p+"'  line through: "+os.join(", "));
console.log("   productive lines (>=2 webs): "+incidences.length+"  — maximize these = the orchard/F_k optimum = a denser reaction network.");
