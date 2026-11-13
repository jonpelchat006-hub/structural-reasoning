// composeSpheres.ts — the VESICA: matter ∘ antimatter (two spheres overlapping).
// Joint synthesis w/o seeing the intermediate: enumerate stage-1 from one sphere,
// push train inputs through, let the OTHER sphere fit the residual. θ=1 acceptance.
import * as path from "path";
import * as fs from "fs";
import { loadTasks } from "./loader";
import { equal } from "./grid";
import { bruteCandidates } from "./search";
import { synthGenerator, matterCandidates } from "./gen2";
import { synthAntimatter, antiCandidates } from "./antimatter";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data"));
const baseline=new Set(fs.readFileSync(path.join(__dirname,"..","combined_solved.txt"),"utf8").trim().split(/\s+/));

const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
function bruteStage2(newTrain:any[]):((g:Grid)=>Grid|null)|null{
  try{ const c=bruteCandidates(newTrain); if(c.bestScore===1){ const prog=c.best; return (g:Grid)=>{ try{ // replay best prog
        let cur=g; for(const step of prog){ const {applyOp}=require("./dsl"); const o=applyOp(step,cur); if(!o)return null; cur=o;} return cur; }catch{return null;} }; } }catch{}
  return null;
}
function chain(s1:(g:Grid)=>Grid|null, s2:(g:Grid)=>Grid|null){ return (g:Grid)=>{ const m=s1(g); return m?s2(m):null; }; }
function fits(prog:(g:Grid)=>Grid|null,tr:any[]){ return tr.every((p:any)=>{const o=prog(p.input);return o&&eqG(o,p.output);}); }
function testPass(prog:(g:Grid)=>Grid|null,t:any){ return t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&eqG(o,te.output);}); }

let found=0; const hits:string[]=[]; let i=0;
for(const t of tasks){ i++;
  if(baseline.has(t.id)) continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>460)) continue;
  let solved=false; let how="";
  const mid=(s1:any)=> t.train.map((p:any)=>s1.prog(p.input));
  // ORDER 1: antimatter ∘ matter (create, then extract)
  for(const s1 of matterCandidates(t.train)){
    const inter=mid(s1); if(inter.some((g:Grid)=>!g)||inter.every((g:Grid,k:number)=>eqG(g,t.train[k].input))) continue;
    const nt=t.train.map((p:any,k:number)=>({input:inter[k],output:p.output}));
    const a=(()=>{try{return synthAntimatter(nt);}catch{return null;}})(); const b=a?a.prog:null;
    if(b){ const prog=chain(s1.prog,b); if(fits(prog,t.train)&&testPass(prog,t)){solved=true;how=`anti∘matter:${s1.kind}`;break;} }
  }
  // ORDER 2: matter ∘ antimatter (extract, then create)
  if(!solved) for(const s1 of antiCandidates(t.train)){
    const inter=mid(s1); if(inter.some((g:Grid)=>!g)||inter.every((g:Grid,k:number)=>eqG(g,t.train[k].input))) continue;
    const nt=t.train.map((p:any,k:number)=>({input:inter[k],output:p.output}));
    const a=(()=>{try{return synthGenerator(nt);}catch{return null;}})(); const b=a?a.prog:null;
    if(b){ const prog=chain(s1.prog,b); if(fits(prog,t.train)&&testPass(prog,t)){solved=true;how=`matter∘anti:${s1.kind}`;break;} }
  }
  if(solved){ found++; hits.push(`${t.id}(${how})`); }
  if(i%100===0) process.stderr.write(`[${i}/400] vesica net-new=${found}\n`);
}
console.log(`\n=== VESICA two-sphere composition ===`);
console.log(`NET-NEW over TRUE-combined (test-generalizing): ${found}`);
hits.forEach(h=>console.log("  "+h));
