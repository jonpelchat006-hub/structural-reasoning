// cycle.ts — the MATTER/ANTIMATTER CYCLE. Antimatter proposes a CONSTRAINT region
// (the "electron cloud": where the answer is allowed to live); matter induces the
// FILL inside it (the "nucleus": what value goes there). A (region × fill) pair that
// closes train+test = solve; a fill matter must invent = a discovered primitive.
// They pass the partial grid: round 2 lets AM re-constrain the residual.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { taskPalette } from "./transfer";
import { equal, background } from "./grid";
import { components, Obj } from "./objects";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data"));
const combined=new Set(fs.readFileSync(path.join(__dirname,"..","combined_solved.txt"),"utf8").trim().split(/\s+/));
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const inb=(g:Grid,y:number,x:number)=>y>=0&&y<g.length&&x>=0&&x<g[0].length;

// ── ANTIMATTER: constraint regions (the cloud). Each returns the candidate cells. ──
type Region=(g:Grid,bg:number)=>[number,number][];
function regions(g:Grid,bg:number):{name:string,cells:[number,number][]}[]{
  const [r,c]=dims(g); const out:{name:string,cells:[number,number][]}[]=[];
  const all:[number,number][]=[],nonbg:[number,number][]=[],bgc:[number,number][]=[],border:[number,number][]=[];
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ all.push([y,x]); if(g[y][x]!==bg)nonbg.push([y,x]); else bgc.push([y,x]); if(y===0||x===0||y===r-1||x===c-1)border.push([y,x]); }
  out.push({name:"all",cells:all},{name:"nonbg",cells:nonbg},{name:"bg",cells:bgc},{name:"border",cells:border});
  // enclosed bg regions (holes)
  const seen=Array.from({length:r},()=>Array(c).fill(false)); const enclosed:[number,number][]=[];
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==bg||seen[y][x])continue; const reg:[number,number][]=[]; const st:[number,number][]=[[y,x]]; seen[y][x]=true; let edge=false;
    while(st.length){const[cy,cx]=st.pop()!;reg.push([cy,cx]);if(cy===0||cx===0||cy===r-1||cx===c-1)edge=true;for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=cy+dy,nx=cx+dx;if(inb(g,ny,nx)&&g[ny][nx]===bg&&!seen[ny][nx]){seen[ny][nx]=true;st.push([ny,nx]);}}}
    if(!edge)enclosed.push(...reg); }
  if(enclosed.length)out.push({name:"enclosed",cells:enclosed});
  // per-colour cell sets
  const cols=new Set<number>(); for(const r2 of g)for(const v of r2)if(v!==bg)cols.add(v);
  for(const col of cols){ const cc:[number,number][]=[]; for(let y=0;y<r;y++)for(let x=0;x<c;x++)if(g[y][x]===col)cc.push([y,x]); out.push({name:`colour${col}`,cells:cc}); }
  return out;
}
function dims(g:Grid):[number,number]{return [g.length,g[0].length];}

