"""Build explorer.html: search any of the 7,756 foods and see its
protein-density percentile, leucine content, and nutrient-density score."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Protein Atlas Explorer — Musing with Mike</title>
<style>
  :root { --teal:#0e7c7b; --coral:#d95f02; --gold:#b5892e; --ink:#222; --mut:#666; --bg:#faf9f6; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--ink); margin: 0; padding: 24px; }
  .wrap { max-width: 860px; margin: 0 auto; }
  h1 { font-size: 26px; margin: 0 0 4px; }
  .sub { color: var(--mut); margin-bottom: 20px; }
  input[type=text] { width: 100%; font-size: 17px; padding: 12px 14px;
    border: 2px solid #ddd; border-radius: 10px; }
  input[type=text]:focus { outline: none; border-color: var(--teal); }
  #results { margin-top: 10px; }
  .hit { padding: 10px 12px; border-bottom: 1px solid #eee; cursor: pointer; }
  .hit:hover { background: #f0eeea; }
  .hit .cat { color: var(--mut); font-size: 12px; }
  #detail { margin-top: 18px; background: white; border: 1px solid #e5e2dc;
    border-radius: 12px; padding: 20px 22px; display: none; }
  #detail h2 { margin: 0 0 2px; font-size: 20px; }
  #detail .cat { color: var(--mut); font-size: 13px; margin-bottom: 14px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin: 14px 0; }
  .stat { background: var(--bg); border-radius: 8px; padding: 10px 12px; }
  .stat .v { font-size: 22px; font-weight: 700; color: var(--teal); }
  .stat .l { font-size: 12px; color: var(--mut); }
  .bar { height: 10px; background: #eee; border-radius: 5px; overflow: hidden; margin-top: 6px; }
  .bar > div { height: 100%; background: var(--teal); }
  .macro { display: flex; height: 22px; border-radius: 6px; overflow: hidden; margin: 8px 0 4px; }
  .macro div { display: flex; align-items: center; justify-content: center;
    font-size: 11px; color: white; font-weight: 600; min-width: 0; }
  .legend { font-size: 12px; color: var(--mut); }
  .note { font-size: 13px; color: var(--mut); margin-top: 14px; }
  .pct { font-size: 13px; color: var(--mut); }
</style>
</head>
<body>
<div class="wrap">
  <h1>🥩 Protein Atlas Explorer</h1>
  <div class="sub">Search 7,756 foods from the USDA database. See how protein-dense
  each one really is — grams of protein per 100 kcal, leucine, and overall nutrient density.</div>
  <input type="text" id="q" placeholder="Try &quot;tofu&quot;, &quot;salmon&quot;, &quot;greek yogurt&quot;…" autocomplete="off">
  <div id="results"></div>
  <div id="detail"></div>
  <div class="note">Data: USDA FoodData Central, SR Legacy release (public domain).
  Percentiles computed across all foods with &ge;25 kcal/100 g, spices excluded.</div>
</div>
<script>
const FOODS = __DATA__;
const q = document.getElementById('q');
const results = document.getElementById('results');
const detail = document.getElementById('detail');

q.addEventListener('input', () => {
  const s = q.value.trim().toLowerCase();
  detail.style.display = 'none';
  if (s.length < 2) { results.innerHTML = ''; return; }
  const hits = FOODS.filter(f => f.n.toLowerCase().includes(s)).slice(0, 20);
  results.innerHTML = hits.length
    ? hits.map((f, i) => `<div class="hit" data-i="${FOODS.indexOf(f)}"><b>${esc(f.n)}</b><br><span class="cat">${esc(f.c)}</span></div>`).join('')
    : '<div class="hit">No matches — try a simpler term.</div>';
  results.querySelectorAll('.hit[data-i]').forEach(el =>
    el.addEventListener('click', () => show(FOODS[+el.dataset.i])));
});

function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;'); }

function show(f){
  results.innerHTML = '';
  const leu = f.l == null ? '—' : `${Math.round(f.l)} mg`;
  const p = f.pp, fp = f.fp, cp = f.cp;
  detail.style.display = 'block';
  detail.innerHTML = `
    <h2>${esc(f.n)}</h2><div class="cat">${esc(f.c)} · ${f.k} kcal / 100 g</div>
    <div class="macro">
      <div style="width:${p}%;background:var(--teal)" title="protein">${p>12?p+'% prot':''}</div>
      <div style="width:${fp}%;background:var(--gold)" title="fat">${fp>12?fp+'% fat':''}</div>
      <div style="width:${cp}%;background:#9db8b7" title="carbs">${cp>12?cp+'% carb':''}</div>
    </div>
    <div class="legend">Calorie split per 100 g: protein ${p}% · fat ${fp}% · carbs ${cp}%</div>
    <div class="stats">
      <div class="stat"><div class="v">${f.pd.toFixed(1)} g</div><div class="l">protein / 100 kcal</div>
        <div class="pct">${f.pdp}th percentile of all foods</div><div class="bar"><div style="width:${f.pdp}%"></div></div></div>
      <div class="stat"><div class="v">${leu}</div><div class="l">leucine / 100 kcal</div>
        <div class="pct">${f.l == null ? 'no data' : 'fuels muscle protein synthesis'}</div></div>
      <div class="stat"><div class="v">${Math.round(f.nrf)}</div><div class="l">nutrient-density score</div>
        <div class="pct">${f.nrfp}th percentile of all foods</div><div class="bar"><div style="width:${f.nrfp}%"></div></div></div>
      <div class="stat"><div class="v">${f.fb.toFixed(1)} g</div><div class="l">fiber / 100 kcal</div>
        <div class="pct">${f.sg.toFixed(1)} g sugar · ${Math.round(f.so)} mg sodium / 100 kcal</div></div>
    </div>
    <div class="note">${verdict(f)}</div>`;
  detail.scrollIntoView({behavior:'smooth', block:'nearest'});
}

function verdict(f){
  if (f.pdp >= 90) return "Elite protein density — this is top-decile fuel for hitting protein targets without overshooting calories.";
  if (f.pdp >= 75) return "Strong protein density — a genuinely good protein source.";
  if (f.pdp >= 50) return "Middle of the pack — fine as part of a mixed diet, not a protein standout.";
  if (f.pdp >= 25) return "Low protein density — you'll need a lot of calories to get much protein from this.";
  return "Minimal protein — treat it as energy, flavor, or micronutrients, not protein.";
}
</script>
</body>
</html>
"""


