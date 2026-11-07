"""Build explorer.html: a threshold slider over the survival curves —
what share of breakfasts / snacks / kids' breakfasts are sweeter than X?
Curves precomputed from the occasion data and embedded as JSON.
"""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ROOT = os.path.join(HERE, "..")


def survival(df, thresholds):
    d = df.sort_values("sugar_share")
    w = d["WTDRD1"].to_numpy()
    s = d["sugar_share"].to_numpy()
    cw = np.cumsum(w) / w.sum()
    return [float(1 - cw[np.searchsorted(s, t, side="right")])
            if np.searchsorted(s, t, side="right") < len(s) else 0.0
            for t in thresholds]


def main():
    occ = pd.read_parquet(os.path.join(DATA, "occasions.parquet"))
    th = [round(x / 100, 2) for x in range(5, 96, 1)]
    curves = {"thresholds": th}
    a1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 20) & (occ["age"] <= 79)
             & (occ["day_kcal"] >= 500) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)]
    k1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 2) & (occ["age"] <= 19)
             & (occ["day_kcal"] >= 300) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)]
    for name, d in [("adult_breakfast", a1[a1["meal"] == "breakfast"]),
                    ("adult_snack", a1[a1["meal"] == "snack"]),
                    ("adult_lunch", a1[a1["meal"] == "lunch"]),
                    ("adult_dinner", a1[a1["meal"] == "dinner"]),
                    ("kids_breakfast", k1[k1["meal"] == "breakfast"]),
                    ("kids_snack", k1[k1["meal"] == "snack"])]:
        curves[name] = survival(d, th)
    payload = json.dumps(curves)
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Breakfast Is Dessert — explorer</title>
<style>
body{font-family:Georgia,serif;max-width:760px;margin:40px auto;padding:0 20px;color:#222;line-height:1.5}
h1{font-size:28px;margin-bottom:4px} .sub{color:#666;margin-top:0}
input[type=range]{width:100%} .big{font-size:44px;font-weight:bold;color:#C0392B}
.row{display:flex;gap:24px;flex-wrap:wrap} .card{flex:1;min-width:150px;border:1px solid #ddd;border-radius:8px;padding:12px 16px}
.card h3{margin:0 0 4px;font-size:15px} .pct{font-size:30px;font-weight:bold}
.note{font-size:13px;color:#666} svg{width:100%;height:auto}
</style></head><body>
<h1>How sweet is your breakfast?</h1>
<p class="sub">Move the slider: what share of American eating occasions are
sweeter than the line you pick? NHANES 2007–2018, day 1, survey-weighted.</p>
<label for="thr"><b>Dessert line: <span id="thrLabel">25%</span> of an
occasion's calories from sugar</b></label>
<input type="range" id="thr" min="5" max="95" value="25" step="1">
<div class="row">
<div class="card"><h3>Adult breakfasts past the line</h3><div class="pct" id="bf" style="color:#C0392B">–</div></div>
<div class="card"><h3>Adult snacks past the line</h3><div class="pct" id="sn" style="color:#E67E22">–</div></div>
<div class="card"><h3>Kids' breakfasts past the line</h3><div class="pct" id="kb" style="color:#8E44AD">–</div></div>
</div>
<p class="note">At 25%, most adult breakfasts (55.5%) and two-thirds of kids'
breakfasts (67.7%) are past the line. At the median snack's own sweetness
(34.6%), 38% of adult breakfasts are still past it. The median adult
breakfast is 27.2% sugar calories; the median dinner is 10.9%.</p>
<p class="note">Data: NHANES dietary recalls, cycles 2007-08 to 2017-18.
Adults 20–79 (n = 24,156 person-days); children 2–19. Total sugars, not
added sugars — see the README for the fruit/milk caveat and the
food-group decomposition.</p>
<script>
const curves = __PAYLOAD__;
const slider = document.getElementById('thr');
function at(curve, t){
  const i = curves.thresholds.indexOf(t);
  return i >= 0 ? curve[i] : null;
}
function update(){
  const t = parseInt(slider.value, 10);
  document.getElementById('thrLabel').textContent = t + '%';
  document.getElementById('bf').textContent = (100*at(curves.adult_breakfast, t/100)).toFixed(1) + '%';
  document.getElementById('sn').textContent = (100*at(curves.adult_snack, t/100)).toFixed(1) + '%';
  document.getElementById('kb').textContent = (100*at(curves.kids_breakfast, t/100)).toFixed(1) + '%';
}
slider.addEventListener('input', update);
update();
</script></body></html>
"""
    html = html.replace("__PAYLOAD__", payload)
    with open(os.path.join(ROOT, "explorer.html"), "w") as f:
        f.write(html)
    print("wrote explorer.html")


if __name__ == "__main__":
    main()