// ── MATTER: fills (the nucleus). Learn what to write in the region cells, from train. ──
// F_const: one learned colour for the whole region. F_sym: mirror partner. F_neighbor: maj neighbour.
function fitCycle(train:any[], bg:number):((g:Grid)=>Grid|null)|null{
  const regNames = regions(train[0].input,bg).map(r=>r.name);
  for(const rn of regNames){
    // F_const
    let C:number|undefined, ok=true;
    for(const p of train){ const rs=regions(p.input,bg).find(r=>r.name===rn); if(!rs){ok=false;break;}
      for(const[y,x]of rs.cells){ const v=p.output[y]?.[x]; if(v==null){ok=false;break;} if(C==null)C=v; else if(C!==v){ok=false;break;} } if(!ok)break; }
    if(ok&&C!=null){ const CC=C; const prog=(g:Grid)=>{ const rs=regions(g,bg).find(r=>r.name===rn); if(!rs)return null; const o=g.map(r=>r.slice()); for(const[y,x]of rs.cells)o[y][x]=CC; return o; };
      if(train.every(p=>{const o=prog(p.input);return o&&eqG(o,p.output);})) return prog; }
    // F_sym (mirror H/V/rot) within region
    for(const mode of [0,1,2,3]){ const fill=(g:Grid):Grid|null=>{ const [r,c]=dims(g); if(mode===3&&r!==c)return null; const o=g.map(rr=>rr.slice()); const rs=regions(g,bg).find(R=>R.name===rn); if(!rs)return null;
        for(const[y,x]of rs.cells){ let my=y,mx=x; if(mode===0)mx=c-1-x; else if(mode===1)my=r-1-y; else if(mode===2){my=r-1-y;mx=c-1-x;} else {my=x;mx=y;} if(!inb(g,my,mx))return null; o[y][x]=g[my][mx]; } return o; };
      if(train.every(p=>{const o=fill(p.input);return o&&eqG(o,p.output);})) return fill; }
    for(const by of ["rank","shape"] as const){ const f=objRecolorInRegion(train,bg,rn,by); if(f&&train.every(p=>{const o=f(p.input);return o&&eqG(o,p.output);})) return f; }
  }
  return null;
}


// object-property recolor restricted to a region (matter fill = discovered primitive in the cloud)
function objRecolorInRegion(train:any[], bg:number, rn:string, by:"rank"|"shape"):((g:Grid)=>Grid|null)|null{
  const key=(o:Obj)=>by==="shape"? o.cells.map(([y,x])=>(y-o.y0)*64+(x-o.x0)).sort((a,b)=>a-b).join(",") : "";
  const map=new Map<string,number>();
  for(const p of train){ const rs=regions(p.input,bg).find(r=>r.name===rn); if(!rs)return null; const inReg=new Set(rs.cells.map(([y,x])=>y+","+x));
    let objs=components(p.input,bg,"blob").filter(o=>o.cells.some(([y,x])=>inReg.has(y+","+x)));
    if(by==="rank")objs=objs.slice().sort((a,b)=>b.size-a.size);
    for(let r=0;r<objs.length;r++){ const o=objs[r]; const cols=new Set(o.cells.map(([y,x])=>p.output[y]?.[x])); if(cols.size!==1)return null; const oc=[...cols][0]; if(oc==null)return null;
      const k=by==="rank"?String(r):key(o); if(map.has(k)&&map.get(k)!==oc)return null; map.set(k,oc); } }
  if(!map.size)return null;
  return (g:Grid)=>{ const rs=regions(g,bg).find(r=>r.name===rn); if(!rs)return null; const inReg=new Set(rs.cells.map(([y,x])=>y+","+x)); const o=g.map(r=>r.slice());
    let objs=components(g,bg,"blob").filter(ob=>ob.cells.some(([y,x])=>inReg.has(y+","+x))); if(by==="rank")objs=objs.slice().sort((a,b)=>b.size-a.size);
    for(let r=0;r<objs.length;r++){ const c=map.get(by==="rank"?String(r):key(objs[r])); if(c==null)continue; for(const[y,x]of objs[r].cells)o[y][x]=c; } return o; };
}

// ── EXPORTED: solve one task via the matter/antimatter cooperative cycle ──
export function solveCycle(train:any[]): ((g:Grid)=>Grid|null) | null {
  if(train.some((p:any)=>p.input.length*p.input[0].length>700||p.input.length!==p.output.length||p.input[0].length!==p.output[0].length)) return null;
  const bg=background(train[0].input);
  try{ return fitCycle(train,bg); }catch{ return null; }
}

if (require.main === module) {
  let net=0; const hits:string[]=[];
  for(const t of tasks){ if(combined.has(t.id)) continue;
    const prog=solveCycle(t.train); if(!prog) continue;
    const tp=t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&eqG(o,te.output);});
    if(tp){ net++; hits.push(t.id); } }
  console.log(`matter/antimatter cycle — NET-NEW: ${net}`); hits.forEach(h=>console.log("  "+h));
}
