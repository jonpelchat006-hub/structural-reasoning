// draw2.ts — "our own version of drawing": a per-task LEARNED draw decoder.
// The discrete analog of the epicycle decoder — instead of Fourier components, the learned
// CODE is a relative-offset SPRITE: what shape gets drawn around each marker, induced from
// the train demonstration, then decoded (stamped) at the test markers. Generative twin of
// shapeRecolor (which learns a colour map; this learns a draw map). Self-contained.
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

// markers = ISOLATED single non-bg cells (8-neighbourhood all bg). The canonical "draw from
// markers" substrate. Returns [y,x,colour].
function isolatedMarkers(g:Grid,bg:number):[number,number,number][]{
  const R=g.length,C=g[0].length, m:[number,number,number][]=[];
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]===bg)continue; let iso=true;
    for(let dy=-1;dy<=1&&iso;dy++)for(let dx=-1;dx<=1;dx++){ if(dy===0&&dx===0)continue; const ny=y+dy,nx=x+dx;
      if(ny>=0&&ny<R&&nx>=0&&nx<C&&g[ny][nx]!==bg){iso=false;break;} }
    if(iso) m.push([y,x,g[y][x]]); }
  return m;
}

// induceStamp — learn sprite (keyed by marker-colour) = the set of (dy,dx)->drawnColour the
// output adds around each marker; verify one consistent sprite explains every train pair.
export function induceStamp(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0;
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  const sprite=new Map<number,Map<string,number>>();   // markerColour -> "dy,dx" -> drawnColour
  for(const p of nt){
    const mk=isolatedMarkers(p.input,bg); if(!mk.length) return null;
    for(let y=0;y<p.output.length;y++)for(let x=0;x<p.output[0].length;x++){
      if(p.output[y][x]===p.input[y][x]) continue;      // unchanged cell
      let best=-1,bd=1e9;                               // assign drawn cell to nearest marker
      for(let i=0;i<mk.length;i++){ const d=Math.max(Math.abs(mk[i][0]-y),Math.abs(mk[i][1]-x)); if(d<bd){bd=d;best=i;} }
      if(best<0) return null;
      const [my,mx,mc]=mk[best]; const key=(y-my)+","+(x-mx); const drawn=p.output[y][x];
      if(!sprite.has(mc)) sprite.set(mc,new Map());
      const sp=sprite.get(mc)!;
      if(sp.has(key)&&sp.get(key)!==drawn) return null; // inconsistent sprite
      sp.set(key,drawn);
    }
  }
  let any=false; for(const s of sprite.values()) if(s.size) any=true; if(!any) return null;
  const apply=(g:Grid):Grid|null=>{
    const out=g.map(r=>r.slice()); const mk=isolatedMarkers(g,bg);
    for(const [my,mx,mc] of mk){ const sp=sprite.get(mc); if(!sp) continue;
      for(const [key,col] of sp){ const a=key.split(","); const ny=my+ +a[0], nx=mx+ +a[1];
        if(ny<0||ny>=out.length||nx<0||nx>=out[0].length) continue; out[ny][nx]=col; } }
    return out;
  };
  return nt.every(p=>eqG(apply(p.input)!,p.output)) ? apply : null;
}
