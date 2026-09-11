"""Build explorer.html: an interactive 'how strong are you?' percentile lookup.

Embeds the per-bodyweight-bin percentile tables from output/standards.csv as
JSON and interpolates the user's total to a percentile rank. Fully
self-contained (no external requests).
"""
import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "output")

PCTS = [5, 10, 25, 50, 75, 90, 95, 99]

standards = pd.read_csv(os.path.join(OUT, "standards.csv"))
data = {}
for _, r in standards.iterrows():
    key = f"{r['sex']}|{r['equipment']}|{int(r['bw_bin'])}"
    data[key] = {"n": int(r["n"]),
                 "pct": [float(r[f"p{p}"]) for p in PCTS]}

with open(os.path.join(OUT, "summary.json")) as fh:
    summary = json.load(fh)

payload = json.dumps({"pcts": PCTS, "bins": data,
                      "overall": summary["overall_percentiles"]})

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strength in Numbers — How strong are you?</title>
<style>
  :root { --bg:#ffffff; --fg:#1c1c1c; --muted:#666; --card:#f5f7fa;
          --blue:#2a6fbf; --orange:#d95f02; --line:#dfe5ec; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171c; --fg:#e8eaed; --muted:#9aa3ad; --card:#1d2127;
            --line:#2c333d; }
  }
  * { box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:var(--bg); color:var(--fg); margin:0; padding:24px;
         max-width:760px; margin-left:auto; margin-right:auto; }
  h1 { font-size:1.5rem; margin-bottom:0.2rem; }
  p.sub { color:var(--muted); margin-top:0; font-size:0.95rem; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:18px; margin:14px 0; }
  label { display:block; font-size:0.85rem; color:var(--muted); margin:10px 0 4px; }
  select, input[type=number] { width:100%; padding:10px; font-size:1rem;
          border:1px solid var(--line); border-radius:8px;
          background:var(--bg); color:var(--fg); }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .verdict { font-size:1.35rem; font-weight:700; margin:6px 0; }
  .bar { height:14px; border-radius:7px; background:var(--line);
         position:relative; margin:14px 0 4px; }
  .bar .fill { position:absolute; left:0; top:0; bottom:0; border-radius:7px;
               background:linear-gradient(90deg,var(--blue),var(--orange)); }
  .ticks { display:flex; justify-content:space-between; font-size:0.75rem;
           color:var(--muted); }
  table { width:100%; border-collapse:collapse; font-size:0.9rem; margin-top:8px; }
  th, td { padding:6px 4px; text-align:right; border-bottom:1px solid var(--line); }
  th:first-child, td:first-child { text-align:left; }
  .note { font-size:0.8rem; color:var(--muted); }
</style>
</head>
<body>
<h1>🏋️ How strong are you, really?</h1>
<p class="sub">Your powerlifting total, ranked against <b>389,009</b> real IPF-affiliate
competitors (one best total per lifter). Data: OpenPowerlifting, Sep 2026.</p>

<div class="card">
  <div class="row">
    <div><label>Sex division</label>
      <select id="sex"><option value="M">Men</option><option value="F">Women</option></select></div>
    <div><label>Equipment</label>
      <select id="equip"><option value="Raw">Raw</option><option value="Single-ply">Single-ply</option></select></div>
  </div>
  <div class="row">
    <div><label>Bodyweight (kg)</label>
      <input type="number" id="bw" value="83" min="40" max="180" step="0.5"></div>
    <div><label>Best total — squat + bench + deadlift (kg)</label>
      <input type="number" id="total" value="500" min="0" step="2.5"></div>
  </div>
</div>

<div class="card">
  <div class="verdict" id="verdict">—</div>
  <div class="bar"><div class="fill" id="fill" style="width:0%"></div></div>
  <div class="ticks"><span>0th</span><span>25th</span><span>50th</span>
    <span>75th</span><span>100th percentile</span></div>
  <p class="note" id="context"></p>
  <table id="ptable"></table>
</div>

<p class="note">Method: percentile tables are computed per 5&nbsp;kg bodyweight bin from
each lifter's single best total (Raw: 225,463 lifters; Single-ply: 163,546).
Your rank is linearly interpolated within your bin. These are <i>competition</i>
standards — the median competitor trains specifically for this — so don't feel
bad about landing under the 50th.</p>

<script>
const DATA = __PAYLOAD__;

function binOf(bw){ let b = Math.floor(bw/5)*5; return Math.min(Math.max(b,40),180); }

function percentileFor(key, total){
  const e = DATA.bins[key]; if(!e) return null;
  const vals = e.pct, ps = DATA.pcts;
  if(total <= vals[0]) return {p: ps[0], approx:true, below:true};
  for(let i=0;i<vals.length-1;i++){
    if(total <= vals[i+1]){
      const f = (total-vals[i])/(vals[i+1]-vals[i]);
      return {p: ps[i] + f*(ps[i+1]-ps[i]), approx:false};
    }
  }
  return {p: ps[ps.length-1], approx:true, above:true};
}

function update(){
  const sex = document.getElementById('sex').value;
  const equip = document.getElementById('equip').value;
  const bw = parseFloat(document.getElementById('bw').value);
  const total = parseFloat(document.getElementById('total').value);
  if(!(bw>0) || !(total>=0)) return;
  const key = sex+'|'+equip+'|'+binOf(bw);
  const r = percentileFor(key, total);
  const e = DATA.bins[key];
  const v = document.getElementById('verdict');
  if(r.below) v.textContent = 'Below the 5th percentile — every champion started somewhere.';
  else if(r.above) v.textContent = 'Above the 99th percentile — you are genuinely elite. 🏆';
  else {
    const top = 100 - r.p;
    v.textContent = top <= 50
      ? `Top ${top.toFixed(1)}% — your ${total} kg total beats ${(100-top).toFixed(1)}% of ${sex==='M'?'men':'women'} competing ${equip.toLowerCase()} at ~${binOf(bw)} kg.`
      : `${r.p.toFixed(1)}th percentile — your ${total} kg total beats ${r.p.toFixed(1)}% of ${sex==='M'?'men':'women'} competing ${equip.toLowerCase()} at ~${binOf(bw)} kg.`;
  }
  document.getElementById('fill').style.width = Math.min(100,Math.max(0,r.p)) + '%';
  document.getElementById('context').textContent =
    `Compared against ${e.n.toLocaleString()} lifters in the ${binOf(bw)}–${binOf(bw)+5} kg bin.`;
  const ps = DATA.pcts, vals = e.pct;
  let html = '<tr><th>Percentile</th>' + ps.map(p=>`<th>p${p}</th>`).join('') + '</tr>';
  html += '<tr><td>Total (kg)</td>' + vals.map(x=>`<td>${x.toFixed(0)}</td>`).join('') + '</tr>';
  document.getElementById('ptable').innerHTML = html;
}
['sex','equip','bw','total'].forEach(id=>
  document.getElementById(id).addEventListener('input', update));
update();
</script>
</body>
</html>
"""

html = HTML.replace("__PAYLOAD__", payload)
with open(os.path.join(HERE, "explorer.html"), "w") as fh:
    fh.write(html)
print("wrote explorer.html", len(html) // 1024, "KB")
