// prune.ts — the PRUNE-DOWN direction (top-down from the possibility space, not built up from
// atoms). A LOCAL-RULE inducer: each output cell = a function of its input neighbourhood; every
// train cell CUTS the space of consistent neighbourhood→value rules down to the survivor, which
// is applied to test. This is constraint-propagation / the infinite→finite collapse on cells —
// it expresses local/cellular rules that op-composition (build-up) can't. Self-contained.
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

function nontrivial(nt:{input:Grid,output:Grid}[]):boolean{
  for(const p of nt)for(let y=0;y<p.input.length;y++)for(let x=0;x<p.input[0].length;x++) if(p.input[y][x]!==p.output[y][x]) return true;
  return false;
}

// EXACT 3x3 neighbourhood (bg-padded) → output value. Strict: a consistent map or null.
export function induceLocalRule(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  if(!nontrivial(nt)) return null;
  const key=(g:Grid,y:number,x:number)=>{ let k=""; for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){ const ny=y+dy,nx=x+dx; k+=((ny<0||ny>=g.length||nx<0||nx>=g[0].length)?-1:g[ny][nx])+","; } return k; };
  const map=new Map<string,number>();
  for(const p of nt) for(let y=0;y<p.input.length;y++)for(let x=0;x<p.input[0].length;x++){ const k=key(p.input,y,x), o=p.output[y][x]; if(map.has(k)&&map.get(k)!==o) return null; map.set(k,o); }
  const apply=(g:Grid):Grid|null=>{ const out=g.map(r=>r.slice()); for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++){ const k=key(g,y,x); if(!map.has(k)) return null; out[y][x]=map.get(k)!; } return out; };
  return nt.every(p=>eqG(apply(p.input)!,p.output)) ? apply : null;
}

// MULTISET key: (centre value, sorted multiset of 8 neighbour values) → output. Arrangement-
// invariant, so it generalizes better (e.g. "centre with >=2 like neighbours → X").
export function induceLocalRuleMS(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  if(!nontrivial(nt)) return null;
  const key=(g:Grid,y:number,x:number)=>{ const nb:number[]=[]; for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){ if(dy===0&&dx===0)continue; const ny=y+dy,nx=x+dx; nb.push((ny<0||ny>=g.length||nx<0||nx>=g[0].length)?-1:g[ny][nx]); } return g[y][x]+"|"+nb.sort((a,b)=>a-b).join(","); };
  const map=new Map<string,number>();
  for(const p of nt) for(let y=0;y<p.input.length;y++)for(let x=0;x<p.input[0].length;x++){ const k=key(p.input,y,x), o=p.output[y][x]; if(map.has(k)&&map.get(k)!==o) return null; map.set(k,o); }
  const apply=(g:Grid):Grid|null=>{ const out=g.map(r=>r.slice()); for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++){ const k=key(g,y,x); if(!map.has(k)) return null; out[y][x]=map.get(k)!; } return out; };
  return nt.every(p=>eqG(apply(p.input)!,p.output)) ? apply : null;
}
