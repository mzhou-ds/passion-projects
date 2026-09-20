"""05_explorer.py — fit a compact logistic bonk model, compute archetype decay
factors, and bake everything into a self-contained explorer.html.

User enters 5k/10k/15k/20k/25k splits -> archetype, predicted finish,
bonk probability.
"""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

be = pd.read_pickle("output/berlin_archetypes.pkl")
cent = pd.read_csv("output/centroids.csv", index_col=0).values
names = json.load(open("output/archetype_names.json"))
REL = [f"rel{i}" for i in range(9)]
SEG = [f"seg{i}" for i in range(9)]
KM = np.array([5, 5, 5, 5, 5, 5, 5, 5, 2.195])

segm = be[SEG].values
p30 = (segm[:, :6] * KM[:6]).sum(axis=1) / 30
pl = (segm[:, 6:] * KM[6:]).sum(axis=1) / 12.195
be["bonk"] = ((pl / p30 - 1) >= 0.12).astype(int)
be["start_aggro"] = be["seg0"] / be[["seg1", "seg2", "seg3"]].mean(axis=1)
be["mid_drift"] = be[["seg3", "seg4"]].mean(axis=1)
be["sexM"] = (be["gender"] == "M").astype(int)
FEATS = ["seg0", "seg1", "seg2", "seg3", "seg4", "start_aggro", "mid_drift", "sexM"]

lr = LogisticRegression(max_iter=2000, C=1.0)
lr.fit(be[be["year"] < 2019][FEATS], be[be["year"] < 2019]["bonk"])
auc = __import__("sklearn.metrics", fromlist=["roc_auc_score"]).roc_auc_score(
    be[be["year"] == 2019]["bonk"],
    lr.predict_proba(be[be["year"] == 2019][FEATS])[:, 1])
print("logreg test AUC:", round(float(auc), 3))

# archetype decay factor: median finish / (time at 25k projected linearly)
t25 = (segm[:, :5] * KM[:5]).sum(axis=1)
proj = t25 / 25 * 42.195
decay = (be["time_full_s"] / proj).groupby(be["archetype"]).median()
print(decay.round(3).to_string())

payload = {
    "centroids": {names[str(i)]: [round(float(v), 4) for v in cent[i]] for i in range(5)},
    "lr_coef": [round(float(c), 6) for c in lr.coef_[0]],
    "lr_intercept": round(float(lr.intercept_[0]), 6),
    "feats": FEATS,
    "decay": {k: round(float(v), 4) for k, v in decay.items()},
}
json.dump(payload, open("output/explorer_payload.json", "w"), indent=1)

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>The Wall Fingerprint — pacing explorer</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:640px;margin:2em auto;padding:0 1em;color:#222}
h1{font-size:1.5em} .row{display:flex;gap:.5em;flex-wrap:wrap;margin:.4em 0}
label{font-size:.85em} input,select{padding:.4em;font-size:1em;width:7em}
button{padding:.6em 1.2em;font-size:1em;margin-top:.6em;cursor:pointer}
#out{margin-top:1.2em;padding:1em;background:#f6f6f6;border-radius:8px;display:none}
.big{font-size:1.4em;font-weight:bold} .risk-high{color:#b00020} .risk-low{color:#0a7a3d}
small{color:#666}
</style></head><body>
<h1>🏃 The Wall Fingerprint — pacing explorer</h1>
<p>Enter your splits through 25k (mm:ss per checkpoint, cumulative). Trained on
158,674 Berlin Marathon finishes (2016–2019).</p>
<div class="row">
<label>5k <input id="s5" placeholder="25:00"></label>
<label>10k <input id="s10" placeholder="50:00"></label>
<label>15k <input id="s15" placeholder="1:15:00"></label>
<label>20k <input id="s20" placeholder="1:40:00"></label>
<label>25k <input id="s25" placeholder="2:05:00"></label>
<label>Sex <select id="sex"><option value="0">F</option><option value="1">M</option></select></label>
</div>
<button onclick="go()">Analyze my race</button>
<div id="out"></div>
<p><small>Archetype = nearest pacing centroid. Finish prediction = linear 25k
projection × archetype-typical decay. Bonk = ≥12% slower over the last 12.2k
than the first 30k. Model: logistic regression on early segment paces.</small></p>
<script>
const P = __PAYLOAD__;
function ts(s){s=s.trim(); if(!s) return NaN;
  const p=s.split(":").map(Number); if(p.some(isNaN)) return NaN;
  return p.length===3 ? p[0]*3600+p[1]*60+p[2] : p[0]*60+p[1];}
function fmt(t){t=Math.round(t); const h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;
  return (h?h+":":"")+String(m).padStart(h?2:1,"0")+":"+String(s).padStart(2,"0");}
function go(){
  const cum=["s5","s10","s15","s20","s25"].map(id=>ts(document.getElementById(id).value));
  if(cum.some(isNaN)){alert("Enter all five splits as mm:ss or h:mm:ss.");return;}
  const bounds=[5,10,15,20,25], seg=[]; let prev=0,pd=0;
  for(let i=0;i<5;i++){seg.push((cum[i]-prev)/(bounds[i]-pd)); prev=cum[i]; pd=bounds[i];}
  const avg=cum[4]/25, rel=seg.map(v=>v/avg);
  let best=null,bd=1e18;
  for(const [name,c] of Object.entries(P.centroids)){
    let d=0; for(let i=0;i<9;i++){const r=i<5?rel[i]:1.0; d+=(r-c[i])**2;}
    if(d<bd){bd=d;best=name;}}
  const sexM=+document.getElementById("sex").value;
  const aggro=seg[0]/((seg[1]+seg[2]+seg[3])/3), drift=(seg[3]+seg[4])/2;
  const feats=[...seg,aggro,drift,sexM];
  let z=P.lr_intercept; feats.forEach((v,i)=>z+=v*P.lr_coef[i]);
  const prob=1/(1+Math.exp(-z));
  const finish=cum[4]/25*42.195*P.decay[best];
  const el=document.getElementById("out"); el.style.display="block";
  el.innerHTML=`<div>Your archetype: <span class="big">${best}</span></div>
  <div>Predicted finish: <span class="big">${fmt(finish)}</span></div>
  <div>Bonk probability: <span class="big ${prob>0.5?"risk-high":"risk-low"}">${(prob*100).toFixed(0)}%</span></div>
  <div><small>First-5k vs 10–20k pace: ${(aggro<1?"hot start ("+(100*(1-aggro)).toFixed(0)+"% fast)":"controlled")}.</small></div>`;
}
</script></body></html>"""
HTML = HTML.replace("__PAYLOAD__", json.dumps(payload))
open("explorer.html", "w").write(HTML)
print("explorer.html written")
