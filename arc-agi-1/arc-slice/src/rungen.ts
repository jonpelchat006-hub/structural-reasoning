import * as path from "path";
import { loadTasks } from "./loader";
import { bruteCandidates } from "./search";
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { solveCodon } from "./codon";
import { induceGenerator } from "./generator";
import { OP_NAMES } from "./dsl";
import { equal, palette } from "./grid";

const tasks = loadTasks(path.join(__dirname,"..","data"));
const solves=(prog:any,train:any[])=>train.every((p:any)=>{try{const o=require("./nested").runProgram?null:null;}catch{} return true;});

function fastSolved(t:any):boolean {
  const c = bruteCandidates(t.train, OP_NAMES);
  for (const cand of c.colorCands) { const f=colorMapRepair(cand,t.train); if(f) return true; }
  const pal = Array.from(new Set(t.train.flatMap((p:any)=>palette(p.input))));
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f=sizeRepair(cand,t.train,pal as number[]); if(f) return true; }
  return false;
}
function eqAll(prog:any,train:any[]){ return train.every((p:any)=>{const o=prog(p.input); return o&&equal(o,p.output);}); }

let fast=0, gen=0, genNew=0; const newHits:string[]=[]; const allGen:string[]=[];
let i=0;
for (const t of tasks) {
  i++;
  if (t.train.some((p:any)=>p.input.length*p.input[0].length>900)) continue;
  let f=false;
  try { f=fastSolved(t); } catch {}
  if (f) fast++;
  let g:any=null;
  try { g=induceGenerator(t.train); } catch {}
  const gWorks = g && eqAll(g,t.train);
  if (gWorks) { gen++; allGen.push(t.id); if(!f){ genNew++; newHits.push(t.id);} }
  if (i%100===0) console.error(`[${i}/400]`);
}
console.log(`\n=== GENERATOR vs transformer ===`);
console.log(`transformer fast-solved: ${fast}`);
console.log(`generator solves (any): ${gen}`);
console.log(`generator NET-NEW (transformer missed): ${genNew}`);
console.log(`net-new ids: ${newHits.join(" ")}`);
console.log(`all generator ids: ${allGen.join(" ")}`);
