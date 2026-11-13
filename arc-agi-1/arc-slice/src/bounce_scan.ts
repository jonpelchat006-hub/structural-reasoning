// bounce_scan.ts — §16: the DOUBLE-BOUNCE roof search. A COMPOSITIONAL program search that JUMPS
// into territory the depth-2 (prefix×residual) engine never reaches. Ops are visited in GOLDEN-RATIO
// order (ergodic scan of the op space — the φ-bounce that fills the gap without retracing); a beam is
// pruned toward the target; a candidate is accepted when it PHASE-LOCKS (reproduces every train pair).
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
type Grid = number[][];
const eqG = (a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

// golden-ratio visiting order over the op list = the §16 bounce scan (ergodic, non-repeating)
function goldenOrder(names: string[]): string[] {
  const n = names.length, phi = (Math.sqrt(5)-1)/2, out: string[] = [], used = new Set<number>(); let x = 0;
  for (let i=0;i<n;i++){ x=(x+phi)%1; let idx=Math.floor(x*n); while(used.has(idx)) idx=(idx+1)%n; used.add(idx); out.push(names[idx]); }
  return out;
}
const OPS_ORDER = goldenOrder(OP_NAMES);

// heuristic: how close partial grids are to the targets (dims must match; then cell agreement)
function score(gs: Grid[], outs: Grid[]): number {
  let s = 0;
  for (let i=0;i<gs.length;i++){ const g=gs[i],o=outs[i];
    if(!g||g.length!==o.length||g[0].length!==o[0].length){ s -= 1; continue; }
    let eq=0,tot=g.length*g[0].length; for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++) if(g[y][x]===o[y][x]) eq++;
    s += eq/tot;
  }
  return s/gs.length;
}

type St = { grids: Grid[]; prog: [string, any][]; sc: number };

export function bounceSearch(train: any[], depth = 3, beamW = 30): ((g:Grid)=>Grid|null)|null {
  if (train.length < 2) return null;
  if (train.some((p:any)=>p.input.length*p.input[0].length>460)) return null;
  const pal = taskPalette(train);
  const outs = train.map((p:any)=>p.output);
  let beam: St[] = [{ grids: train.map((p:any)=>p.input), prog: [], sc: score(train.map((p:any)=>p.input), outs) }];
  const seen = new Set<string>();
  for (let d=0; d<depth; d++){
    const next: St[] = [];
    for (const st of beam){
      for (const op of OPS_ORDER){
        let params: any[]; try { params = (OPS as any)[op].enumerate(pal).slice(0,4); } catch { params = [{}]; }
        for (const pr of params){
          let g2: Grid[] = []; let bad = false;
          for (const g of st.grids){ let r:Grid|null=null; try{ r=applyOp({name:op,params:pr} as any, g);}catch{} if(!r){bad=true;break;} g2.push(r); }
          if (bad) continue;
          const prog: [string,any][] = [...st.prog, [op, pr]];
          if (g2.every((g,i)=>eqG(g, outs[i]))) {
            // PHASE-LOCK: a program that maps every train input->output. Reject trivial identity-only.
            if (prog.length===1 && prog[0][0]==="identity") continue;
            return (g:Grid)=>{ let cur:Grid|null=g; for(const [o,p] of prog){ if(!cur)return null; try{cur=applyOp({name:o,params:p} as any,cur);}catch{return null;} } return cur; };
          }
          const key = g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
          if (seen.has(key)) continue; seen.add(key);
          next.push({ grids: g2, prog, sc: score(g2, outs) });
        }
      }
    }
    next.sort((a,b)=>b.sc-a.sc); beam = next.slice(0, beamW);
    if (!beam.length) break;
  }
  return null;
}

// §16b SPRINGS: diagnostic search — tracks the FURTHEST-POKING spring (best near-miss program)
// so we know where to recurse/deepen, and which springs "break" (close but unlocked = where to look).
export function bounceSearchDiag(train: any[], depth = 3, beamW = 30): { prog: ((g:Grid)=>Grid|null)|null; bestScore: number; bestProg: [string,any][]|null } {
  const res: { prog: ((g:Grid)=>Grid|null)|null; bestScore: number; bestProg: [string,any][]|null } = { prog: null, bestScore: -1, bestProg: null };
  if (train.length < 2) return res;
  if (train.some((p:any)=>p.input.length*p.input[0].length>460)) return res;
  const pal = taskPalette(train); const outs = train.map((p:any)=>p.output);
  let beam: St[] = [{ grids: train.map((p:any)=>p.input), prog: [], sc: score(train.map((p:any)=>p.input), outs) }];
  const seen = new Set<string>();
  for (let d=0; d<depth; d++){
    const next: St[] = [];
    for (const st of beam){ for (const op of OPS_ORDER){
      let params:any[]; try{ params=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ params=[{}]; }
      for (const pr of params){
        let g2: Grid[]=[]; let bad=false; for (const g of st.grids){ let r:Grid|null=null; try{r=applyOp({name:op,params:pr} as any,g);}catch{} if(!r){bad=true;break;} g2.push(r); }
        if (bad) continue;
        const prog: [string,any][] = [...st.prog, [op,pr]]; const sc = score(g2, outs);
        if (sc > res.bestScore){ res.bestScore = sc; res.bestProg = prog; }
        if (g2.every((g,i)=>eqG(g,outs[i]))){ if(prog.length===1 && prog[0][0]==="identity") continue;
          res.prog = (g:Grid)=>{ let cur:Grid|null=g; for(const[o,p]of prog){ if(!cur)return null; try{cur=applyOp({name:o,params:p} as any,cur);}catch{return null;} } return cur; };
          res.bestScore = 1; res.bestProg = prog; return res; }
        const key = g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|"); if(seen.has(key)) continue; seen.add(key);
        next.push({ grids: g2, prog, sc });
      } } }
    next.sort((a,b)=>b.sc-a.sc); beam = next.slice(0, beamW); if(!beam.length) break;
  }
  return res;
}

if (require.main === module) {
  const eval_ = loadTasks(path.join(__dirname,"..","data-eval"));
  const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
  const START=+(process.argv[2]||0), END=+(process.argv[3]||eval_.length), DEPTH=+(process.argv[4]||3);
  let solved=0, net:string[]=[];
  for(let i=START;i<Math.min(END,eval_.length);i++){ const t=eval_[i];
    if(!t.test||t.test.some((te:any)=>!te.output)) continue;
    let prog:any=null; try{prog=bounceSearch(t.train, DEPTH, 30);}catch{}
    if(!prog) continue;
    const ok=t.test.every((te:any)=>{const o=prog(te.input);return o&&eqG(o,te.output);});
    if(!ok) continue; solved++; if(!verified.has(t.id)) net.push(t.id);
    if((i+1)%50===0) process.stderr.write(`[${i+1}] solved=${solved} net=${net.length}\n`);
  }
  console.log("\n=== §16 BOUNCE-SCAN (compositional, depth="+DEPTH+") on EVAL ["+START+","+END+") ===");
  console.log("solved (this range): "+solved);
  console.log("NET-NEW vs verified_eval(26): "+net.length+"   "+net.join(" "));
}