def main():
    df = pd.read_csv(OUT / "foods_derived.csv")
    keep = df[(df["kcal"] >= 25)].copy()
    keep["pdp"] = keep["prot_100kcal"].rank(pct=True).mul(100).round(0)
    keep["nrfp"] = keep["nrf_score"].rank(pct=True).mul(100).round(0)
    keep["pp"] = (keep["protein_g"] * 4 / keep["kcal"] * 100).round(1)
    keep["fp"] = (keep["fat_g"] * 9 / keep["kcal"] * 100).round(1)
    keep["cp"] = (keep["carb_g"].fillna(0) * 4 / keep["kcal"] * 100).round(1)

    recs = []
    for _, r in keep.iterrows():
        recs.append({
            "n": r["description"], "c": r["category"], "k": round(float(r["kcal"]), 1),
            "pd": round(float(r["prot_100kcal"]), 2), "pdp": int(r["pdp"]),
            "l": None if pd.isna(r["leu_100kcal_mg"]) else round(float(r["leu_100kcal_mg"]), 1),
            "nrf": round(float(r["nrf_score"]), 1), "nrfp": int(r["nrfp"]),
            "fb": round(float(r["fiber_100kcal"]), 2),
            "sg": round(float(r["sugar_100kcal"]), 2),
            "so": round(float(r["sodium_100kcal"]), 1),
            "pp": float(r["pp"]), "fp": float(r["fp"]), "cp": float(r["cp"]),
        })
    html = HTML_HEAD.replace("__DATA__", json.dumps(recs, separators=(",", ":")))
    path = ROOT / "explorer.html"
    path.write_text(html)
    print(f"wrote {path} ({path.stat().st_size/1e6:.1f} MB, {len(recs):,} foods)")


if __name__ == "__main__":
    main()
