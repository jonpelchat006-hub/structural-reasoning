// trace.ts — v1 of the TRACE SYNTHESIZER, the ARC distillation of the geo format:
// "everything becomes a trace — a path of segments between anchor points (bubbles)."
// Anchors = isolated markers (the bubbles). The drawn content = straight segments (H / V /
// 45°-diagonal) between selected anchor pairs, under a LEARNED pairing rule + colour,
// induced from the train demonstration and replayed at test. Generalizes `connect`
// (consecutive aligned only) to arbitrary anchor pairs + diagonals. Self-contained.
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

function isolatedMarkers(g:Grid,bg:number):[number,number,number][]{
  const R=g.length,C=g[0].length, m:[number,number,number][]=[];
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]===bg)continue; let iso=true;
    for(let dy=-1;dy<=1&&iso;dy++)for(let dx=-1;dx<=1;dx++){ if(dy===0&&dx===0)continue; const ny=y+dy,nx=x+dx;
      if(ny>=0&&ny<R&&nx>=0&&nx<C&&g[ny][nx]!==bg){iso=false;break;} }
    if(iso) m.push([y,x,g[y][x]]); }
  return m;
}
// straight (H/V/45°) interior points between two anchors; null if not straight-alignable
function segment(a:[number,number,number], b:[number,number,number]):[number,number][]|null{
  const dy=b[0]-a[0], dx=b[1]-a[1];
  const straight = dy===0 || dx===0 || Math.abs(dy)===Math.abs(dx);
  if(!straight || (dy===0&&dx===0)) return null;
  const sy=Math.sign(dy), sx=Math.sign(dx); const n=Math.max(Math.abs(dy),Math.abs(dx));
  const pts:[number,number][]=[];
  for(let k=1;k<n;k++) pts.push([a[0]+sy*k, a[1]+sx*k]);   // interior only (exclude endpoints)
  return pts;
}

export function induceTrace(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0;
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  // learn a constant draw-colour if needed (first bg→non-bg cell in pair 0)
  let CONST=-1; { const p=nt[0]; outer: for(let y=0;y<p.output.length;y++)for(let x=0;x<p.output[0].length;x++) if(p.input[y][x]===bg&&p.output[y][x]!==bg){ CONST=p.output[y][x]; break outer; } }
  const PAIRS=["allStraight","sameColor","nearest"] as const;
  const COLS=["src","const"] as const;
  for(const pr of PAIRS) for(const cm of COLS){
    if(cm==="const"&&CONST<0) continue;
    const draw=(g:Grid):Grid=>{ const out=g.map(r=>r.slice()); const A=isolatedMarkers(g,bg);
      const chosen:[number,number][]=[];
      if(pr==="nearest"){
        for(let i=0;i<A.length;i++){ let bj=-1,bd=1e9; for(let j=0;j<A.length;j++){ if(i===j)continue; const s=segment(A[i],A[j]); if(!s)continue; const d=s.length; if(d<bd){bd=d;bj=j;} } if(bj>=0)chosen.push([i,bj]); }
      } else {
        for(let i=0;i<A.length;i++)for(let j=i+1;j<A.length;j++){ if(pr==="sameColor"&&A[i][2]!==A[j][2])continue; chosen.push([i,j]); }
      }
      for(const [i,j] of chosen){ const s=segment(A[i],A[j]); if(!s)continue; const col=cm==="src"?A[i][2]:CONST;
        for(const [y,x] of s){ if(out[y][x]===bg) out[y][x]=col; } }
      return out; };
    if(nt.every(p=>eqG(draw(p.input),p.output))) return draw;
  }
  return null;
}
