// scan_map.ts — §21/§22/§23/§24: SCAN MAP as pure REPLAY of the live event log, grounded in Vesica Physics.
// §24 grounding (Vesica AI/Physics): MASS = the snake's TRAIL (mass_as_snake_trail.py) — more trail = slower,
// which IS the §22 law. DUST accretes per bounce with the 0.14 ψ-coefficient (dust_correction.py). KNOT vs
// TAIL (ATOM_GROUNDING_RESULTS.md): the inert closed shell = the NUCLEUS mass (knot, stays, foundation);
// the reactive VALENCE/tail = where energy transfer happens = where COPPER DUST sorts into conductive wires.
// So node mass increment = the solving ops' NUCLEUS (knot) mass; and valence sites accrete conductance =
// copper wires whose resistance falls with use (electrons move more freely). Two masses = nucleus (stays)
// + electron-current (flows), exactly like a copper wire. CLI: `tsx src/scan_map.ts ingest` | `report`.
import * as path from "path"; import * as fs from "fs";
const ROOT=path.join(__dirname,"..");
const MAP=path.join(ROOT,"scan_map.json"), LOG=path.join(ROOT,"scan_events.jsonl");
type Kind="solved"|"overfit"|"nearmiss"; type Shell="inner"|"middle"|"outer";
type Entry={ id:string; seenBy:string[]; solvedBy:string[]; failedBy:string[]; touches:number; isFailure:boolean;
  mass:number; velocity:number; shell:Shell; stopped:boolean; committed:boolean; };
type Path={ path:string; uses:number; tasks:string[]; cost:number; };
type Wire={ edge:string; conductance:number; uses:number; };
const MAX_SPEED=0.5, STOP_EPS=0.08, MASS_GRAV=0.5, CACHED=0.2, DUST=0.14; // 0.14 = the ψ-dust coefficient
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(ROOT,f),"utf8"));}catch{return null;}};
// element table (atom_cards.json): knot = inert NUCLEUS mass (stays); valence = reactive TAIL (conducts)
const CARDS=readJSON("atom_cards.json")||[]; const KNOT:Record<string,number>={}, VAL:Record<string,number>={};
for(const c of CARDS){ KNOT[c.op]=(c.knot||[]).length; VAL[c.op]=(c.valence||[]).length; }
const knotOf=(o:string)=>KNOT[o]??3, valOf=(o:string)=>VAL[o]??2;
const isOpPath=(p?:string)=>!!p && /^[a-zA-Z]+(>[a-zA-Z]+)*$/.test(p);
const fresh=(id:string):Entry=>({id,seenBy:[],solvedBy:[],failedBy:[],touches:0,isFailure:false,mass:0,velocity:MAX_SPEED,shell:"outer",stopped:false,committed:false});

