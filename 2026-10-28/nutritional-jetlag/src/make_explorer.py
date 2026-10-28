"""Generate explorer.html: pick an age band + day-pair type + clock reading
and see the median day-to-day shift for people like that, from the real
pair-level table (aggregated into output/explorer_cells.csv)."""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def wmed(x, w):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(w) - 0.5 * w
    return float(np.interp(0.5, cw / cw[-1] if cw[-1] else cw, x)) if len(x) else None


def main():
    pairs = pd.read_parquet(os.path.join(ROOT, "data", "pairs_enriched.parquet"))
    cells = []
    for (age, pt), sub in pairs.groupby(["age_band", "pair_type"], observed=True):
        if len(sub) < 60:
            continue
        row = {"age": str(age), "pair": pt, "n": int(len(sub))}
        for c in ["first", "mid", "last", "window"]:
            row[c] = round(wmed(sub[f"abs_shift_{c}"], sub["WTDR2D"]), 2)
        row["gt2"] = round(float(np.average(sub["abs_shift_mid"] > 2,
                                            weights=sub["WTDR2D"])) * 100, 1)
        cells.append(row)
    pd.DataFrame(cells).to_csv(os.path.join(ROOT, "output", "explorer_cells.csv"),
                               index=False)
    html = TEMPLATE.replace("__CELLS__", json.dumps(cells))
    with open(os.path.join(ROOT, "explorer.html"), "w") as f:
        f.write(html)
    print("explorer cells:", len(cells))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your Eating Clock Wobble — Musing with Mike</title>
<style>
body{font-family:Georgia,serif;margin:2rem auto;max-width:640px;padding:0 1rem;color:#222}
h1{font-size:1.5rem} select{font-size:1rem;padding:.3rem;margin:.2rem}
.big{font-size:2.6rem;font-weight:bold;color:#1b6f5e}
.card{border:1px solid #ddd;border-radius:8px;padding:1rem;margin-top:1rem}
small{color:#666}
</style></head><body>
<h1>How far does your eating clock move between two ordinary days?</h1>
<p>Pick people like you. The numbers are the median day-to-day shift in the
calorie-weighted midpoint of the eating day, measured in NHANES two-day
24-hour recalls (2007–2018, adults 20–79).</p>
<label>Age <select id="age"></select></label>
<label>Your two days <select id="pair">
<option value="both_weekday">both weekdays</option>
<option value="mixed">one weekday, one weekend</option>
<option value="both_weekend">both weekend</option></select></label>
<label>Clock reading <select id="clock">
<option value="mid">calorie midpoint</option>
<option value="first">first bite</option>
<option value="last">last bite</option>
<option value="window">eating window</option></select></label>
<div class="card"><div class="big" id="out">–</div>
<div id="sub"></div></div>
<p><small>Median absolute shift between recall day 1 and day 2. Based on real
NHANES respondents in that cell; small cells (n &lt; 60) are omitted.</small></p>
<script>
const CELLS = __CELLS__;
const ages = [...new Set(CELLS.map(c=>c.age))];
const ageSel = document.getElementById('age');
ages.forEach(a=>{const o=document.createElement('option');o.value=a;o.textContent=a;ageSel.appendChild(o);});
function upd(){
  const a=ageSel.value, p=document.getElementById('pair').value,
        k=document.getElementById('clock').value;
  const c=CELLS.find(x=>x.age===a&&x.pair===p);
  if(!c){document.getElementById('out').textContent='not enough data';document.getElementById('sub').textContent='';return;}
  document.getElementById('out').textContent=c[k].toFixed(2)+' hours';
  document.getElementById('sub').textContent=
    `Median shift for ${a} adults (n=${c.n.toLocaleString()}). `+
    `${c.gt2}% of them moved their calorie midpoint by more than 2 hours between the two days.`;
}
document.querySelectorAll('select').forEach(s=>s.addEventListener('change',upd));
upd();
</script></body></html>
"""

if __name__ == "__main__":
    main()
