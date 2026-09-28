"""Build explorer.html: canvas UMAP map of all passages with search + click-to-read."""
import json, os, html
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")

GROUP_COLORS = {"canon": "#2a6f6f", "philosophy": "#b07a2a", "selfhelp": "#a03a3a"}

def main():
    z = np.load(os.path.join(DATA, "umap2d.npz"))["xy"]
    df = pd.read_csv(os.path.join(DATA, "corpus.csv"))
    cl = pd.read_csv(os.path.join(DATA, "clusters.csv"))
    df = df.merge(cl[["passage_id", "cluster"]], on="passage_id", how="left")

    pts = []
    for i, r in df.iterrows():
        pts.append({"x": round(float(z[i, 0]), 3), "y": round(float(z[i, 1]), 3),
                    "g": r["group"], "w": r["work"], "t": r["title"],
                    "a": r["author"], "y_": int(r["year"]),
                    "c": int(r["cluster"]) if pd.notna(r["cluster"]) else -1,
                    "p": r["passage"][:500]})
    payload = json.dumps(pts, ensure_ascii=False).replace("</", "<\\/")
    colors = json.dumps(GROUP_COLORS)

    page = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Wisdom Atlas — explorer</title>
<style>
body{font-family:Georgia,serif;margin:0;color:#222}
#head{padding:1em 1.5em;border-bottom:1px solid #ddd}
#head h1{margin:0;font-size:1.4em}
#head p{margin:.3em 0 0;color:#555;font-size:.9em}
#bar{display:flex;gap:.6em;padding:.7em 1.5em;border-bottom:1px solid #ddd;align-items:center;flex-wrap:wrap;font-family:sans-serif;font-size:.85em}
#main{display:flex;height:calc(100vh - 150px)}
#map{flex:1;position:relative;background:#fafafa}
canvas{width:100%;height:100%;display:block;cursor:crosshair}
#side{width:340px;border-left:1px solid #ddd;padding:1em;overflow-y:auto;font-size:.92em}
#side blockquote{border-left:3px solid #2a6f6f;padding-left:.8em;font-style:italic;margin:.5em 0}
.meta{color:#666;font-size:.85em}
.hit{background:#ffe9a8}
.legend span{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}
</style></head><body>
<div id="head"><h1>Wisdom Atlas</h1>
<p>9,446 passages from 15 wisdom &amp; self-help texts, positioned by meaning (MiniLM + UMAP). Click any dot to read it.</p></div>
<div id="bar">
<input id="q" type="text" placeholder="search words, e.g. diligence, desire, death" size="38">
<button id="go">Search</button>
<button id="clr">Clear</button>
<select id="gf"><option value="">all shelves</option><option value="canon">ancient canon</option><option value="philosophy">transcendentalists</option><option value="selfhelp">self-help classics</option></select>
<span class="legend"><span style="background:#2a6f6f"></span>canon <span style="background:#b07a2a"></span>transcendentalists <span style="background:#a03a3a"></span>self-help</span>
<span id="count"></span>
</div>
<div id="main"><div id="map"><canvas id="cv"></canvas></div><div id="side"><p class="meta">Click a dot, or search.</p></div></div>
<script>
const PTS = __PAYLOAD__;
const COLORS = __COLORS__;
const cv=document.getElementById('cv'),ctx=cv.getContext('2d'),side=document.getElementById('side');
let W,H,x0,x1,y0,y1,hl=new Set(),gf='';
function fit(){W=cv.width=cv.offsetWidth*2;H=cv.height=cv.offsetHeight*2;
 let xs=PTS.map(p=>p.x),ys=PTS.map(p=>p.y);
 x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);}
function draw(){ctx.clearRect(0,0,W,H);
 const sx=x=>(x-x0)/(x1-x0)*W, sy=y=>(1-(y-y0)/(y1-y0))*H;
 let n=0;
 for(let i=0;i<PTS.length;i++){const p=PTS[i];
  if(gf&&p.g!==gf)continue;
  const isH=hl.has(i); n++;
  ctx.fillStyle=isH?'#e8a100':COLORS[p.g];
  const s=isH?10:5;
  ctx.fillRect(sx(p.x)-s/2,sy(p.y)-s/2,s,s);}
 document.getElementById('count').textContent=n.toLocaleString()+' passages';
 cv._sx=sx;cv._sy=sy;}
function show(i){const p=PTS[i];
 side.innerHTML=`<blockquote>${esc(p.p)}</blockquote>
 <div class="meta"><b>${esc(p.t)}</b><br>${esc(p.a)}, ${p.y_<0?('c. '+(-p.y_)+' BCE'):p.y_}<br>shelf: ${p.g} · cluster ${p.c}</div>`;}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}
cv.addEventListener('click',e=>{const r=cv.getBoundingClientRect();
 const mx=(e.clientX-r.left)*2,my=(e.clientY-r.top)*2;let best=-1,bd=1e9;
 for(let i=0;i<PTS.length;i++){const p=PTS[i];if(gf&&p.g!==gf)continue;
  const dx=cv._sx(p.x)-mx,dy=cv._sy(p.y)-my,d=dx*dx+dy*dy;if(d<bd){bd=d;best=i;}}
 if(best>=0)show(best);});
document.getElementById('go').onclick=()=>{const q=document.getElementById('q').value.toLowerCase().trim();
 hl=new Set();if(!q){draw();return;}
 PTS.forEach((p,i)=>{if(p.p.toLowerCase().includes(q))hl.add(i);});
 draw();side.innerHTML=`<p class="meta">${hl.size} passages mention "<b>${esc(q)}</b>". Matches glow gold — click one.</p>`;};
document.getElementById('clr').onclick=()=>{document.getElementById('q').value='';hl=new Set();gf='';document.getElementById('gf').value='';draw();};
document.getElementById('gf').onchange=e=>{gf=e.target.value;draw();};
fit();draw();window.addEventListener('resize',()=>{fit();draw();});
</script></body></html>"""
    page = page.replace("__PAYLOAD__", payload).replace("__COLORS__", colors)
    out = os.path.join(PROJ, "explorer.html")
    open(out, "w", encoding="utf-8").write(page)
    print(f"wrote {out} ({len(pts)} points, {os.path.getsize(out)//1024} KB)")

if __name__ == "__main__":
    main()
