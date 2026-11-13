// topo.ts — the TOPOLOGY lift: inducers keyed on holes / enclosure (the axis eval lives in,
// 200/400 tasks at 8%). The discrete "lift into the torus dimension" — the solver was blind to
// enclosed interiors; these see them. Generalize holeFill (one fixed colour) to per-hole colour
// determined by the ENCLOSING structure or the hole's SIZE-RANK. Self-contained.
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

// enclosed bg regions (holes not touching the border), with the colour that surrounds them.
function enclosedRegions(g:Grid,bg:number){
  const R=g.length,C=g[0].length; const seen=Array.from({length:R},()=>Array(C).fill(false));
  const regions:{cells:[number,number][],encloser:number}[]=[];
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){
    if(g[y][x]!==bg||seen[y][x])continue;
    const cells:[number,number][]=[]; const st:[number,number][]=[[y,x]]; seen[y][x]=true; let edge=false; const bord=new Set<number>();
    while(st.length){ const [cy,cx]=st.pop()!; cells.push([cy,cx]); if(cy===0||cx===0||cy===R-1||cx===C-1)edge=true;
      for(const [dy,dx] of [[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=cy+dy,nx=cx+dx; if(ny<0||ny>=R||nx<0||nx>=C)continue;
        if(g[ny][nx]===bg){ if(!seen[ny][nx]){seen[ny][nx]=true;st.push([ny,nx]);} } else bord.add(g[ny][nx]); } }
    if(!edge) regions.push({cells, encloser: bord.size===1?[...bord][0]:-1});
  }
  return regions;
}

// each hole filled with a colour keyed by its ENCLOSING colour (learned map).
export function induceHoleFillByEncloser(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  const map=new Map<number,number>(); let any=false;
  for(const p of nt){ for(const reg of enclosedRegions(p.input,bg)){ const cols=new Set(reg.cells.map(([y,x])=>p.output[y][x])); if(cols.size!==1) return null; const fc=[...cols][0] as number; if(fc===bg) continue; any=true; if(map.has(reg.encloser)&&map.get(reg.encloser)!==fc) return null; map.set(reg.encloser,fc); } }
  if(!any) return null;
  const apply=(g:Grid):Grid|null=>{ const out=g.map(r=>r.slice()); for(const reg of enclosedRegions(g,bg)){ const fc=map.get(reg.encloser); if(fc==null) continue; for(const [y,x] of reg.cells) out[y][x]=fc; } return out; };
  return nt.every(p=>eqG(apply(p.input)!,p.output)) ? apply : null;
}

// each hole filled with a colour keyed by its SIZE-RANK (largest hole = rank 0, …): learned map.
export function induceHoleFillByRank(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  const map=new Map<number,number>(); let any=false;
  for(const p of nt){ const regs=enclosedRegions(p.input,bg).slice().sort((a,b)=>b.cells.length-a.cells.length);
    for(let r=0;r<regs.length;r++){ const reg=regs[r]; const cols=new Set(reg.cells.map(([y,x])=>p.output[y][x])); if(cols.size!==1) return null; const fc=[...cols][0] as number; if(fc===bg) continue; any=true; if(map.has(r)&&map.get(r)!==fc) return null; map.set(r,fc); } }
  if(!any) return null;
  const apply=(g:Grid):Grid|null=>{ const out=g.map(r=>r.slice()); const regs=enclosedRegions(g,bg).slice().sort((a,b)=>b.cells.length-a.cells.length); for(let r=0;r<regs.length;r++){ const fc=map.get(r); if(fc==null) continue; for(const [y,x] of regs[r].cells) out[y][x]=fc; } return out; };
  return nt.every(p=>eqG(apply(p.input)!,p.output)) ? apply : null;
}