function strike(e:Entry, kind:Kind, nucleus:number){
  e.mass += kind==="solved" ? nucleus : 1;          // §24: dust added per bounce = the solving ops' NUCLEUS (knot) mass
  e.velocity = MAX_SPEED/(1+e.mass*MASS_GRAV);       // mass = trail → more trail → slower (mass_as_snake_trail)
  if(e.shell==="outer" && e.solvedBy.length>=1) e.shell="middle";
  if(e.shell==="middle" && e.solvedBy.length>=2) e.shell="inner";
  if(e.shell==="inner"){ e.committed=true; if(e.velocity<STOP_EPS) e.stopped=true; }
}
function replay(){
  const entries:Record<string,Entry>={}, paths:Record<string,Path>={}, wires:Record<string,Wire>={};
  if(!fs.existsSync(LOG)) return {entries,paths,wires};
  for(const line of fs.readFileSync(LOG,"utf8").split("\n")){ if(!line.trim())continue;
    let ev:any; try{ev=JSON.parse(line);}catch{continue;} if(ev.marker)continue;
    const e=entries[ev.id]||(entries[ev.id]=fresh(ev.id));
    if(!e.seenBy.includes(ev.scan))e.seenBy.push(ev.scan); e.touches++;
    // nucleus (knot) mass of this solve's ops = the trail dust to add
    let nucleus=3; if(isOpPath(ev.path)){ const ops=ev.path.split(">"); nucleus=ops.reduce((s:number,o:string)=>s+knotOf(o),0)/ops.length; }
    if(ev.kind==="solved"){ if(!e.solvedBy.includes(ev.scan))e.solvedBy.push(ev.scan); } else { if(!e.failedBy.includes(ev.scan))e.failedBy.push(ev.scan); e.isFailure=true; }
    strike(e, ev.kind, nucleus);
    if(ev.kind==="solved" && ev.path){
      const p=paths[ev.path]||(paths[ev.path]={path:ev.path,uses:0,tasks:[],cost:1});
      p.uses++; p.cost=1/(1+p.uses); if(!p.tasks.includes(ev.id))p.tasks.push(ev.id);
      // §24: COPPER DUST sorts onto valence/tail sites — each op-transition edge accretes conductance
      if(isOpPath(ev.path)){ const ops=ev.path.split(">");
        for(let i=0;i+1<ops.length;i++){ const key=ops[i]+">"+ops[i+1];
          const w=wires[key]||(wires[key]={edge:key,conductance:0,uses:0});
          w.conductance += DUST*(valOf(ops[i])+valOf(ops[i+1]))/2; w.uses++; } }
    }
  }
  return {entries,paths,wires};
}
function build(){
  const {entries,paths,wires}=replay();
  const events=fs.existsSync(LOG)?fs.readFileSync(LOG,"utf8").split("\n").filter(l=>l.trim()&&!l.includes("marker")).length:0;
  fs.writeFileSync(MAP,JSON.stringify({version:"24",updated:new Date().toISOString(),eventsReplayed:events,entries,paths,wires},null,1));
  console.log("replayed "+events+" events -> "+Object.keys(entries).length+" places, "+Object.keys(paths).length+" paths, "+Object.keys(wires).length+" wires");
  report(entries,paths,wires);
}
function report(entries?:Record<string,Entry>, paths?:Record<string,Path>, wires?:Record<string,Wire>){
  const mf=readJSON("scan_map.json");
  const E=Object.values(entries||(mf&&mf.entries)||{}) as Entry[];
  const P=Object.values(paths||(mf&&mf.paths)||{}) as Path[];
  const W=Object.values(wires||(mf&&mf.wires)||{}) as Wire[];
  const inner=E.filter(e=>e.shell==="inner"), middle=E.filter(e=>e.shell==="middle"), outer=E.filter(e=>e.shell==="outer");
  console.log("\n=== SCAN MAP §24 (nucleus mass + copper-wire conductance) — "+E.length+" places ===");
  console.log("INNER (foundation): "+inner.length+"   STOPPED (black-hole/void, pinned): "+inner.filter(e=>e.stopped).length);
  for(const e of inner.sort((a,b)=>b.mass-a.mass).slice(0,6)) console.log("   "+e.id+"  nucleusMass="+e.mass.toFixed(2)+"  vel="+e.velocity.toFixed(3)+(e.stopped?"  STOPPED":"")+"  solvedBy["+e.solvedBy.join(",")+"]");
  console.log("MIDDLE: "+middle.length+"    OUTER/dark-matter: "+outer.length+" (dense walls: "+outer.filter(e=>e.mass>=4).map(e=>e.id).slice(0,4).join(",")+")");
  console.log("\nCOPPER WIRES (valence/tail edges where current sorts; resistance=1/(1+conductance)):");
  for(const w of W.sort((a,b)=>b.conductance-a.conductance).slice(0,8)) console.log("   "+w.edge+"   conductance="+w.conductance.toFixed(3)+"  resistance="+(1/(1+w.conductance)).toFixed(3)+"  uses="+w.uses);
  const transfer=P.filter(p=>p.tasks.length>=2);
  console.log("\nPATHS: "+P.length+"   cached(cost<="+CACHED+"): "+P.filter(p=>p.cost<=CACHED).length+"   transferable(>=2 tasks): "+transfer.length);
  for(const p of P.sort((a,b)=>b.uses-a.uses).slice(0,5)) console.log("   ["+p.uses+"x cost="+p.cost.toFixed(3)+(p.cost<=CACHED?" cached":"")+"]  "+p.path);
}
const cmd=process.argv[2]||"report";
if(cmd==="ingest")build(); else report();
